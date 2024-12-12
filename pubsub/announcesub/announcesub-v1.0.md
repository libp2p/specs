# announcesub v1.0: pubsub protocol with no duplicates

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 1A              | Working Draft  | Active | r0, 2024-12-04  |

Authors: [@ppopth], [@nisdas], [@chirag-parmar]

[@ppopth]: https://github.com/ppopth
[@nisdas]: https://github.com/nisdas
[@chirag-parmar]: https://github.com/chirag-parmar

See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

---

## Overview

This is the specification for a new pubsub protocol over libp2p, heavily based on gossipsub. The protocol is designed in a way to reduce the number of duplicates to zero, trading off with more latency.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Background](#background)
  - [Problem With Gossipsub](#problem-with-gossipsub)
- [Enter Announcesub](#enter-announcesub)
- [Dependencies](#dependencies)
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
  - [IANNOUNCE](#iannounce)
  - [INEED](#ineed)
- [Message Processing](#message-processing)
- [Heartbeat](#heartbeat)
  - [Mesh Maintenance](#mesh-maintenance)
  - [Fanout Maintenance](#fanout-maintenance)
  - [Gossip Emission](#gossip-emission)
- [Protobuf](#protobuf)
- [Future Improvement](#future-improvement)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Background

Before diving into the motivations for announcesub, we can look at gossipsub as of v1.2 to understand how it works.

Gossipsub is a pubsub protocol over lib2p which is based on randomized topic meshes. The general message propagation strategy is to broadcast any message to a subset of its peers. This subset is referred to as the 'mesh'. By controlling the outbound degree of each peer you are also able to control the amplification factor in the network.

By selecting a high enough degree you can achieve a robust network with minimum latency. This allows messages to be dispersed resiliently across a network in a short amount of time.

The mesh that is selected is random and is constantly maintained via gossip control messages to ensure that the quality of peers stays consistent and doesn't deteriorate. Gossip Metadata is emitted during every heartbeat to allow peers who might have missed certain messages due to downstream message loss to be able to recover and retrieve them.

Each peer has a memory of all seen messages in the network over a period of time. This allows nodes to drop duplicates and prevents them from being further disseminated.Also having memory of messages which were propagated allows peers to make scoring decisions on their mesh peers. This allows them to prune lousy peers from the mesh and graft new ones in.

### Problem With Gossipsub

As demonstrated above gossipsub has some very desirable characteristics as a pubsub protocol. However, while you have a resilient network with minimal latency (assuming a high enough degree), Gossipsub as of its current design brings about a high level of amplification.

The tradeoff of the current design is if a network requires messages to be propagated with minimal latency it requires a large amount of amplification. This is problematic in networks which need to propagate large messages, as the amplification done is significant. If many of these large messages start being propagated in a network it would affect the general decentralization and scalability of the network.

For networks such as those Gossipsub v1.2 introduced a new control message called `IDONTWANT`. This control message allows a peer to tell its mesh peers not to propagate a message matching a particular message ID. The main goal of this is to prevent duplicates from being sent and reduce amplification in the network as a whole.

While this does help in reducing duplicates it ultimately relies on remote peers being able to act on the control message in time. If they do not, the message still ends up being forwarded wasting bandwidth on both the sender and the receiver. So how can we improve on this?

## Enter Announcesub

Announcesub can be thought of as a modification to gossipsub which reduces the number of duplicates to zero trading off with more latency.

In announcesub, instead of sending the messages right away to mesh peers, you send `IANNOUNCE` to them instead and see if they are interested in the message or not. If they are, they can send `INEED`.

After sending `INEED` to mesh peers, if there is no response after some timeout, you send `INEED` to another peer that sent you `IANNOUNCE` earliest. If you still get no response, keep going on.

By doing this, you are guaranteed that you will receive only one copy of messages. However you may need to send the message more than once to your mesh peers which is bound by the degree. Unless you are the publisher or very close to the publisher, you are expected to send only one copy anyway.

The benefits of doing this are numerous, a few are listed below:
- In congested networks which have peers with lower bandwidth, reducing the number of duplicates to 0 actually improves latency as only one copy of the message passes through each peer.
- The mesh degree can be increased greatly without affecting decentralization. The main reason the degree is bounded was to make sure that bandwidth requirements are maintainable. Since we now have zero duplicates via each link, you can have a message propagated with even less latency (fewer hops are required with a higher degree).

## Dependencies

Before peers can exchange pubsub messages, they must first become aware of each other's existence. Similar to gossipsub, peer discovery mechanism is assumed to be provided by the environment.

Whenever a new peer is connected, the announcesub implementation checks to see if the peer implements floodsub, gossipsub, and/or announcesub, and if so, it sends it a hello packet that announces the topics that it is currently subscribing to.

## Parameters

This section lists the configurable parameters that control the behavior of announcesub, along with a short description and reasonable defaults. Each parameter is introduced with full context elsewhere in this document.

| Parameter            | Purpose                                               | Reasonable Default |
|----------------------|-------------------------------------------------------|--------------------|
| `D`                  | The desired mesh degree of the network                | 6                  |
| `D_low`              | Lower bound for mesh degree                           | 4                  |
| `D_high`             | Upper bound for mesh degree                           | 12                 |
| `D_lazy`             | (Optional) the outbound degree for gossip emission    | `D`                |
| `timeout`            | Timeout for INEED messages                            | 400 milliseconds   |
| `heartbeat_interval` | Time between [heartbeats](#heartbeat)                 | 1 second           |
| `fanout_ttl`         | Time-to-live for each topic's fanout state            | 60 seconds         |
| `mcache_len`         | Number of history windows in message cache            | 5                  |
| `mcache_gossip`      | Number of history windows to use when emitting gossip | 3                  |
| `seen_ttl`           | Expiry time for cache of seen message ids             | 2 minutes          |

## Router State

The router keeps track of some necessary state to maintain stable topic meshes.

The state can be roughly divided into two categories: [peering state](#peering-state), and state related to the [message cache](#message-cache).

### Peering State

Peering state is how the router keeps track of the pubsub-capable peers it's aware of and the relationship with each of them.

There are three main pieces of peering state:

- `peers` is a set of ids of all known peers that support announcesub, gossipsub, or floodsub. Throughout this document `peers.announcesub` will denote peers supporting announcesub, while `peers.gossipsub` and `peers.floodsub` denotes gossipsub and floodsub peers.

- `mesh` is a map of subscribed topics to the set of peers in our overlay mesh for that topic.

- `fanout`, like `mesh`, is a map of topics to a set of peers, however, the `fanout` map contains topics to which we _are not_ subscribed.

In addition to the gossipsub-specific state listed above, the libp2p pubsub framework maintains some "router-agnostic" state. This includes the set of topics to which we are subscribed, as well as the set of topics to which each of our peers is subscribed. Elsewhere in this document, we refer to `peers.floodsub[topic]`, `peers.gossipsub[topic]`, and `peers.announcesub[topic]` to denote floodsub, gossipsub, or announcesub capable peers within a specific topic.

### Message Cache

The message cache (or `mcache`), is a data structure that stores message IDs and their corresponding messages, segmented into "history windows." Each window corresponds to one heartbeat interval, and the windows are shifted during the [heartbeat procedure](#heartbeat) following [gossip emission](#gossip-emission). The number of history windows to keep is determined by `mcache_len`, while the number of windows to examine when sending gossip is controlled by `mcache_gossip`.

The message cache supports the following operations:

- `mcache.put(m)`: adds a message to the current window and the cache.
- `mcache.get(id)`: retrieves a message from the cache by its ID, if it is still present.
- `mcache.get_gossip_ids(topic)`: retrieves the message IDs for messages in the most recent history windows, scoped to a given topic. The number of windows to examine is controlled by the `mcache_gossip` parameter.
- `mcache.shift()`: shifts the current window, discarding messages older than the history length of the cache (`mcache_len`).

We also keep a `seen` cache, which is a timed least-recently-used cache of message IDs that we have observed recently. The value of "recently" is determined by `seen_ttl`, with a reasonable default of two minutes. This value should be chosen to approximate the propagation delay in the overlay, within a healthy margin.

The `seen` cache serves two purposes. In all pubsub implementations, we can first check the `seen` cache before starting the forwarding process to avoid wastefully republishing the same message multiple times. The `seen` cache is also used when processing `IANNOUNCE` and `IHAVE` sent by another peer, so that we only request messages we have not already seen before.

In the go implementation, the `seen` cache is provided by the pubsub framework and is separate from the `mcache`, however other implementations may wish to combine them into one data structure.

## Topic Membership

In addition to the `SUBSCRIBE` / `UNSUBSCRIBE` events sent by the pubsub framework, gossipsub must do additional work to maintain the mesh for the topic it is joining or leaving. We will refer to the two topic membership operations below as `JOIN(topic)` and `LEAVE(topic)`.

When the application invokes `JOIN(topic)`, the router will form a topic mesh by selecting up to `D` peers from its [local peering state](#peering-state) first examining the `fanout` map. If there are peers in `fanout[topic]`, the router will move those peers from the `fanout` map to `mesh[topic]`. If the topic is not in the `fanout` map, or if `fanout[topic]` contains fewer than `D` peers, the router will attempt to fill `mesh[topic]` with peers from `peers.announcesub[topic]` which is the set of all announcesub-capable peers it is aware of that are members of the topic.

Regardless of whether they came from `fanout` or `peers.announcesub`, the router will inform the new members of `mesh[topic]` that they have been added to the mesh by sending them `GRAFT`.

The application can invoke `LEAVE(topic)` to unsubscribe from a topic. The router will inform the peers in `mesh[topic]` by sending them `PRUNE`, so that they can remove the link from their own topic mesh. After sending `PRUNE` messages, the router will forget `mesh[topic]` and delete it from its local state.

## Control Messages

Control messages are exchanged to maintain topic meshes and emit gossip. This section lists the control messages in the core gossipsub protocol.

For details on how gossipsub routers respond to control messages, see [Message Processing](#message-processing).

The [protobuf](https://developers.google.com/protocol-buffers) schema for control messages is detailed in the [Protobuf](#protobuf) section.

### GRAFT

The `GRAFT` message grafts a new link in a topic mesh. The `GRAFT` informs a peer that it has been added to the local router's mesh view for the included topic id.

### PRUNE

The `PRUNE` message prunes a mesh link from a topic mesh. `PRUNE` notifies a peer that it has been removed from the local router's mesh view for the included topic id.

### IHAVE

The `IHAVE` message is [emitted as gossip](#gossip-emission). It provides the remote peer with a list of messages that were recently seen by the local router. The remote peer may then request the full message content with `IWANT`.

### IWANT

The `IWANT` message requests the full content of one or more messages whose IDs were announced by a remote peer in an `IHAVE` message.

### IANNOUNCE

The `IANNOUNCE` message is sent to mesh peers, when the local router receives a new message. It provides the remote peer with a single message id of the message that was recently seen by the local router.

### INEED

The `INEED` message requests the full content of a single message whose id was announced by a remote peer in an `IANNOUNCE` message.

## Message Processing

Upon receiving a message, the router will first process the message payload. Payload processing will validate the message according to application-defined rules and check the [`seen` cache](#message-cache) to determine if the message has been processed previously.

If the message is valid and has not been previously seen, then it will send `IANNOUNCE` with its message id attached to all mesh peers to tell them that it just receives a new message. If they want the full content of the message, they should send `INEED` back.

After processing the message payload, the router will process the control
messages:

- Upon receiving `GRAFT`, the router will check to see if it is indeed subscribed to the topic identified in the message. If so, the router will add the sender to `mesh[topic]`. If the router is no longer subscribed to the topic, it will respond with `PRUNE` to inform the sender that it should remove its mesh link.

- Upon receiving `PRUNE`, the router will remove the sender from `mesh[topic]`.

- Upon receiving `IWANT`, the router will check its [`mcache`](#message-cache) and will forward any requested messages that are present in the `mcache` to the peer who sent the `IWANT` message.

- Upon receiving `IHAVE`, the router will check its `seen` cache. If the `IHAVE` message contains message IDs that have not been seen, the router will request them with an `IWANT` message.

- Upon receiving `INEED` after sending `IANNOUNCE`, the router must send the full content back without an option to decline. Otherwise it will be deemed misbehaving.

- Upon receiving `IANNOUNCE`, the router adds the sending peer to a priority list of who sent `IANNOUNCE` earliest for a particular message id. If it is the first `IANNOUNCE` of a particular id, the router sends `INEED` to that peer immediately.

  After the router sends `INEED`, it will time out if it doesn't receive the message back in time, as indicated by `timeout`. If the timeout happens, the router will send `INEED` to the next peer on the priority list. If it still times out, keep going with next peers until the list runs out of peers.

  Notice that timeouts can delay receiving the message. It's worth noting that timeouts are rare, since the peer just sent the router `IANNOUNCE` so it means the network condition is already good and the peer should be able to send the actual message without problems.

  In the next version of announcesub, we plan to penalize peers that don't send the message in time.

Apart from forwarding received messages, the router can of course publish messages on its own behalf, which originate at the application layer. This is very similar to receiving and forwarding received messages:

- If the router is subscribed to the topic, it will send `IANNOUNCE` to all mesh peers in `mesh[topic]` and reply with the actual message if it gets `INEED` back.
- If the router is not subscribed to the topic, it will examine the set of peers in `fanout[topic]`. If this set is empty, the router will choose up to `D` peers from `peers.announcesub[topic]` and add them to `fanout[topic]`. Assuming there are now some peers in `fanout[topic]`, the router will send the full content of the message to each.

## Heartbeat

Each peer runs a periodic stabilization process called the "heartbeat procedure" at regular intervals. The frequency of the heartbeat is controlled by the [parameter](#parameters) `heartbeat_interval`, with a reasonable default of 1 second.

The heartbeat serves three functions: [mesh maintenance](#mesh-maintenance), [fanout maintenance](#fanout-maintenance), and [gossip emission](#gossip-emission).

### Mesh Maintenance

Topic meshes are maintained with the following stabilization algorithm:

```
for each topic in mesh:
 if |mesh[topic]| < D_low:
   select D - |mesh[topic]| peers from peers.announcesub[topic] - mesh[topic]
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

- `D`: the desired mesh degree of the network
- `D_low`: an acceptable lower threshold for `D`. If there are fewer than
  `D_low` peers in a given topic mesh, we attempt to add new peers.
- `D_high`: an acceptable upper threshold for `D`. If there are more than
  `D_high` peers in a given topic mesh, we randomly select peers for removal.

### Fanout Maintenance

The `fanout` map is maintained by keeping track of the last published time for each topic. If we do not publish any messages to a topic within a configurable TTL, the fanout state for that topic is discarded.

We also try to ensure that each `fanout[topic]` set has at least `D` members.

The fanout maintenance algorithm is:

```
for each topic in fanout:
  if time since last published > fanout_ttl
    remove topic from fanout
  else if |fanout[topic]| < D
    select D - |fanout[topic]| peers from peers.announcesub[topic] - fanout[topic]
    add the peers to fanout[topic]
```

The [parameters](#parameters) of the algorithm are:

- `D`: the desired mesh degree of the network.
- `fanout_ttl`: the time for which we keep the fanout state for each topic. If
  we do not publish to a topic within `fanout_ttl`, the `fanout[topic]` set is
  discarded.

### Gossip Emission

Gossip is emitted to a random selection of peers for each topic that are not already members of the topic mesh:

```
for each topic in mesh+fanout:
  let mids be mcache.get_gossip_ids(topic)
  if mids is not empty:
    select D peers from peers.announcesub[topic]
    for each peer not in mesh[topic] or fanout[topic]
      emit IHAVE(mids)

shift the mcache
```

Note that we use the same parameter `D` as the target degree for both gossip and mesh membership, however this is not normative. A separate parameter `D_lazy` can be used to explicitly control the gossip propagation factor, which allows for tuning the tradeoff between eager and lazy transmission of messages.

## Protobuf

The announcesub protocol extends the [existing `RPC` message structure][pubsub-spec-rpc] with a new field, `control`. This is an instance of `ControlMessage` which may contain one or more control messages.

The four control messages are `ControlIHave` for [`IHAVE`](#ihave) messages, `ControlIWant` for [`IWANT`](#iwant) messages, `ControlGraft` for [`GRAFT`](#graft) messages, `ControlPrune` for [`PRUNE`](#prune) messages, `ControlIAnnounce` for [`IANNOUNCE`](#iannounce) messages, and `ControlINeed` for [`INEED`](#ineed) messages.

```protobuf
syntax = "proto2";

message RPC {
	// ... see definition in pubsub interface spec
	optional ControlMessage control = 3;
}

message ControlMessage {
	repeated ControlIHave ihave = 1;
	repeated ControlIWant iwant = 2;
	repeated ControlGraft graft = 3;
	repeated ControlPrune prune = 4;
	repeated ControlIAnnounce iannounce = 5;
	repeated ControlINeed ineed = 6;
}

message ControlIHave {
	optional string topicID = 1;
	repeated bytes messageIDs = 2;
}

message ControlIWant {
	repeated bytes messageIDs = 1;
}

message ControlGraft {
	optional string topicID = 1;
}

message ControlPrune {
	optional string topicID = 1;
}

message ControlIAnnounce {
	optional string topicID = 1;
	optional bytes messageID = 2;
}

message ControlINeed {
	optional bytes messageID = 2;
}
```

[pubsub-interface-spec]: ../README.md
[pubsub-spec-rpc]: ../README.md#the-rpc

## Future Improvement

- Add a scoring function with a bunch of rules to detect misbehaving peers just like the one in [gossipsub v1.1][gossipsub-v1.1-spec]
- Let publishers just send the full content of messages to mesh peers, rather than `IANNOUNCE`, because no one has really seen the message before. This saves one RTT, but it will kill anonymity so we are not sure yet to do it.

[gossipsub-v1.1-spec]: ../gossipsub/gossipsub-v1.1.0.md
