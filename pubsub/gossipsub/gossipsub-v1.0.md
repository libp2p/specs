# gossipsub: An extensible baseline pubsub protocol

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 3A              | Recommendation | Active | r1, 2018-08-29  |


Authors: [@vyzo]

Editor: [@yusefnapora]

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

- [Motivations and Prior Work](#motivations-and-prior-work)
  - [In the beginning was floodsub](#in-the-beginning-was-floodsub)
- [gossipsub: The gossiping mesh router](#gossipsub-the-gossiping-mesh-router)
- [Dependencies](#dependencies)
  - [Ambient Peer Discovery](#ambient-peer-discovery)
- [Parameters](#parameters)
- [Router State](#router-state)
  - [Peering State](#peering-state)
  - [Message Cache](#message-cache)
- [Topic Membership](#topic-membership)
- [Control Messages](#control-messages)
  - [GRAFT](#graft)
  - [PRUNE](#prune)
  - [IHAVE](#ihave)
  - [IWANT](#iwant)
- [Message Processing](#message-processing)
- [Control Message Piggybacking](#control-message-piggybacking)
- [Heartbeat](#heartbeat)
  - [Mesh Maintenance](#mesh-maintenance)
  - [Fanout Maintenance](#fanout-maintenance)
  - [Gossip Emission](#gossip-emission)
- [Protobuf](#protobuf)

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
| `D_lazy`             | (Optional) the outbound degree for gossip emission    | `D`                |
| `heartbeat_interval` | Time between [heartbeats](#heartbeat)                 | 1 second           |
| `fanout_ttl`         | Time-to-live for each topic's fanout state            | 60 seconds         |
| `mcache_len`         | Number of history windows in message cache            | 5                  |
| `mcache_gossip`      | Number of history windows to use when emitting gossip | 3                  |
| `seen_ttl`           | Expiry time for cache of seen message ids             | 2 minutes          |

Note that `D_lazy` is considered optional. It is used to control the outbound
degree when [emitting gossip](#gossip-emission), which may be tuned separately
than the degree for eager message propagation. By default, we simply use `D` for
both.

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
framework maintains some "router-agnostic" state. This includes the set of
topics to which we are subscribed, as well as the set of topics to which each of
our peers is subscribed. Elsewhere in this document, we refer to
`peers.floodsub[topic]` and `peers.gossipsub[topic]` to denote floodsub or
gossipsub capable peers within a specific topic.

### Message Cache

The message cache (or `mcache`), is a data structure that stores message IDs and
their corresponding messages, segmented into "history windows." Each window
corresponds to one heartbeat interval, and the windows are shifted during the
[heartbeat procedure](#heartbeat) following [gossip emission](#gossip-emission).
The number of history windows to keep is determined by the `mcache_len`
[parameter](#parameters), while the number of windows to examine when sending
gossip is controlled by `mcache_gossip`.

The message cache supports the following operations:

- `mcache.put(m)`: adds a message to the current window and the cache.
- `mcache.get(id)`: retrieves a message from the cache by its ID, if it is still present.
- `mcache.get_gossip_ids(topic)`: retrieves the message IDs for messages in the
  most recent history windows, scoped to a given topic. The number of windows to
  examine is controlled by the `mcache_gossip` parameter.
- `mcache.shift()`: shifts the current window, discarding messages older than the
   history length of the cache (`mcache_len`).

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

The [pubsub interface spec][pubsub-interface-spec] defines the baseline RPC
message format used by all libp2p pubsub routers. As part of the RPC message,
peers can include announcements regarding the topics they wish to subscribe to
or unsubscribe from. These announcements are sent to all known pubsub-capable
peers, regardless of whether we currently have any topics in common.

For this document, we assume that the underlying pubsub framework is responsible
for sending the RPC messages announcing subscription changes. A gossipsub
implementation that does not build upon an existing libp2p pubsub framework
would need to implement those control RPC messages.

In addition to the `SUBSCRIBE` / `UNSUBSCRIBE` events sent by the pubsub
framework, gossipsub must do additional work to maintain the mesh for the topic
it is joining or leaving. We will refer to the two topic membership operations
below as `JOIN(topic)` and `LEAVE(topic)`.

When the application invokes `JOIN(topic)`, the router will form a topic mesh by
selecting up to [`D`](#parameters) peers from its [local peering
state](#peering-state) first examining the `fanout` map. If there are peers in
`fanout[topic]`, the router will move those peers from the `fanout` map to
`mesh[topic]`. If the topic is not in the `fanout` map, or if `fanout[topic]`
contains fewer than `D` peers, the router will attempt to fill `mesh[topic]`
with peers from `peers.gossipsub[topic]` which is the set of all
gossipsub-capable peers it is aware of that are members of the topic.

Regardless of whether they came from `fanout` or `peers.gossipsub`, the router
will inform the new members of `mesh[topic]` that they have been added to the
mesh by sending them a [`GRAFT` control message](#graft).

The application can invoke `LEAVE(topic)` to unsubscribe from a topic. The
router will inform the peers in `mesh[topic]` by sending them a [`PRUNE` control
message](#prune), so that they can remove the link from their own topic mesh.
After sending `PRUNE` messages, the router will forget `mesh[topic]` and delete
it from its local state.

## Control Messages

Control messages are exchanged to maintain topic meshes and emit gossip. This
section lists the control messages in the core gossipsub protocol, although it
is worth noting that extensions to gossipsub (such as [episub](./episub) may
define further control messages for their own purposes.

For details on how gossipsub routers respond to control messages, see [Message
Processing](#message-processing).

The [protobuf](https://developers.google.com/protocol-buffers) schema for
control messages is detailed in the [Protobuf](#protobuf) section.

### GRAFT

The `GRAFT` message grafts a new link in a topic mesh. The `GRAFT` informs a peer
that it has been added to the local router's mesh view for the included topic id.

### PRUNE

The `PRUNE` message prunes a mesh link from a topic mesh. `PRUNE` notifies a
peer that it has been removed from the local router's mesh view for the
included topic id.

### IHAVE

The `IHAVE` message is [emitted as gossip](gossip-emission). It provides the
remote peer with a list of messages that were recently seen by the local router.
The remote peer may then request the full message content with an [`IWANT` message](#iwant).

### IWANT

The `IWANT` message requests the full content of one or more messages whose IDs
were announced by a remote peer in an [`IHAVE` message](#ihave).

## Message Processing

Upon receiving a message, the router will first process the message payload.
Payload processing will validate the message according to application-defined
rules and check the [`seen` cache](#message-cache) to determine if the message
has been processed previously. It will also ensure that it was not the source of
the message; if the router receives a message that it published itself, it will
not forward it further.

If the message is valid, was not published by the router itself, and has not
been previously seen, the router will forward the message. First, it will
forward the message to every peer in `peers.floodsub[topic]` for
backwards-compatibility with [floodsub](#in-the-beginning-was-floodsub). Next,
it will forward the message to every peer in its local gossipsub topic mesh,
contained in `mesh[topic]`.

After processing the message payload, the router will process the control
messages:

- On receiving a [`GRAFT(topic)` message](#graft), the router will check to see
  if it is indeed subscribed to the topic identified in the message. If so, the
  router will add the sender to `mesh[topic]`. If the router is no longer
  subscribed to the topic, it will respond with a [`PRUNE(topic)`
  message](#prune) to inform the sender that it should remove its mesh link.

- On receiving a [`PRUNE(topic)` message](#prune), the router will remove the
  sender from `mesh[topic]`.

- On receiving an [`IHAVE(ids)` message](#ihave), the router will check it's
  `seen` cache. If the `IHAVE` message contains message IDs that have not been
  seen, the router will request them with an `IWANT` message.

- On receiving an [`IWANT(ids)` message](#iwant), the router will check its
  [`mcache`](#message-cache) and will forward any requested messages that are
  present in the `mcache` to the peer who sent the `IWANT` message.

Apart from forwarding received messages, the router can of course publish
messages on its own behalf, which originate at the application layer. This is
very similar to forwarding received messages:

- First, the message is sent to every peer in `peers.floodsub[topic]`.
- If the router is subscribed to the topic, it will send the message to all
  peers in `mesh[topic]`.
- If the router is not subscribed to the topic, it will examine the set of peers
  in `fanout[topic]`. If this set is empty, the router will choose up to `D`
  peers from `peers.gossipsub[topic]` and add them to `fanout[topic]`. Assuming
  there are now some peers in `fanout[topic]`, the router will send the message
  to each.

## Control Message Piggybacking

Gossip and other control messages do not have to be transmitted in their own
message. Instead, they can be coalesced and piggybacked on any other message in
the regular flow, for any topic. This can lead to message rate reduction
whenever there is some correlated flow between topics, which can be significant
for densely connected peers.

For piggyback implementation details, consult the [Go
implementation](https://github.com/libp2p/go-libp2p-pubsub/blob/master/gossipsub.go).

## Heartbeat

Each peer runs a periodic stabilization process called the "heartbeat procedure"
at regular intervals. The frequency of the heartbeat is controlled by the
[parameter](#parameters) `heartbeat_interval`, with a reasonable default of 1
second.

The heartbeat serves three functions: [mesh maintenance](#mesh-maintenance),
[fanout maintenance](#fanout-maintenance), and [gossip
emission](#gossip-emission).

### Mesh Maintenance

Topic meshes are maintained with the following stabilization algorithm:

```
for each topic in mesh:
 if |mesh[topic]| < D_low:
   select D - |mesh[topic]| peers from peers.gossipsub[topic] - mesh[topic]
    ; i.e. not including those peers that are already in the topic mesh.
   for each new peer:
     add peer to mesh[topic]
     emit GRAFT(topic) control message to peer

 if |mesh[topic]| > D_high:
   select |mesh[topic]| - D peers from mesh[topic]
   for each new peer:
     remove peer from mesh[topic]
     emit PRUNE(topic) control message to peer
```

The [parameters](#parameters) of the algorithm are:

- `D`: the desired outbound degree of the network
- `D_low`: an acceptable lower threshold for `D`. If there are fewer than
  `D_low` peers in a given topic mesh, we attempt to add new peers.
- `D_high`: an acceptable upper threshold for `D`. If there are more than
  `D_high` peers in a given topic mesh, we randomly select peers for removal.

### Fanout Maintenance

The `fanout` map is maintained by keeping track of the last published time for
each topic. If we do not publish any messages to a topic within a configurable
TTL, the fanout state for that topic is discarded.

We also try to ensure that each `fanout[topic]` set has at least `D` members.

The fanout maintenance algorithm is:

```
for each topic in fanout:
  if time since last published > fanout_ttl
    remove topic from fanout
  else if |fanout[topic]| < D
    select D - |fanout[topic]| peers from peers.gossipsub[topic] - fanout[topic]
    add the peers to fanout[topic]
```

The [parameters](#parameters) of the algorithm are:

- `D`: the desired outbound degree of the network.
- `fanout_ttl`: the time for which we keep the fanout state for each topic. If
  we do not publish to a topic within `fanout_ttl`, the `fanout[topic]` set is
  discarded.

### Gossip Emission

Gossip is emitted to a random selection of peers for each topic that are not
already members of the topic mesh:

```
for each topic in mesh+fanout:
  let mids be mcache.get_gossip_ids(topic)
  if mids is not empty:
    select D peers from peers.gossipsub[topic]
    for each peer not in mesh[topic] or fanout[topic]
      emit IHAVE(mids)

shift the mcache
```

Note that we use the same parameter `D` as the target degree for both gossip and
mesh membership, however this is not normative. A separate parameter `D_lazy`
can be used to explicitly control the gossip propagation factor, which allows
for tuning the tradeoff between eager and lazy transmission of messages.

## Protobuf

The gossipsub protocol extends the [existing `RPC` message
structure][pubsub-spec-rpc] with a new field, `control`. This is an instance of
`ControlMessage` which may contain one or more control messages.

The four control messages are `ControlIHave` for [`IHAVE`](#ihave) messages,
`ControlIWant` for [`IWANT`](#iwant) messages, `ControlGraft` for
[`GRAFT`](#graft) messages and `ControlPrune` for [`PRUNE`](#prune) messages.

The protobuf is as follows:

```protobuf
message RPC {
    // ... see definition in pubsub interface spec
	optional ControlMessage control = 3;
}

message ControlMessage {
	repeated ControlIHave ihave = 1;
	repeated ControlIWant iwant = 2;
	repeated ControlGraft graft = 3;
	repeated ControlPrune prune = 4;
}

message ControlIHave {
	optional string topicID = 1;
	repeated string messageIDs = 2;
}

message ControlIWant {
	repeated string messageIDs = 1;
}

message ControlGraft {
	optional string topicID = 1;
}

message ControlPrune {
	optional string topicID = 1;
}
```

[pubsub-interface-spec]: ../README.md
[pubsub-spec-rpc]: ../README.md#the-rpc
