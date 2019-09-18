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
messages and gossip in order to provide behaviour optimized for specific
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
on the outbound degree of each peer and globally controling the amplification
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

Mesh links are bidirectional - when a peer recieves a `GRAFT` message informing
them that they have been added to another peer's mesh, they will in turn add the
peer to their own mesh, if it is still subscribed to the topic. In steady
state (after [message processing](#message-processing)), if a peer `A` is in the
mesh of peer `B`, then peer `B` is also in the mesh of peer `A`.

One shortcoming of the overlay mesh is that it necessarily offers a restricted
view of the global network. To allow peers to "reach beyond" their mesh view of
a topic, we use _gossip_ to propagate _metadata_ about the message flow
throughout the network. This gossip is emitted to a random subset of peers who
are not in the mesh.

The metadata can be arbitrary, but as a baseline, we send the [`IHAVE`
message](#ihave), which includes the message ids of messages we've seen in the
last few seconds. These messages are cached, so that peers receiving the gossip
can request them using an [`IWANT` message](#iwant).

The router can use this metadata to improve the mesh, for instance an
[episub](./episub.md) router built on top of gossipsub can create epidemic
broadcast trees, suitible for use cases in which a relatively small set of
publishers broadcasts to a much larger audience.

Other possible uses for gossip include restarting message transmission at
different points in the overlay to rectify downstream message loss, or
accelerating message transmission to peers who may be at some distant in the
mesh by opportunistically skipping hops.

## Dependencies

Pubsub is designed to fit into the libp2p "ecosystem" of modular components that
serve complemenatary purposes. As such, some key functionality is assumed to be
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
inform other libp2p subsytems (such as pubsub) of newly connected peers.

Whenever a new peer is connected, the gossipsub implementation checks to see if
the peer implements floodsub and/or gossipsub, and if so, it sends it a hello
packet that announces the topics that it is currently subscribing to.

## Parameters

## Router State

## Topic Membership

## Control Messages

### GRAFT

### PRUNE

### IHAVE

### IWANT

## Mesh Maintenance

### Heartbeat

[pubsub-interface-spec]: ../README.md
