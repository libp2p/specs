# RFC: Proximity Aware Epidemic PubSub

<!-- toc -->

- [Introduction](#introduction)
- [Membership Management Protocol](#membership-management-protocol)
  * [Design Parameters for View Sizes](#design-parameters-for-view-sizes)
  * [Joining the Overlay](#joining-the-overlay)
  * [Leaving the Overlay](#leaving-the-overlay)
  * [Active View Management](#active-view-management)
  * [Passive View Management](#passive-view-management)
- [Broadcast Protocol](#broadcast-protocol)
  * [Broadcast State](#broadcast-state)
  * [Message Propagation and Multicast Tree Construction](#message-propagation-and-multicast-tree-construction)
  * [Multicast Tree Repair](#multicast-tree-repair)
  * [Multicast Tree Optimization](#multicast-tree-optimization)
  * [Active View Changes](#active-view-changes)
- [Protocol Messages](#protocol-messages)
- [Differences from Plumtree/HyParView](#differences-from-plumtreehyparview)

<!-- tocstop -->

## Introduction

This RFC proposes a topic pubsub protocol based on the following papers:
1. [Epidemic Broadcast Trees](http://www.gsd.inesc-id.pt/~ler/docencia/rcs1617/papers/srds07.pdf)
2. [HyParView: a membership protocol for reliable gossip-based broadcast](http://asc.di.fct.unl.pt/~jleitao/pdf/dsn07-leitao.pdf)
3. [GoCast: Gossip-enhanced Overlay Multicast for Fast and Dependable Group Communication](http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.75.4811)

The protocol implements the Plumtree algorithm from [1], with
membership managed using HyParView[2] and proximity-aware overlay
construction based on the scheme proposed in GoCast[3]. The marrying
of proximity awareness from GoCast with Plumtree was suggested by
the original authors of Plumtree in [1].

The protocol has two distinct components: the membership management
protocol (subscribe) and the brodcast protocol (publish).

The membership management protocol (Peer Sampling Service in [1])
maintains two lists of peers that are subscribed to the topic.  The
_active_ list contains peers with active broadcast connections. The
_passive_ list is a partial view of the overlay at large, and is used
for directing new joins, replacing failed peers in the active list and
optimizing the overlay. The active list is symmetric, meaning that if
a node P has node Q in its active list, then Q also has P in its active
list.

The broadcast protocol lazily constructs and optimizes a multicast
tree using epidemic broadcast. The peer splits the active list into
two sets of peers: the _eager_ peers and the _lazy_ peers. The eager
peers form the edges of the multicast tree, while the lazy peers
form a gossip mesh supporting the multicast tree.

When a new message is broadcast, it is pushed to the eager
peers, while lazy peers only receive message summaries and have to
pull missing messages.  Initially, all peers in the active list are
eager forming a connected mesh.  As messages propagate, peers _prune_
eager links when receiving duplicate messages, thus constructing a
multicast tree. The tree is repaired when peers receive lazy messages
that were not propagated via eager links by _grafting_ an eagler link
on top of a lazy one.

In steady state, the protocol optimizes the multicast tree in two
ways. Whenever a message is received via both an eager link and a
lazy message summary, its hop count is compared. When the eager
transmission hop count exceeds the lazy hop count by some threshold,
then the lazy link can replace the eager link as a tree edge, reducing
latency as measured in hops.  In addition, active peers may be
periodically replaced by passive peers with better network proximity,
thus reducing propagation latency in time.

## Membership Management Protocol

### Design Parameters for View Sizes

The size of the active and passive lists is a design parameter in HyParView,
dependent on the size `N` of the overlay:
```
A(N) = log(N) + c
P(N) = k * A(N)
```
The authors in [2] select `c=1` and `k=6`, while fixing N to a target size
of 10,000 nodes. Long term, the membership list sizes should be dynamically
adjusted based on overlay size estimations. For practical purposes, we can
start with a large target size, and introduce dynamic sizing later in the
development cycle.

A second parameter that needs to be adjusted is the number of random and
nearby neighbors in A for proximity optimizations. In [3], the authors
use two parameters `C_rand` and `C_near` to set the size of the neighbor list
such that
```
A = C_rand + C_near
```

In their analysis they fix `C_rand=1` and `C_near=5`, with their
rationale being that a single random link is sufficient to connect the
overlay, at least in bimodal distributions, while overlays without any
random links may fail to connect at all.  Nonetheless, the random link
parameter is directly related to the connectivity of the overlay. A
higher `C_rand` ensures connectivity with high probability and fault
tolerance.  The fault-tolerance and connectivity properpties
of HyParView stem from the random overlay structure, so in order to
preserve them and still optimize for proximity, we need to set
```
C_rand = log(N)
```

For a real-world implementation at the scale of IPFS, we can use the following
starting values:
```
N = 10,000
C_rand = 4
C_near = 3
A = 7
P = 42
```

### Joining the Overlay

In order to subscribe to the topic, a node P needs to locate one or more
nodes in the topic and join the overlay. The initial contact nodes can
be obtained via rendezvous with DHT provider records.

Once a list of initial contact nodes has been obtained, the node selects
nodes randomly and sends a `GETNODES` message in order to obtain
an up-to-date view of the overlay from the passive list of a subscribed node
regardless of age of Provider records. Once an up-to-date passive view of
the overlay has been obtained, the node proceeds to join.

In order to join, it picks a subscribed node at random and sends
`JOIN` a message to it with some initial TTL set as a design
parameter.

The `JOIN` message propagates with a random walk until a node is willing
to accept it or the TTL expires. Upon receiving a `JOIN` message, a node Q
evaluates it with the following criteria:
- Q tries to open a connection to P and take an RTT measurement. If the connection
  cannot be opened (eg because of NAT), then it checks the TTL of the message.
  If it is 0, the request is dropped, otherwise Q decrements the TTL and fowards
  the message to a random node in its active list.
- If the size of its active list is less than `A`, it accepts the join, adds
  P to its active list and sends to it `NEIGHBOR` message.
- If the RTT to P is smaller by some factor alpha (design parameter, set to 2 in [3])
  than any of its near nodes then it evicts a near neighbor if it has enough active
  links by sending a `DISCONNECT`  message and accepts P as a near neighbor.
- If the TTL of the request is 0, then it  accepts the P as a new random neighbor.

When Q accepts P as a new neighbor, it also sends a `FORWARDJOIN`
message to a random node in its active list. The `FORWARDJOIN`
propagates with a random walk until its TTL is 0, while being added to
the passive list of the receiving node.

If P fails to join because of connectivity issues, it decrements the
TTL and tries another starting node. This is repeated until a ttl of zero
reuses the connection in the case of NATed hosts.

Once the first link has been established, P then needs to increase its
active list size to `A` by connecting to more nodes.  This is
accomplished by ordering the subscriber list by RTT and picking the
nearest nodes and some nodes at random and sending `NEIGHBOR`
requests.  The neighbor requests may be accepted by `NEIGHBOR` message
and rejected by a `DISCONNECT` message.

Upon receiving a `NEIGHBOR` request a node Q evaluates it with the
followin criteria:
- If the size of Q's active list is less than A, it accepts the new
  node.
- If P does not have enough active links (less than `C_rand`, as specified in the message),
  it accepts P as a random neighbor.
- Otherwise Q takes an RTT measurement to P.
  If it's closer than any near neighbors by a factor of alpha, then
  it evicts the near neighbor if it has enough active links and accepts
  P as a new near neighbor.
- Otherwise the request is rejected.

Note that during joins, the size of the active list for some nodes may
end up being larger than `A`. Similarly, P may end up with fewer links
than `A` after an initial join. This follows [3] and tries to minimize
fluttering in joins, leaving the active list pruning for the
stabilization period of the protocol.

### Leaving the Overlay

In order to unsubscribe, the node can just leave the overlay by
sending `DISCONNECT` messages to its active neighbors.  References to
the node in the various passive lists scattered across the overlay
will be lazily pruned over time by the passive view management
component of the protocol.

In order to facilitate fast clean up of departing nodes, we can also
introduce a `LEAVE` message that eagerly propagates across the
network.  A node that wants to unsubscribe from the topic, emits a
`LEAVE` to its active list neighbors in place of `DISCONNECT`.  Upon
receiving a `LEAVE`, a node removes the node from its active list
_and_ passive lists. If the node was removed from one of the lists or
if the ttl is greater than zero, then the `LEAVE` is propagated
further across the active list links. This will ensure a random
diffusion through the network that would clean most of the active
lists eagerly, at the cost of some bandwidth.

### Active View Management

The active list is generally managed reactively: failures are detected
by TCP, either when a message is sent or when the connection is detected
as closed. 

In addition to the reactive management strategy, the active list has
stabilization and optimization components that run periodically with a
randomized timer, and also serve as failure detectors. The
stabilization component attempts to prune active lists that are larger
than A, say because of a slew of recent joins, and grow active lists
that are smaller than A because of some failures or previous inability
to neighbor with enough nodes.

When a node detects that its active list is too large, it queries the neighbors
for their active lists.
- If some neighbors have more than `C_rand` random neighbors, then links can be dropped
  with a `DISCONNECT` message until the size of the active list is A again.
- If the list is still too large, then it checks the active lists for neighbors that
  are connected with each other. In this case, one of the links can be dropped
  with a `DISCONNECT` message.
- If the list is still too large, then we cannot safely drop connections and it will
  remain that large until the next stabilization period.

When a node detects that its active list is too small, then it tries
to open more connections by picking nodes from its passive list, as
described in the Join section.

The optimization component tries to optimize the `C_near` connections
by replacing links with closer nodes. In order to do so, it takes RTT
samples from active list nodes and maintains a smoothed running
average. The neighbors are reordered by RTT and the closest ones are
considered the near nodes. It then checks the RTT samples of passive
list nodes and selects the closest node.  If the RTT is smaller by a
factor of alpha than a near neighbor and it has enough random
neighbors, then it disconnects and adopts the new node from the
passive list as a neighbor.

### Passive View Management

The passive list is managed cyclically, as per [2]. Periodically, with
a randomized timer, each node performs a passive list shuffle with one
of its active neighbors. The purpose of the shuffle is to update the
passive lists of the nodes involved. The node that iniates the shuffle
creates an exchange list that contains its id, `k_a` peers from its
active list and `k_p` peers from its passive list, where `k_a` and
`k_p` are protocol parameters (unspecified in [2]). It then sends a
`SHUFFLE` request to a random neighbor, which is propagated with a
random walk with an associated TTL.  If the TTL is greater than 0 and
the number of nodes in the receiver's active list is greater than 1,
then it propagates the request further. Otherwise, it selects nodes
from its passive list at random, sends back a `SHUFFLEREPLY` and
replaces them with the shuffle contents. The originating node
receiving the `SHUFFLEREPLY` also replaces nodes in its passive list
with the contents of the message. Care

should be taken for issues with transitive connectivity due to NAT. If
a node cannot connect to the originating node for a `SHUFFLEREPLY`,
then it should not perform the shuffle. Similarly, the originating
node could time out waiting for a shuffle reply and try with again
with a lower ttl, until a ttl of zero reuses the connection in the
case of NATed hosts.

In addition to shuffling, proximity awareness and leave cleanup
requires that we compute RTT samples and check connectivity to nodes
in the passive list.  Periodically, the node selects some nodes from
its passive list at random and tries to open a connection if it
doesn't already have one. It then checks that the peer is still
subscribed to the overlay. If the connection attempt is successful and
the node is still subscribed to the topic, it then updates the RTT
estimate for the peer in the list with a ping. Otherwise, it removes
it from the passive list for cleanup.


## Broadcast Protocol

### Broadcast State

Once it has joined the overlay, the node starts its main broadcast logic
loop. The loop receives messages to publish from the application, messages
published from other nodes, and with notifications from the management
protocol about new active neighbors and disconnections.

The state of the broadcast loop consists of two sets of peers, the eager
and lazy lists, with the eager list initialized to the initial neighbors
and the lazy list empty. The loop also maintains a time-based cache of
recent messages, together with a queue of lazy message notifications.
In addition to the cache, it maintains a list of missing messages 
known by lazy gossip but not yet received through the multicast tree.

### Message Propagation and Multicast Tree Construction

When a node publishes a message, it broadcasts a `GOSSIP` message with
a hopcount of 1 to all its eager peers, adds the message to the cache,
and adds the message id to the lazy notification queue.

When a node receives a `GOSSIP` message from a neighbor, first it
checks its cache to see if it has already seen this message. If the
message is in the cache, it prunes the edge of the multicast graph by
sending a `PRUNE` message to the peer, removing the peer from the
eager list, and adding it to the lazy list.

If the node hasn't seen the message before, it delivers the message to
the application and then adds the peer to the eager list and proceeds
to broadcast. The hopcount is incremented and then the node forwards
it to its eager peers, excluding the source. It also adds the message
to the cache, and pushes the message id to the lazy notification queue.

The loop runs a short periodic timer, with a period in the order of
0.1s for gossiping message summaries. Every time it fires, the node
flushes the lazy notification queue with all the recently received
message ids in an `IHAVE` message to its lazy peers.  The `IHAVE`
notifications summarize recent messages the node has seen and have not
propagated through the eager links.

### Multicast Tree Repair

When a failure occurs, at least one multicast tree branch is affected,
as messages are not transmitted by eager push.  The `IHAVE` messages
exchanged through lazy gossip are used both to recover missing messages
but also to provide a quick mechanism to heal the multicast tree.

When a node receives an `IHAVE` message for unknown messages, it
simply marks the messages as missing and places them to the missing
message queue. It then starts a timer and waits to receive the message
with eager push before the timer expires. The timer duration is a
protocol parameter that should be configured considering the diameter
of the overlay and the target recovery latency. A more realistic
implementation is to use a persistent timer heartbeat to check for
missing messages periodically, marking on first touch and considered
missing on the second timer touch.

When a message is detected as missing, the node selects the first
`IHAVE` announcement it has seen for the missing message and sends a
`GRAFT` message to the peer, piggybacking other missing messages. The
`GRAFT` message serves a dual purpose: it triggers the transmission of
the missing messages and on the same time adds the link to the
multicast tree, healing it.

Upon receiving a `GRAFT` message, a node adds the peer to the eager
list and transmits the missing messages from its cache as `GOSSIP`.
Note that the message is not removed from the missing list until it is
received as a response to a `GRAFT`. If the message has not been
received by the next timer tick, say because the grafted peer has
also failed, then another graft is attempted and so on, until enough
ticks have elapsed to consider the message lost.

### Multicast Tree Optimization

The multicast tree is constructed lazily, following the path of the
first published message from some source. Therefore, the tree does not
directly take advantage of new paths that may appear in the overlay as
a result of new nodes/links. The overlay may also be suboptimal for
all by the first source.

To overcome these limitations and adapt the overlay to multiple
sources, the authors in [1] propose an optimization: every time a
message is received, it is checked against the missing list and the
hopcount of messages in the list. If the eager transmission hopcount
exceeds the hopcount of the lazy transmission, then the tree is
candidate for optimization. If the tree were optimal, then the
hopcount for messages received by eager push should be less than or
equal to the hopcount of messages propagated by lazy push. Thus the
eager link can be replaced by the lazy link and result to a shorter
tree.

To promote stability in the tree, the authors in [1] suggest that this
optimization be peformed only if the difference in hopcount is greater
than a threshold value. This value is a design parameter that affects
the overall stability of the tree: the lower the value, the more
easier the protocol will try to optimize the tree by exchanging
links. But if the threshold value is too low, it may result in
fluttering with multiple active sources. Thus, the value should be
higher and closer to the diameter of the tree to avoid constant
changes.

### Active View Changes

The active peer list is maintained by the Membership Management protocol:
nodes may be removed because of failure or overlay reorganization, and new
nodes may be added to the list because of new connections. The Membership
Management protocol communicates these changes to the broadcast loop via
`NeighborUp` and `NeighborDown` notifications.

When a new node is added to the active list, the broadcast loop receives
a `NeighborUp` notifications, it simply adds the node to the eager peer
list. On the other hand, when a node is removed with a `NeighborDown`
notificaiton, the loop has to consider if the node was an eager or lazy
peer. If the node was a lazy peer, it doesn't need to do anything as the
departure does not affect the multicast tree. If the node was an eager peer
however, the loss of that edge may result in a disconnected tree.

There are two strategies in reaction to the loss of an eager peer. The
first one is to do nothing, and wait for lazy push to repair the tree
naturally with `IHAVE` messages in the next message broadcast. This
might result in delays propagating the next few messages but is
advocated by the authors in [1]. An alternative is to eagerly repair
the tree by promoting lazy peers to eager with empty `GRAFT` messages
and let the protocol prune duplicate paths naturally with `PRUNE`
messages in the next message transmission. This may have a bit of
bandwidth cost, but it is perhaps more appropriate for applications
that value latency minimization which is the case for many IPFS
applications.

## Protocol Messages

A quick summary of referenced protocol messages and their payload.
All messages are assumed to be enclosed in a suitable envelope and have
a source and monotonic sequence id.

```
;; Initial node discovery
GETNODES {}

NODES {
 peers []peer.ID
 ttl int
}

;; Topic querying (membership check for passive view management)
GETTOPICS {}

TOPICS {
 topics []topic.ID
}

;; Membership Management protocol
JOIN {
 peer peer.ID
 ttl int
}

FORWARDJOIN {
 peer peer.ID
 ttl int
}

NEIGHBOR {
 peers []peer.ID
}

DISCONNECT {}

LEAVE {
 source peer.ID
 ttl int
}

SHUFFLE {
 peer peer.ID
 peers []peer.ID
 ttl int
}

SHUFFLEREPLY {
 peers []peer.ID
}

;; Broadcast protocol
GOSSIP {
 source peer.ID
 hops int
 msg []bytes
}

IHAVE {
 summary []MessageSummary
}

MessageSummary {
 id message.ID
 hops int
}

PRUNE {}

GRAFT {
 msgs []message.ID
}

```

## Differences from Plumtree/HyParView

There are some noteworthy differences in the protocol described and
the published Plumtree/HyParView protocols. There might be some more
differences in minor details, but this document is written from a
practical implementer's point of view.

Membership Management protocol:
- The node views are managed with proximity awareness. The HyParView protocol
  has no provisions for proximity, these come from GoCast's implementation
  of proximity aware overlays; but note that we don't use UDP for RTT measurements
  and the increased `C_rand` to increase fault-tolerance at the price of some optimization.
- Joining nodes don't get to get all A connections by kicking out extant nodes,
  as this would result in overlay instability in periods of high churn. Instead, nodes
  ensure that the first few links are created even if they oversubscribe their fanout, but they
  don't go out of their way to create remaining links beyond the necessary `C_rand` links.
  Nodes later bring the active list to balance with a stabilization protocol.
  Also noteworthy is that only a single `JOIN` message is propagated with a random walk, the
  remaining joins are handled with normal `NEIGHBOR` requests.
  In short, the Join protocol is very much reworked, with the influence of GoCast.
- There is no active view stabilization/optimization protocol in HyParView. This is very
  much influenced from GoCast, where the protocol allows oversubscribing and later drops
  extraneous connections and replaces nodes for proximity optimization.
- `NEIGHBOR` messages play a dual role in the proposed protocol implementation, as they can
  be used to retrieve membership lists. 
- There is no connectivity check in HyParView and retires with reduced TTLs, but this
  is incredibly important in world  full of NAT.
- There is no `LEAVE` provision in HyParView.

Broadcast protocol:
- `IHAVE` messages are aggregated and lazily pushed via a background timer. Plumtree eagerly
  pushes `IHAVE` messages, which is wasteful and loses the opportunity for aggregation.
  The authors do suggest lazy aggregation as a possible optimization nonetheless.
- `GRAFT` messages similarly aggregate multiple message requests.
- Missing messages and overlay repair are managed by a single background timer instead of
  of creating timers left and right for every missing message; that's impractical from an
  implementation point of view, at least in Go.
- There is no provision for eager overlay repair on `NeighborDown` messages in Plumtree.
