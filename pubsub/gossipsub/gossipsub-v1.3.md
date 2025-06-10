# gossipsub v1.3: Topic observation

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r1, 2024-05-28  |

Authors: [@pop]

Interest Group: [@pop]

[@pop]: https://github.com/ppopth

See the [lifecycle document][lifecycle-spec] for context about maturity level and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Overview](#overview)
- [Motivation](#motivation)
- [Parameters](#parameters)
- [Observing a topic](#observing-a-topic)
- [Notifying observing peers](#notifying-observing-peers)
- [Unobserving a topic](#unobserving-a-topic)
- [Limits on observing peers](#limits-on-observing-peers)
- [Control Messages](#control-messages)
  - [OBSERVE](#observe)
  - [UNOBSERVE](#unobserve)
- [Protobuf](#protobuf)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Overview

This document specifies a minimal extension to the [gossipsub v1.2](gossipsub-v1.2.md) protocol.

The proposed extension is intended to enable the nodes to get notified when there is a new message in
a topic without actually receiving the actual message.

Four new control messages are introduced: `OBSERVE`, `OBSERVED`, `UNOBSERVE`, and `UNOBSERVED`. They
are primarily used to notify the peers that the node wants to observe/unobserve if there is a new
message in the topic.

## Motivation

There are many use cases of topic observation:

- For a node that just wants to get notified when there is a new message in the topic and doesn't
  want to consume too much bandwidth by directly subscribing to the topic.

- For a node that wants to subscribe to the topic, but has some bandwidth constraint. The node can
  observe the topic and see which peer notifies it first and later send the `IWANT` to get the
  actual message. This ensures that the bandwidth used is approximately the size of the message.

The downside of topic observation is that the observing node is not part of the mesh network, so it
only consumes the messages, but doesn't contribute to other peers by forwarding the messages.

## Parameters

This section lists new configurable parameters.

| Parameter   | Description                                                | Reasonable Default |
|-------------|------------------------------------------------------------|--------------------|
| `D_observe` | (Optional) the maximum number of observing peers per topic | `D`                |

## Observing a topic

A node can observe a topic by sending an `OBSERVE` message to a peer that already subscribes to the topic.
If the observation is successful, the peer will send back an `OBSERVED` message.

If the node already subscribes to the topic, it doesn't make sense for that node to observe the topic so
the node SHOULD NOT send an `OBSERVE` message for that topic.

## Notifying observing peers

When a node receives a message in the topic, it will fordward the message to its mesh peers as usual and
, in addition, it will also send the `IHAVE` message to the peers observing that topic.

Unlike normal `IHAVE` messages which are sent at the heartbeats, these `IHAVE`s are sent immediately when
the message arrives.

After the observing peers receive the `IHAVE`, they MAY choose to request the message by sending an `IWANT`.

After the node receives an `IWANT` from an observing (not subscribing) peer, it SHOULD send back the message.

## Unobserving a topic

A node can unobserve a topic by sending an `UNOBSERVE` message to a peer that it previously sent an `OBSERVE`.
If the unobservation is successful, the peer will send back an `UNOBSERVED` message.

## Limits on observing peers

If there are too many observing peers, those peers can send the `IWANT` messages and the node will have to
send too many messages out to those peers which consumes a lot of bandwidth of the node.

The node MUST limit the number of observing peers per topic below or equal to `D_observe`.

If a node receives an `OBSERVE`, but the limit is already reached, it MAY send an `UNOBSERVED` to the peer
with lowest score. Note that an `UNOBSERVED` can be sent, even if there is no `UNOBSERVE`.

## Control Messages

There are four new control messages introduced in this extension: `OBSERVE`, `OBSERVED`,
`UNOBSERVE`, and `UNOBSERVED`.

### OBSERVE

The `OBSERVE` message informs a peer that the node wants to receive an IHAVE message immediately when
there is a new message in the specified topic arriving at the peer.

If the node already subscribes to the topic, the peer MUST ignore the `OBSERVE` message.

### OBSERVED

The `OBSERVED` message informs a peer that the observation is successful.

### UNOBSERVE

The `UNOBSERVE` message informs a peer that the node doesn't want to receive an IHAVE message
immediately for the specified topic anymore. This is like an undo message for the `OBSERVE`.

If there is no previous `OBSERVE` message for the specified topic from the node, the peer MUST ignore
the `UNOBSERVE` message.

### UNOBSERVED

There are two use cases for `UNOBSERVED`:

- To inform a peer that the unobservation is successful.

- To inform a peer that it has been forced to unobserve.

## Protobuf

This extension extends the existing `ControlMessage` structure as follows.

```protobuf
message RPC {
    // ... see definition in the gossipsub specification
}

message ControlMessage {
    // ... see definition in the gossipsub specification
    repeated ControlObserve    observe    = 6;
    repeated ControlObserved   observed   = 7;
    repeated ControlUnobserve  unobserve  = 8;
    repeated ControlUnobserved unobserved = 9;
}

message ControlObserve {
	optional string topicID = 1;
}

message ControlObserved {
	optional string topicID = 1;
}

message ControlUnobserve {
	optional string topicID = 1;
}

message ControlUnobserved {
	optional string topicID = 1;
}
```
