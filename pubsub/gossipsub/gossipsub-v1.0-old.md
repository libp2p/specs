# gossipsub v1.0 (OLD): An extensible baseline pubsub protocol

> `DISCLAIMER:` This is the original specification, please refer to [gossipsub-v1.0](gossipsub-v1.0.md) from now on

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 3A              | Recommendation | Active | r1, 2018-08-29  |

Authors: [@vyzo]
Interest Group: [@yusefnapora], [@raulk], [@whyrusleeping], [@Stebalien], [@jamesray1], [@vasco-santos], [@daviddias], [@yiannisbot]

[@whyrusleeping]: https://github.com/whyrusleeping
[@yusefnapora]: https://github.com/yusefnapora
[@raulk]: https://github.com/raulk
[@vyzo]: https://github.com/vyzo
[@Stebalien]: https://github.com/Stebalien
[@jamesray1]: https://github.com/jamesray1
[@vasco-santos]: https://github.com/vasco-santos
[@daviddias]: https://github.com/daviddias
[@yiannisbot]: https://github.com/yiannisbot

See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

---

This is the specification for an extensible baseline pubsub protocol,
based on randomized topic meshes and gossip. It is a general purpose
pubsub protocol with moderate amplification factors and good scaling
properties. The protocol is designed to be extensible by more
specialized routers, which may add protocol messages and gossip in
order to provide behaviour optimized for specific application
profiles.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Contents**

