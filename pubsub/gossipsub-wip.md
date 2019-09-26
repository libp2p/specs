# gossipsub: An extensible baseline pubsub protocol

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 3A              | Recommendation | Active | r1, 2018-08-29  |


Authors: [@vyzo]

Interest Group: [@yusefnapora], [@raulk], [@whyrusleeping], [@Stebalien],
[@jamesray1], [@vasco-santos]

[@whyrusleeping]: https://github.com/whyrusleeping
[@yusefnapora]: https://github.com/yusefnapora
[@raulk]: https://github.com/raulk
[@vyzo]: https://github.com/vyzo
[@Stebalien]: https://github.com/Stebalien
[@jamesray1]: https://github.com/jamesray1
[@vasco-santos]: https://github.com/vasco-santos

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

---

## Overview

This is the specification for an extensible pubsub protocol over libp2p, based
on randomized topic meshes and gossip. It is a general purpose pubsub protocol
with moderate amplification factors and good scaling properties. The protocol is
designed to be extensible by more specialized routers, which may add protocol
messages and gossip in order to provide behavior optimized for specific
application profiles.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Contents**


<!-- END doctoc generated TOC please keep comment here to allow auto update -->


## Motivations and Prior Work

The libp2p [pubsub interface specification][pubsub-interface-spec] defines the
RPC messages exchanged by peers, but deliberately does not define routing
semantics, connection management, or other specifics of how peers interact. This
is left to specific pubsub protocols, allowing a great deal of flexibility in
protocol design to support different use cases.

