# Episub - Gossipsub Extension


# Overview

This document aims to provide a minimal extension to the [gossipsub
v1.1](https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/gossipsub-v1.1.md)
protocol, that supersedes the previous
[episub](https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/episub.md)
proposal.

The proposed extensions are backwards-compatible and aim to enhance the
efficiency (minimize amplification/duplicates and decrease message latency) of
the gossip mesh networks by dynamically adjusting the messages sent by mesh
peers based on a local view of message duplication and latency. 

In more specific terms, two new control messages are introduced, `CHOKE` and
`UNCHOKE`. When a Gossipsub router is receiving many duplicates on a particular
mesh, it can send a `CHOKE` message to it's mesh peers that are sending
duplicates slower than its fellow mesh peers. Upon receiving a `CHOKE` message,
a peer is informed to no longer propagate mesh messages to the sender of the
`CHOKE` message, rather lazily (in every heartbeat) send it's gossip. 

A Gossipsub router may notice that it is receiving messages via gossip from
it's `CHOKE`'d peers faster than it receives them via the mesh. In this case it
may send an `UNCHOKE` message to the peer to inform the peer to resume
propagating messages in the mesh. The router may also notice that it is
receiving messages from gossip from peers not in the mesh faster than it
receives messages from it's mesh peers. It may then add these peers into the
mesh. 

The modifications outlined above intend to optimize the Gossipsub mesh to
receive minimal duplicates from peers with the lowest latency.

# Specification

## Protocol Id

Nodes that support this Gossipsub extension should additionally advertise the
version number `1.2.0`. Gossipsub nodes can advertise their own protocol-id
prefix, by default this is `meshsub` giving the default protocol id:
- `/meshsub/1.2.0`

## Parameters

This section lists the configuration parameters that control the behaviour of the mesh optimisation.


| Parameter | Description  | Reasonable Default |
| -------- | -------- | -------- |
| `D_non_choke`     | The minimum number of peers in a mesh that must remain unchoked. | `D_lo` |
| `choke_heartbeat_interval` | The number of heartbeats before assessing and applying `CHOKE`/`UNCHOKE` control messages and adding peers to the mesh. | 20 |
| `choke_churn` | The maximum number of peers that can be `CHOKE`'d or `UNCHOKE`'d in any `choke_heartbeat_interval`. | 2 |
|` unchoke_churn` | Determines how aggressively we unchoke peers. The number of peers per `choke_heartbeat_interval` that can be unchoked on an individual mesh. | 2 |
| `mesh_addition_churn` | How aggressively we add peers from into the mesh. The number of peers per `choke_heartbeat_interval` that can be added to an individual mesh. | 1 |

## Implementation Notes

The actual strategy for choking/unchoking peers is left to each implementation
and potentially application user. Although the strategies for choking/unchoking
can be generic, a few useful strategies are listed in the appendix for implementers.

## The CHOKE Message

Every `choke_heartbeat_interval` the router applies its choking strategy to a
set of collected metrics of recent messages, in order to decide if any of its
mesh peers should be choked. The router should send no more
than `choke_churn` `CHOKE` messages to peers per mesh topic. The router should
also ensure that `D_non_choke` peers remain unchoked in each mesh topic.

Upon receiving a `CHOKE` message, the router MUST no longer forward messages to
the peer that sent the `CHOKE` message, while it is still in the mesh. Instead
it MUST always send an IHAVE message (provided there are messages to send and
it does not hit the IHAVE message limit) in the next gossipsub heartbeat to the
peer.

A peer MUST NOT send a `CHOKE` message to another peer that is not currently
grafted into it's mesh.

A peer MUST NOT send a `CHOKE` message to another peer that is already choked
on a given mesh topic.

#### Pruning

If a mesh peer sends a `PRUNE`, the local router should consider itself also
unchoked by this peer. If that peer was choked by the local router, as it is no
longer in the mesh, it should also be considered unchoked. 

Therefore, when pruning a choked peer from the mesh, an `UNCHOKE` message is
not required to be sent.

#### Publishing

Messages that are published to mesh peers MUST only be published to non-choked
peers. If flood-publishing, messages can be sent to non-mesh peers, which are
unchoked by definition.

## The UNCHOKE Message 

Every `choke_heartbeat_interval` the router applies its unchoking strategy to a
set of collected metrics of recent messages, in order to decide whether to
unchoke any of it's choked peers. The router should send no more
than `unchoke_churn` `UNCHOKE` messages to peers per mesh topic. 

Upon receiving an `UNCHOKE` message, the router MUST resume forwarding messages to
the peer that sent the `UNCHOKE` message and resume the normal lazy stochastic
gossiping operation in each heartbeat.

A peer MUST NOT send an `UNCHOKE` message to any peer that is not currently
grafted into it's mesh.

A peer MUST NOT send an `UNCHOKE` message to a peer that is already unchoked on
a given mesh topic.

## Mesh Addition

Every `choke_heartbeat_interval` the local router may use a strategy to decide
if it wishes to add peers into its meshes. Peers may be added to fill up to
`mesh_n_high` but should be limited to at most `mesh_addition_churn` per
`choke_heartbeat_interval`. 


## Scoring for Episub

Peers have an incentive to be choked by their mesh neighbours. Being choked
means less bandwidth the node is required to send to support the mesh network.
Malicious nodes may then intentionally attempt to game various choking
strategies in order to get choked by the router.

Choked peers are inherently less valuable mesh peers than unchoked peers. As
such, a slight scoring penalty should be added to each choked-peer which grows
the longer they are choked. This will disfavour them when a mesh gets pruned.
As Episub introduces mesh additions, peer pruning should be more common.

The exact scoring penalty is currently left as a TODO.

## Protobuf Extension

The protobuf messages are identical to those specified in the [gossipsub v1.0.0
specification](https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/gossipsub-v1.0.md)
with the following  control message modifications:

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

# Appendix

### Optional Choking Strategies

#### Latency Cutoff

A mesh peer can get choked if it sends duplicates that arrive beyond a cut-off
latency. A threshold may be added such that if more than this duplicate
threshold (as a percentage) is sent over the latency threshold the peer is
eligible to be choked.

#### Percentile Latency

Duplicate messages can be collected over a topic and ordered by the latency
received. Peers can be choked if they send over a threshold amount of
duplicates that lie in a specific percentile.

#### Order of Arrival

Messages can be grouped based on the order that they arrive. If a peers average
order of messages is greater than a specified number, that peer is eligible to
be choked.

### Optional UnChoking Strategies

#### IHAVE Message Percentage

If a choked peer has a sent an IHAVE message prior to mesh message for more
than a specified percent of the total mesh messages received, that peer is
eligible to be unchoked.

### Optional Mesh Addition Strategies

Similar to the unchoking strategy mentioned above, a router may wish to add
peers that are frequently and consistently sending IHAVE messages prior to
receiving the referenced message on the mesh.
