# Gossipsub v1.2

# Overview

This document aims to provide a minimal extension to the [gossipsub
v1.1](https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/gossipsub-v1.1.md)
protocol.

The proposed extensions are backwards-compatible and aim to add utility control messages for 
better network efficiency (delivery latency and total throughput) tuning gossip protocol 
implementations 

In more specific terms, new control messages are introduced: `PING` and `PONG`. 
They are primarily intended for collecting statistics to estimate peer connection 
latency and bandwidth and adjusting message broadcasting strategy accordingly.

# Specification

## Protocol Id

Nodes that support this Gossipsub extension should additionally advertise the
version number `1.2.0`. Gossipsub nodes can advertise their own protocol-id
prefix, by default this is `meshsub` giving the default protocol id:
- `/meshsub/1.2.0`

## Parameters

This section lists the configuration parameters that needs to agreed on across clients to avoid
peer penalizations

| Parameter         | Description                                                            | Reasonable Default |
|-------------------|------------------------------------------------------------------------|--------------------|
| `max_ping_rate`   | maximum number of `PING` messages per minute      | 60                 |

## PING/PONG Messages

### Sender

Sender MAY send `PING` message (either standalone or piggy tailing) at any time. Sender is free to choose 
any `id` however it might be reasonable to select unique numbers across the session. 

Sender MUST NOT send `PING` message to a peer if `max_ping_rate` `PING` message were already sent 
to that peer during the last minute.

An implementation is free to choose a reasonable timeout (e.g. 60 seconds) for waiting for a corresponding 
`PONG` message. However it is worth considering that a `PONG` message might be 
delayed by another message which is already in the send buffer (on wire) , thus the timeout should not be too small.
`PONG` timeout exceeding SHOULD be treated as protocol malfunction and the peer connection 
SHOULD be closed  

### Responder

Upon receiving a `PING` message the responder
- MUST respond with a `PONG` message with the same `id` value
- SHOULD check if the `max_ping_rate` is respected by sending peer (otherwise the peer MAY be penalized)
- SHOULD make his best to respond back with a corresponding `PONG` as soon as possible. That means:
  - SHOULD NOT queue the message for later send (e.g. on heartbeat or piggy tailing for a next publish message)
  - if there are messages queued for sending to the peer that queue SHOULD be disregarded and the 
    the `PONG` message should be flushed immediately

### Usage scenarios

#### Latency estimation

This is the most obvious and basic scenario of Ping/Pong usage. Gossip implementation may use estimated 
connection latency to optimize message dissemination behavior (e.g. adjust the staggered sending strategy).
This could be implemented without relying on external protocols. 

Worth mentioning that the latencies measured with Gossip Ping/Pong may have significant outliers as all
the gossip messages are transmitted sequentially and both `PING` and `PONG` messages could be delayed 
due to a message which was buffered for sending a moment earlier. 
Thus it makes sense to consider the lower percentile of measured latencies within some time window.  

#### Message delivery ACKnowledgement

When sending a message (especially of a larger size) the sender may attach a `PING` control message such 
that a receiver would respond with `PONG` as soon as the message transfer is complete. That way the sender 
may roughly estimate connection bandwidth to optimize its message dissemination behavior.

## Protobuf Extension

The protobuf messages are identical to those specified in the [gossipsub v1.0.0
specification](https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/gossipsub-v1.0.md)
with the following  control message modifications:

```protobuf
message RPC {
 // ... see definition in the gossipsub specification
}

message ControlMessage {
    // messages from v1.0
    optional ControlPingPong ping = 5;
    optional ControlPingPong pong = 6;
}

message ControlPingPong {
    required uint64 id = 1;
}

```

