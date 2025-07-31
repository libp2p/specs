# Generalized Gossipsub

This is a generalization of the original [gossipsub protocol](../gossipsub/README.md)
that makes the protocol extensible through additional modules called strategies.
These strategies can be employed per-topic and allow the protocol to be
fine-tuned under a range of scenarios and circumstances and applied either
dynamically or statically on a per-application (topic) basis.

NOTE: Any current gossipsub implementation can be fully compatible with this
protocol by simply implementing the CHOKE/UNCHOKE control messages. This protocol is
fully backwards compatible with original gossipsub implementations.

## Table of Contents

- [Generalized Gossipsub](#generalized-gossipsub)
  - [Motivation](#motivation)
  - [Overview](#overview)
  - [Strategies](#strategies)
  - [The RPC](#the-rpc)
  - [Deviations from Gossipsub](#deviations-from-gossipsub)
    - [Protocol State](#protocol-state)
    - [Topic Membership](#topic-membership)
    - [Control Messages](#control-messages)
    - [Message Propagation](#message-propagation)

## Motivation

[Gossipsub](../pubsub/gossipsub/README.md) is designed to be a configurable protocol that allows users to adjust
configuration parameters to make trade-offs between resiliency, latency and
bandwidth. Over the years, these parameters have been found too constraining
resulting in a number of proposals to modify the specification to achieve better
results under specific circumstances.

There are three major areas that are constrained by the gossipsub specification, that are a
prime targets to free from the specification and allow users to implement freely, these
are:

- **Scoring** - A system used to score peers for security and performance.
- **Mesh construction/peer sampling** (and therefore network topologies).
- **Message dissemination** - The choice of how to send messages either direct or
  via gossip and the timing.

A further constraint is that gossipsub requires that any given choice of these
areas is enforced across all topics, which constrains the solution space for
users to one design choice for potentially different applications.

There are mesh construction strategies that can select mesh's in such a way that
can form efficient broadcast trees. We could think of a topology that forms a
single tree spanning all nodes on the network. This would be very efficient, but
not very resilient. Another example could be small mesh sizes, which sacrifices
resiliency for bandwidth, which may be applicable to applications implementing
schemes like erasure coding which have redundancy built in.
There are different broadcast strategies that could favour gossip over direct
sending. This could be a trade-off between latency and bandwidth. In some
cases these strategies would be better suited for nodes under bandwidth
constraints.

The generalization proposed here aims to specify these strategies and allow the core protocol
to select each strategy per topic. This allows for scenarios where an
application may have a topic where resiliency is not very important, so a
low-bandwidth strategy could be chosen, (i.e low-mesh, sparse topology) and at
the same time have a topic where resiliency is important so chooses a
high-bandwidth strategy (i.e high-mesh, dense topology).

A node that is heavily resource constrained, might also wish to switch to a
combination of strategies that is known to perform better under those
conditions.

The goal of this protocol is into increase the degrees of freedom in fine-tuning
p2p message dissemination in a general way that doesn't require specification
changes to apply. It also aims to minimize engineering overhead for
implementations that already have gossipsub.

## Overview

The protocol defined here is an extension/modification of the [original
gossipsub](../pubsub/gossipsub/README.md) protocol. It is aimed to increase the
configurability of the protocol to allow for a wider set of applications and
performance tunings.

As this is based on the original gossipsub specification, this document does not compile all past versions of the specification here,
rather lists the main departures from the original specification and consolidates all the protobuf and control messages.

## Strategies

There are three strategies that can be selected at any given time on a per-topic
bases:

- **Scoring** - How to score peers based on their behaviour/performance. This can
  also be global (not necessarily per-topic)
- **Mesh** - Construction/Maintenance - This strategy, if combined across all nodes,
  fundamentally controls the topology of the network.
- **Broadcast** - This strategy can dictate tradeoffs between resilience, bandwidth
  and latency by deciding how aggressively to directly send messages vs
  gossiping them.

Each of these are detailed in the [Strategies](./strategies.md) section.

Examples strategies are also provided:

- [Original Gossipsub Broadcast](./strategies/broadcast/original-gossipsub.md)
- [Original Gossipsub Mesh](./strategies/mesh/original-gossipsub.md)
- [Random Choke Mesh](./strategies/mesh/random-choke.md)

## The RPC

All communication between peers happens in the form of exchanging protobuf RPC
messages between participating peers.

The `RPC` protobuf is as follows:

```protobuf
syntax = "proto2";
message RPC {
 repeated SubOpts subscriptions = 1;
 repeated Message publish = 2;

 message SubOpts {
  optional bool subscribe = 1; // subscribe or unsubscribe
  optional string topic_id = 2;
 }

 optional ControlMessage control = 3;
}

message Message {
 optional bytes from = 1;
 optional bytes data = 2;
 optional bytes seqno = 3;
 required string topic = 4;
 optional bytes signature = 5;
 optional bytes key = 6;
}

message ControlMessage {
 repeated ControlIHave ihave = 1;
 repeated ControlIWant iwant = 2;
 repeated ControlGraft graft = 3;
 repeated ControlPrune prune = 4;
 repeated ControlChoke choke = 5;
 repeated ControlUnChoke unchoke = 6;
}

message ControlIHave {
 optional string topic_id = 1;
 repeated bytes message_ids = 2;
}

message ControlIWant {
 repeated bytes message_ids= 1;
}

message ControlGraft {
 optional string topic_id = 1;
}

message ControlPrune {
 optional string topic_id = 1;
 repeated PeerInfo peers = 2; // gossipsub v1.1 PX
 optional uint64 backoff = 3; // gossipsub v1.1 backoff time (in seconds)
}

message ControlChoke {
    required string topicID = 1;
}
message ControlUnChoke {
    required string topicID = 1;
}

message PeerInfo {
 optional bytes peer_id = 1;
 optional bytes signed_peer_record = 2;
}
```

## Deviations from Gossipsub Logic

Logic has been split from what we call "core" protocol into strategies. Here the
distinction between the split is made.

### Parameters

The parameters that remain in the protocol are:

| Parameter            | Purpose                                               | Reasonable Default |
| -------------------- | ----------------------------------------------------- | ------------------ |
| `heartbeat_interval` | Time between [heartbeats](#heartbeat)                 | 1 second           |
| `fanout_ttl`         | Time-to-live for each topic's fanout state            | 60 seconds         |
| `mcache_len`         | Number of history windows in message cache            | 5                  |
| `mcache_gossip`      | Number of history windows to use when emitting gossip | 3                  |
| `seen_ttl`           | Expiry time for cache of seen message ids             | 2 minutes          |

### Protocol State

The core protocol still handles the control messages such as
SUBSCRIBE/UNSUBSCRIBE/GRAFT/PRUNE/CHOKE/UNCHOKE and therefore must still
maintain a state of peers that form a mesh (how this is formed is up to any
given strategy), and keep track of which peers are subscribed to which topic.

### Topic Membership

The [original gossipsub](../pubsub/gossipsub/README.md) specification describes
how a router behaves when peers join or leave topics. The terminology used is
`JOIN(topic)` and `LEAVE(topic)`. The new logic of this behaves is described
here.

When the application invokes `JOIN(topic)`, the router will form a topic mesh by
asking the selected [mesh strategy][./mesh-strategy.md] for the given topic.

For all new peers that have formed the mesh, the router will inform them that they have been added to the
mesh by sending them a `GRAFT` control message.

The application can invoke `LEAVE(topic)` to unsubscribe from a topic. The
router will inform the peers in `mesh[topic]` by sending them a `PRUNE` control
message, so that they can remove the link from their own topic mesh.

After sending `PRUNE` messages, the router will forget `mesh[topic]` and delete
it from its local state.

### Control Messages

Control messages are exchanged to maintain topic meshes and emit gossip. This
section lists the control messages in the core gossipsub protocol

#### SUBSCRIBE

When a subscribe message is received, the router records that the new peer is
now subscribed to the topic and informs the mesh strategy. The mesh strategy may
choose to GRAFT this peer on this topic.

#### GRAFT

The `GRAFT` message grafts a new link in a topic mesh. The `GRAFT` informs a peer
that it has been added to the local router's mesh view for the included topic id.

#### PRUNE

The `PRUNE` message prunes a mesh link from a topic mesh. `PRUNE` notifies a
peer that it has been removed from the local router's mesh view for the
included topic id.

#### IHAVE

The `IHAVE` message provides the
remote peer with a list of messages that were recently seen by the local router.

The remote peer may then request the full message content with an `IWANT` message.

The speed and degree at which these messages are sent are entirely left to the
broadcast strategy.

#### IWANT

The `IWANT` message requests the full content of one or more messages whose IDs
were announced by a remote peer in an `IHAVE` message.

#### The CHOKE Message

Upon receiving a `CHOKE` message, the router MUST no longer forward messages to
the peer that sent the `CHOKE` message, while it is still in the mesh. Instead
it MUST always send an IHAVE message (provided there are messages to send and
it does not hit the IHAVE message limit) immediately to the peer.

A peer MUST NOT send a `CHOKE` message to another peer that is not currently
grafted into it's mesh.

A peer MUST NOT send a `CHOKE` message to another peer that is already choked
on a given mesh topic.

##### Pruning

If a mesh peer sends a `PRUNE`, the local router should consider itself also
unchoked by this peer. If that peer was choked by the local router, as it is no
longer in the mesh, it should also be considered unchoked.

Therefore, when pruning a choked peer from the mesh, an `UNCHOKE` message is
not required to be sent.

##### Publishing

Messages that are published to mesh peers MUST only be published to non-choked
peers. If flood-publishing, messages can be sent to non-mesh peers, which are
unchoked by definition.

#### The UNCHOKE Message

Upon receiving an `UNCHOKE` message, the router MUST resume forwarding messages to
the peer that sent the `UNCHOKE` message and halt sending IHAVE messages.

A peer MUST NOT send an `UNCHOKE` message to any peer that is not currently
grafted into it's mesh.

A peer MUST NOT send an `UNCHOKE` message to a peer that is already unchoked on
a given mesh topic.

### Message Processing

#### Message

When a message is received that is valid and was not published by the router itself, the router informs the broadcast module via the
Forward(Topic) interface.

The broadcast module will return which peers to forward the message to and which
to gossip to (if any).

#### GRAFT Message

On receiving a `GRAFT(topic)` message, the router will check to see
if it is indeed subscribed to the topic identified in the message. If so, the
router will inform the Mesh strategy for the topic to determine if this peer
should stay in the mesh, or if the peer should be pruned and a PRUNE(topic)
should be sent to inform the peer to remove its mesh link.

#### PRUNE Message

On receiving a `PRUNE(topic)` message, the router will remove the sender from `mesh[topic]`.

#### IHAVE Message

On receiving an `IHAVE(ids)` message, the router will check its
`seen` cache. If the `IHAVE` message contains message IDs that have not been
the router will ask the [broadcast strategy](./strategies.md) whether it should request it via an
IWANT message.

#### IWANT Message

On receiving an `IWANT(ids)` message, the router will check its
`mcache` and will forward any requested messages that are
present in the `mcache` to the peer who sent the `IWANT` message. It does this
immediately.

## Heartbeat

Each peer runs a periodic stabilization process called the "heartbeat procedure"
at regular intervals. The frequency of the heartbeat is controlled by the
[parameter](#parameters) `heartbeat_interval`, with a reasonable default of 1
second.

The heartbeat serves three functions:

- Mesh and fanout maintenance - As defined by the mesh strategy
- Gossip Emission - As defined by the broadcast strategy.

Every heartbeat, the equivalent heartbeat is called for each strategy.