Before [introducing gossipsub itself](#gossipsub-the-gossiping-mesh-router),
let's first examine the properties of `floodsub`, the simplest pubsub
implementation.

### In the beginning was floodsub

The initial implementation of the pubsub interface was `floodsub`, which adopts a
very simple message propagation strategy - it simply "floods" the network by
having every peer broadcast to every other peer they know about in a given
topic.

With flooding, routing is almost trivial: for each incoming message, forward to
all known peers in the topic. There is a bit of logic, as the router maintains a
timed cache of previous messages, so that seen messages are not further
forwarded. It also never forwards a message back to the source or the peer that
forwarded the message.

The floodsub routing strategy has the following highly desirable properties:

- It is straightforward to implement.
- It minimizes latency; messages are delivered across minimum latency paths, so
  long as the overlay is sufficiently well connected.
- It is highly robust; there is very little maintenance logic or state to
  manage.
  
The problem however is that messages don't just follow the minimum latency
paths; they follow all edges, thus creating a flood. The outbound degree of the
network is unbounded, whereas we want it to be bounded in order to reduce
bandwidth requirements and increase decentralization and scalability. 

This unbounded outbound degree creates a problem for individual densely
connected nodes, as they may have a large number of connected peers and cannot
afford the bandwidth to forward all these pubsub messages. Similarly, the
amplification factor is only bounded by the sum of degrees of all nodes in the
overlay, which creates a scaling problem for densely connected overlays at
large.

## gossipsub: The gossiping mesh router

gossipsub addresses the key shortcomings of floodsub by imposing an upper bound
on the outbound degree of each peer and globally controlling the amplification
factor.

In order to do so, gossipsub peers form an overlay mesh, in which each peer
forwards messages to a subset of its peers, rather than all known peers in a
topic. The mesh is constructed by peers as they join a pubsub topic, and it is
maintained over time by the exchange of [control messages](#control-messages).

The initial construction of the mesh is random. When a peer joins a new topic,
it will examine its [local state](#router-state) to find other peers that it
knows to be members of the topic. It will then select a subset of the topic
members, up to a maximum of `D`, which is a configurable
[parameter](#parameters) representing the desired degree of the network. These
will be added to the mesh for that topic, and the newly added peers will be
notified with a [`GRAFT` control message](#graft).

Upon leaving a topic, a peer will notify the members of its mesh with a [`PRUNE`
message](#prune) and remove the mesh from its [local state](#router-state).
[Further maintenance](#mesh-maintenance) is performed periodically as part of
the [heartbeat procedure](#heartbeat) to keep the mesh size within acceptable
bounds as peers come and go.

Mesh links are bidirectional - when a peer receives a `GRAFT` message informing
them that they have been added to another peer's mesh, they will in turn add the
peer to their own mesh, assuming they are still subscribed to the topic. In
steady state (after [message processing](#message-processing)), if a peer `A` is
in the mesh of peer `B`, then peer `B` is also in the mesh of peer `A`.

To allow peers to "reach beyond" their mesh view of a topic, we use _gossip_ to
propagate _metadata_ about the message flow throughout the network. This gossip
is emitted to a random subset of peers who are not in the mesh. We can think of
the mesh members as "full message" peers, to whom we propagate the full content
of all messages received in a topic. The remaining peers we're aware of in a
topic can be considered "metadata-only" peers, to whom we emit gossip at
[regular intervals](#heartbeat).

The metadata can be arbitrary, but as a baseline, we send the [`IHAVE`
message](#ihave), which includes the message ids of messages we've seen in the
last few seconds. These messages are cached, so that peers receiving the gossip
can request them using an [`IWANT` message](#iwant).

The router can use this metadata to improve the mesh, for instance an
[episub](./episub.md) router built on top of gossipsub can create epidemic
broadcast trees, suitable for use cases in which a relatively small set of
publishers broadcasts to a much larger audience.

Other possible uses for gossip include restarting message transmission at
different points in the overlay to rectify downstream message loss, or
accelerating message transmission to peers who may be at some distant in the
mesh by opportunistically skipping hops.

## Dependencies

Pubsub is designed to fit into the libp2p "ecosystem" of modular components that
serve complementary purposes. As such, some key functionality is assumed to be
present and is not specified as part of pubsub itself.

### Ambient Peer Discovery

Before peers can exchange pubsub messages, they must first become aware of each
others' existence. There are several practical peer discovery mechanisms that
can be employed, for example, randomly walking a DHT, rendezvous protocols, etc.

As peer discovery is broadly useful and not specific to pubsub, neither the
[pubsub interface spec][pubsub-interface-spec] nor this document prescribe a
particular discovery mechanism. Instead, this function is assumed to be provided
by the environment. A pubsub-enabled libp2p application must also be configured
with a peer discovery mechanism, which will send ambient connection events to
inform other libp2p subsystems (such as pubsub) of newly connected peers.

Whenever a new peer is connected, the gossipsub implementation checks to see if
the peer implements floodsub and/or gossipsub, and if so, it sends it a hello
packet that announces the topics that it is currently subscribing to.

## Parameters

This section lists the configurable parameters that control the behavior of
gossipsub, along with a short description and reasonable defaults. Each
parameter is introduced with full context elsewhere in this document.

| Parameter            | Purpose                                               | Reasonable Default |
|----------------------|-------------------------------------------------------|--------------------|
| `D`                  | The desired outbound degree of the network            | 6                  |
| `D_low`              | Lower bound for outbound degree                       | 4                  |
| `D_high`             | Upper bound for outbound degree                       | 12                 |
| `heartbeat_interval` | Time between [heartbeats](#heartbeat)                 | 1 second           |
| `fanout_ttl`         | Time-to-live for each topic's fanout state            | 60 seconds         |
| `mcache_len`         | Number of history windows in message cache            | 5                  |
| `mcache_gossip`      | Number of history windows to use when emitting gossip | 3                  |
| `seen_ttl`           | Expiry time for cache of seen message ids             | 2 minutes          |

## Router State

The router keeps track of some necessary state to maintain stable topic meshes
and emit useful gossip.

The state can be roughly divided into two categories: [peering
state](#peering-state), and state related to the [message cache](#message-cache).

### Peering State

Peering state is how the router keeps track of the pubsub-capable peers it's
aware of and the relationship with each of them.

There are three main pieces of peering state:

- `peers` is a set of ids of all known peers that support gossipsub or floodsub.
  Throughout this document `peers.gossipsub` will denote peers supporting
  gossipsub, while `peers.floodsub` denotes floodsub peers.
  
- `mesh` is a map of subscribed topics to the set of peers in our overlay mesh
  for that topic.

- `fanout`, like `mesh`, is a map of topics to a set of peers, however, the
  `fanout` map contains topics to which we _are not_ subscribed.

In addition to the gossipsub-specific state listed above, the libp2p pubsub
implementation maintains some "router-agnostic" state. This includes the set of
topics to which we are subscribed, as well as the set of topics to which each of
our peers is subscribed.

### Message Cache

The message cache (or `mcache`), is a data structure that stores message IDs and
their corresponding messages, segmented into "history windows." Each window
corresponds to one heartbeat interval, and the windows are shifted during the
[heartbeat procedure](#heartbeat) following [gossip emission](#gossip-emission).

The message cache supports the following operations:

- `mcache.put(m)`: adds a message to the current window and the cache.
- `mcache.get(id)`: retrieves a message from the cache by its ID, if it is still present.
- `mcache.window()`: retrieves the message IDs for messages in the current history window.
- `mcache.shift()`: shifts the current window, discarding messages older than the
   history length of the cache.

We also keep a `seen` cache, which is a timed least-recently-used cache of
message IDs that we have observed recently. The value of "recently" is
determined by the [parameter](#parameter) `seen_ttl`, with a reasonable default
of two minutes. This value should be chosen to approximate the propagation delay
in the overlay, within a healthy margin.

The `seen` cache serves two purposes. In all pubsub implementations, we can
first check the `seen` cache before forwarding messages to avoid wastefully
republishing the same message multiple times. For gossipsub in particular, the
`seen` cache is used when processing an [`IHAVE` message](#ihave) sent by
another peer, so that we only request messages we have not already seen before.

In the go implementation, the `seen` cache is provided by the pubsub framework
and is separate from the `mcache`, however other implementations may wish to
combine them into one data structure.

## Topic Membership



## Control Messages

### GRAFT

### PRUNE

### IHAVE

### IWANT

## Message Processing

## Heartbeat

Each peer runs a periodic stabilization process called the "heartbeat procedure"
at regular intervals. The frequency of the heartbeat is controlled by the
[parameter](#parameters) `H`, with a reasonable default of 1 second.

The heartbeat serves three functions: [mesh maintenance](#mesh-maintenance),
[fanout maintenance](#fanout-maintenance), and [gossip
emission](#gossip-emission).

### Mesh Maintenance

### Fanout Maintenance

### Gossip Emission

[pubsub-interface-spec]: ../README.md
