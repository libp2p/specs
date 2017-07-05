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
- [Protocol Messages](#protocol-messages)

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
TTL and tries another starting node.  Once the first link has been
established, P then needs to increase its active list size to `A` by
connecting to more nodes.  This is accomplished by ordering the
subscriber list by RTT and picking the nearest nodes and
some nodes at random and sending `NEIGHBOR` requests.  The
neighbor requests may be accepted by `NEIGHBOR` message and rejected
by a `DISCONNECT` message.

Upon receiving a `NEIGHBOR` request a node Q evaluates it with the
followin criteria:
- If the size of P's active list is less than A, it accepts the new
  node.
- If P has not enough neighbors  (as specified in the message),
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
introduce a `LEAVE` message that eagerly propagates across the network.  A
node that wants to unsubscribe from the topic, emits a `LEAVE` to its
active list neighbors in place of `DISCONNECT`.  Upon receiving a
`LEAVE`, a node removes the node from its active list _and_ passive
lists. If the node was removed from one of the lists, then the `LEAVE`
is propagated further across the active list links. This will ensure a
random diffusion through the network that would clean most of the
active lists eagerly, at the cost of some bandwidth.

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
- If the list is still too large, then it picks nodes with at least 2 random links
  and drops the ones with the highest `D_rand`.
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
from its passive list at random, replaces them with the shuffle
contents, and sends back a `SHUFFLEREPLY`. The originating node
receiving the `SHUFFLEREPLY` also replaces nodes in its passive list
with the contents of the message.

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


## Protocol Messages