- [Implementation status](#implementation-status)
- [Context - In the beginning was floodsub](#context--in-the-beginning-was-floodsub)
  - [Ambient Peer Discovery](#ambient-peer-discovery)
  - [Flood routing](#flood-routing)
  - [Retrospective](#retrospective)
- [Proposed alternatives - Controlling the flood](#proposed-alternatives--controlling-the-flood)
  - [randomsub: A random message router](#randomsub-a-random-message-router)
  - [meshsub: An overlay mesh router](#meshsub-an-overlay-mesh-router)
  - [gossipsub: The gossiping mesh router](#gossipsub-the-gossiping-mesh-router)
- [Protocol Architecture - Gossipsub](#protocol-architecture--gossipsub)
  - [Control messages](#control-messages)
  - [Router state](#router-state)
  - [Topic membership](#topic-membership)
  - [Message processing](#message-processing)
  - [Heartbeat](#heartbeat)
  - [Control message piggybacking](#control-message-piggybacking)
  - [Protobuf](#protobuf)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Context - In the beginning was floodsub

The initial pubsub experiment in libp2p was `floodsub`.
It implements pubsub in the most basic manner, with two defining aspects:
- ambient peer discovery; and
- most basic routing: flooding.

### Ambient Peer Discovery

With ambient peer discovery, the function is pushed outside the scope of the
protocol. Instead, the mechanism for discovering peers is provided for by the
environment. In practice, this can be embodied by DHT walks, rendezvous
points, etc. This protocol relies on the ambient connection events produced by
such mechanisms. Whenever a new peer is connected, the protocol checks to see
if the peer implements floodsub and/or gossipsub, and if so, it sends it a
hello packet that announces the topics that it is currently subscribing to.

This allows the peer to maintain soft overlays for all topics of
interest. The overlay is maintained by exchanging subscription
control messages whenever there is a change in the topic list. The
subscription messages are not propagated further, so each peer
maintains a topic view of its direct peers only. Whenever a peer
disconnects, it is removed from the overlay.

Ambient peer discovery can be driven by arbitrary external means, which
allows orthogonal development and no external dependencies for the protocol
implementation.

There are a couple of options we are exploring as canonical approaches
for the discovery driver:
- DHT rendezvous using provider records; peers in the topic announce
  a provider record named after the topic.
- Rendezvous through known or dynamically discovered rendezvous points.

### Flood routing

With flooding, routing is almost trivial: for each incoming message,
forward to all known peers in the topic. There is a bit of logic, as
the router maintains a timed cache of previous messages, so that seen
messages are not further forwarded. It also never forwards a message
back to the source or the peer that forwarded the message.

### Retrospective

Evaluating floodsub as a viable pubsub protocol reveals the following
highly desirable properties:
- it is straightforward to implement.
- it minimizes latency; messages are delivered across minimum latency
  paths, modulo overlay connectivity.
- it is highly robust; there is very little maintenance logic or state.

The problem however is that messages don't just follow the minimum
latency paths; they follow all edges, thus creating a flood. The
outbound degree of the network is unbounded, whereas we want it to be
bounded in order to reduce bandwidth requirements and increase
decentralization and scalability. In other words, this unbounded
outbound degree creates a problem for individual densely connected
nodes, as they may have a large number of connected peers and cannot
afford the bandwidth to forward all these pubsub messages.  Similary,
the amplification factor is only bounded by the sum of degrees of all
nodes in the overlay, which creates a scaling problem for densely
connected overlays at large.

## Proposed alternatives - Controlling the flood

In order to scale pubsub without excessive bandwidth waste or peer
overload, we need a router that bounds the degree of each peer and
globally controls the amplification factor.

### randomsub: A random message router

Let's first consider the simplest bounded floodsub variant, which we
call `randomsub`. In this construction, the router is still stateless,
apart from a list of known peers in the topic. But instead of
forwarding messages to all peers, it forwards to a random subset of up
to `D` peers, where `D` is the desired degree of the network.

The problem with this construction is that the message propagation
patterns are non-deterministic. This results in extreme message route
instability, manifesting as message reordering and varying timing patterns,
which is an undesirable property for many applications.

### meshsub: An overlay mesh router

Nonetheless, the idea of limiting the flow of messages to a random
subset of peers is solid. But instead of randomly selecting peers on a
per message basis, we can form an overlay mesh where each peer
forwards to a subset of its peers on a stable basis. We construct a
router in this fashion, dubbed `meshsub`.

Each peer maintains its own view of the mesh for each topic, which is
a list of bidirectional links to other peers.  That is, in steady
state, whenever a peer A is in the mesh of peer B, then peer B is also
in the mesh of peer A.

The overlay is initially constructed in a random fashion. Whenever a
peer joins a topic, then it selects `D` peers (in the topic) at random
and adds them to the mesh, notifying them with a control message. When
it leaves the topic, it notifies its peers and forgets the mesh for
the topic.

The mesh is maintained with the following periodic stabilization
algorithm:

```
at each peer:
  loop:
    if |peers| < D_low:
       select D - |peers| non-mesh peers at random and add them to the mesh
    if |peers| > D_high:
       select |peers| - D mesh peers at random and remove them from the mesh
    sleep t
```
The parameters of the algorithm are `D` which is the target degree,
and two relaxed degree parameters `D_low` and `D_high` which represent
admissible mesh degree bounds.

### gossipsub: The gossiping mesh router

The meshsub router offers a baseline construction with good amplification
control properties, which we augment with _gossip_ about message flow.
The gossip is emitted to random subsets of peers not in the mesh, similar
to randomsub, and it allows us to propagate _metadata_ about message flow
throughout the network. The metadata can be arbitrary, but as a baseline
we include the message ids of seen messages in the last few seconds.
The messages are cached, so that peers receiving the gossip can request
them for transmission with a control message.

The router can use this metadata to improve the mesh, for instance an
[episub](episub.md) router built on top of gossipsub can create
epidemic broadcast trees.  Beyond that, the metadata can restart
message transmission at different points in the overlay to rectify
downstream message loss. Or it can simply jump hops opportunistically
and accelerate message transmission for peers who are at some distance
in the mesh.

Essentially, gossipsub is a blend of meshsub for data and randomsub
for mesh metadata. It provides bounded degree and amplification factor
with the meshsub construction and augments it using gossip propagation
of metadata with the randomsub technique.


## Protocol Architecture - Gossipsub

We can now provide a specification of the pubsub protocol by sketching
out the router implementation.  The router is backwards compatible
with floodsub, as it accepts floodsub peers and behaves like floodsub
towards them.

If you would like to get a video presentation and visualization on Gossipsub, watch [Scalable PubSub with GossipSub - Dimitris Vyzovitis](https://www.youtube.com/watch?v=mlrf1058ENY&index=3&list=PLuhRWgmPaHtRPl3Itt_YdHYA0g0Eup8hQ) from the [IPFS London Hack Week of 2018 Q4](http://gateway.ipfs.io/ipns/blog.ipfs.io/65-london-hack-week-report/).

### Control messages

The protocol defines four control messages:
- `GRAFT`: graft a mesh link; this notifies the peer that it has been added to the local mesh view.
- `PRUNE`: prune a mesh link; this notifies the peer that it has been removed from the local mesh view.
- `IHAVE`: gossip; this notifies the peer that the following messages were recently seen and are available on request.
- `IWANT`: request transmission of messages announced in an `IHAVE` message.

### Router state

The router maintains the following state:
- `peers`: a set of all known peers; `peers.gossipsub` denotes the gossipsub peers
   while `peers.floodsub` denotes the floodsub peers.
- `mesh`: the overlay meshes as a map of topics to lists of peers.
- `fanout`: the mesh peers to which we are publishing to without topic membership,
   as a map of topics to lists of peers.
- `seen`: this is the timed message ID cache, which tracks seen messages.
- `mcache`: a message cache that contains the messages for the last few
   heartbeat ticks.

The message cache is a data structure that stores windows of message IDs
and the corresponding messages. It supports the following operations:
- `mcache.put(m)`: adds a message to the current window and the cache.
- `mcache.get(id)`: retrieves a message from the cache by its ID, if it is still present.
- `mcache.window()`: retrieves the message IDs for messages in the current history window.
- `mcache.shift()`: shifts the current window, discarding messages older than the
   history length of the cache.

The `seen` cache is the flow control mechanism. It tracks
the message IDs of seen messages for the last two minutes. It is
separate from `mcache` for implementation reasons in Go (the `seen`
cache is inherited from the pubsub framework), but they could be the
same data structure. Note that the two minute cache interval is non-normative;
a router could use a different value, chosen to approximate the propagation
delay in the overlay with some healthy margin.

### Topic membership

Topic membership is controlled by two operations supported by the
router, as part of the pubsub api:
- On `JOIN(topic)` the router joins the topic. In order to do so, if it already has
  `D` peers from the `fanout` peers of a topic, then it adds them to `mesh[topic]`,
  and notifies them with a `GRAFT(topic)` control message. Otherwise, if there are
  less than `D` peers (let this number be `x`) in the fanout for a topic (or the
  topic is not in the fanout), then it
  still adds them as above (if there are any), and selects the remaining number
  of peers (`D-x`) from `peers.gossipsub[topic]`, and likewise adds them to
  `mesh[topic]` and notifies them with a `GRAFT(topic)` control message.
- On `LEAVE(topic)` the router leaves the topic. It notifies the peers in
  `mesh[topic]` with a `PRUNE(topic)` message and forgets `mesh[topic]`.

Note that the router can publish messages without topic membership. In order
to maintain stable routes in that case, it maintains a list of peers for each
topic it has published in the `fanout` map. If the router does not publish any
messages of a topic for some time, then the `fanout` peers for that topic are
forgotten, so this is soft state.

Also note that as part of the pubsub api, the peer emits `SUBSCRIBE`
and `UNSUBSCRIBE` control messages to all its peers whenever it joins
or leaves a topic. This is provided by the the ambient peer discovery
mechanism and nominally not part of the router. A standalone
implementation would have to implement those control messages.

### Message processing

Upon receiving a message, the router first processes the payload of the message.
If it contains a valid message that has not been previously seen, then
it publishes the message:
- It forwards the message to every peer in `peers.floodsub[topic]`, provided it's not
  the source of the message.
- It forwards the message to every peer in `mesh[topic]`, provided it's not the
  source of the message.

After processing the payload, it then processes the control messages in the envelope:
- On `GRAFT(topic)` it adds the peer to `mesh[topic]` if it is
  subscribed to the topic. If it is not subscribed, it responds with a `PRUNE(topic)`
  control message.
- On `PRUNE(topic)` it removes the peer from `mesh[topic]`.
- On `IHAVE(ids)` it checks the `seen` set and requests unknown messages with an `IWANT`
   message.
- On `IWANT(ids)` it forwards all request messages that are present in `mcache` to the
   requesting peer.

When the router publishes a message that originates from the router itself (at the
application layer), then it proceeds similarly to the payload reaction:
- It forwards the message to every peer in `peers.floodsub[topic]`.
- If it is subscribed to the topic, then it must have a set of peers in `mesh[topic]`,
  to which the message is forwarded.
- If it is not subscribed to the topic, it then forwards the message to
  the peers in `fanout[topic]`. If this set is empty, it chooses `D` peers from
  `peers.gossipsub[topic]` to become the new `fanout[topic]` peers and forwards
  to them.

### Heartbeat

The router periodically runs a heartbeat procedure, which is
responsible for maintaining the mesh, emitting gossip, and shifting
the message cache.

The `mesh` is maintained exactly as prescribed by `meshsub`:
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

The `fanout` map is maintained by keeping track of the last published time
for each topic:
```
for each topic in fanout:
  if time since last published > ttl
    remove topic from fanout
  else if |fanout[topic]| < D
    select D - |fanout[topic]| peers from peers.gossipsub[topic] - fanout[topic]
    add the peers to fanout[topic]
```

Gossip is emitted by selecting peers for each topic that are not already part
of the mesh:
```
for each topic in mesh+fanout:
  let mids be mcache.window[topic]
  if mids is not empty:
    select D peers from peers.gossipsub[topic] not in mesh[topic] or fanout[topic]
    for each peer
      emit IHAVE(mids)

shift the mcache
```
Note that we used the same parameter `D` as the target degree for
gossip for simplicity, but this is not normative. A separate parameter
`D_lazy` can be used to explicitly control the gossip propagation
factor, which allows for tuning the tradeoff between eager and lazy
transmission of messages.

### Control message piggybacking

Gossip and other control messages do not have to be transmitted on
their own message.  Instead, they can be coalesced and piggybacked on
any other message in the regular flow, for any topic. This can lead to
message rate reduction whenever there is some correlated flow between
topics, and can be significant for densely connected peers.

For piggyback implementation details, consult the [Go implementation](https://github.com/libp2p/go-floodsub/blob/master/gossipsub.go).

### Protobuf

The protocol extends the existing `RPC` message structure with a new field,
`control`. This is an instance of `ControlMessage` which may contain one or more
control messages. The four control messages are `ControlIHave` for `IHAVE` messages,
`ControlIWant` for `IWANT` messages, `ControlGraft` for `GRAFT` messages and
`ControlPrune` for `PRUNE` messages.

The protobuf is as follows:

```protobuf
syntax = "proto2";

message RPC {
    // ...
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
