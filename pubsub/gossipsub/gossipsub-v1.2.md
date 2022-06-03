# Episub - Gossipsub Extension


# Overview

This document aims to provide a minimal extension to the [gossipsub v1.1](https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/gossipsub-v1.1.md) protocol, that supersedes the previous [episub](https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/episub.md) proposal.

The proposed extensions are backwards-compatible and aim to enhance the efficiency (minimize amplification/duplicates and decrease message latency) of the gossip mesh networks by dynamically adjusting the messages sent by mesh peers based on a local view of message duplication and latency. 

In more specific terms, two new control messages are introduced, `CHOKE` and `UNCHOKE`. When a Gossipsub router is receiving many duplicates on a particular mesh, it can send a `CHOKE` message to it's mesh peers that are sending duplicates slower than its fellow mesh peers. Upon receiving a `CHOKE` message, a peer is informed to no longer propagate mesh messages to the sender of the `CHOKE` message, rather lazily (in every heartbeat) send it's gossip. 

A Gossipsub router may notice that it is receiving messages via gossip from it's `CHOKE`'d peers faster than it receives them via the mesh. In this case it may send an `UNCHOKE` message to the peer to inform the peer to resume propagating messages in the mesh. 
The router may also notice that it is receiving messages from gossip from peers not in the mesh (fanout) faster than it receives messages in the mesh. It may then add these peers into the mesh. 

The modifications outlined above intend to optimize the Gossipsub mesh to receive minimal duplicates from peers with the lowest latency.

# Specification

## Protocol Id

Nodes that support this Gossipsub extension should additionally advertise the version number `1.2.0`. Gossipsub nodes can advertise their own protocol-id prefix, by default this is `meshsub` giving the default protocol id:
- `/meshsub/1.2.0`

## Parameters

This section lists the configuration parameters that control the behaviour of the mesh optimisation.


| Parameter | Description  | Reasonable Default |
| -------- | -------- | -------- |
| `D_non_choke`     | The minimum number of peers in a mesh that must remain unchoked. | `D_lo` |
| `choke_heartbeat_interval` | The number of heartbeats before assessing and applying `CHOKE`/`UNCHOKE` control messages and adding `D_max_add`. | 20 |
| `D_max_add` | The maximum number of peers to add into the mesh (from fanout) if they are performing well per `choke_heartbeat_interval`. | 1 |
| `choke_duplicates_threshold` | The minimum number of duplicates as a percentage of received messages a peer must send before being eligible of being `CHOKE`'d. | 60 |
| `choke_churn` | The maximum number of peers that can be `CHOKE`'d or `UNCHOKE`'d in any `choke_heartbeat_interval`. | 2 |
|` unchoke_threshold` | Determines how aggressively we unchoke peers. The percentage of messages that we receive in the `choke_heartbeat_interval` that were received by gossip from a choked peer. | 50 |
| `fanout_addition_threshold` | How aggressively we add peers from the fanout into the mesh. The percentage of messages that we receive in the `choke_heartbeat_interval` that were received from a fanout peer. | 10 |

## Choking

Every `choke_heartbeat_interval` the router counts the number of valid (or not invalid) duplicate messages (note that the first message of its kind received is not a duplicate) and the time it took to receive each duplicate for each peer in each mesh that are not `CHOKE`'d. The router then filters which peers have sent duplicates over the `choke_duplicates_threshold` and sends `CHOKE` messages to at most `choke_churn` peers ordered by largest average latency. A router should ensure that at least `D_non_choke` peers remain in the mesh (and should not send `CHOKE` messages if this limit is to be violated) and should perform this check every heartbeat with the mesh maintenance. 

## UnChoking

Every `choke_heartbeat_interval` the router counts the number of received valid messages obtained via `IWANT` (and hence gossip) from a `CHOKE`'d peer. If the percentage of received valid messages is greater then `unchoke_threshold` we send an `UNCHOKE` to randomly selected peers up to the `choke_churn` limit.

## Fanout Addition

Every `choke_heartbeat_interval` the router counts the number of received valid messages obtained via `IWANT` (and hence gossip) from `fanout` peers. If the percentage of received messages is greater than `fanout_addition_threshold` a random selection of these peers up to `D_max_add` are added to the mesh (provided the mesh bounds remain valid, i.e `D_high`).

## Handling Gossipsub Scoring For Choked Peers

TODO

## Protobuf Extension

The protobuf messages are identical to those specified in the [gossipsub v1.0.0 specification](https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/gossipsub-v1.0.md) with the following  control message modifications:

```protobuf
message RPC {
 // ... see definition in the gossipsub specification
}

message ControlMessage {
    repeated ControlIHave ihave = 1;
    repeated ControlIWant iwant = 2;
    repeated ControlGraft graft = 3;
    repeated ControlPrune prune = 4;
    repeated ControlChoke choke = 5;
    repeated ControlUnChoke unchoke = 6;
}

message ControlChoke {
    optional string topicID = 1;
}

message ControlUnChoke {
    optional string topicID = 1;
}
```
