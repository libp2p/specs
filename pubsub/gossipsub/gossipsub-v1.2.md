# gossipsub v1.2: TODO

| Lifecycle Stage | Maturity                  | Status | Latest Revision |
|-----------------|---------------------------|--------|-----------------|
| 1A              | Working Draft             | Active | r1, 2023-07-14  |

Authors: [@Nashatyrev], [@Menduist]

Interest Group: [@vyzo], [@Nashatyrev], [@Menduist]

[@vyzo]: https://github.com/vyzo
[@Nashatyrev]: https://github.com/Nashatyrev
[@Menduist]: https://github.com/Menduist

See the [lifecycle document][lifecycle-spec] for context about maturity level and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

# Overview

This document aims to provide a minimal extension to the [gossipsub
v1.1](https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/gossipsub-v1.1.md)
protocol.

The proposed extensions are backwards-compatible and aim to enhance the
efficiency (minimize amplification/duplicates and decrease message latency) of
the gossip mesh networks for larger messages. 

In more specific terms, a new control message is introduced: `IDONTWANT`. It's primarily 
intended to notify mesh peers that the node already received a message and there is no 
need to send its duplicate.

# Specification

## Protocol Id

Nodes that support this Gossipsub extension should additionally advertise the
version number `1.2.0`. Gossipsub nodes can advertise their own protocol-id
prefix, by default this is `meshsub` giving the default protocol id:
- `/meshsub/1.2.0`

## Parameters

This section lists the configuration parameters that needs to agreed on across clients to avoid 
 peer penalizations

| Parameter                | Description                                                      | Reasonable Default |
|--------------------------|------------------------------------------------------------------|--------------|
| `max_idontwant_messages` | The maximum number of `IDONTWANT` messages per heartbeat per peer | ???  |


## IDONTWANT Message

### Basic scenario

When the peer receives the first message instance it immediately broadcasts 
(not queue for later piggybacking) `IDONTWANT` with the `messageId` to all its mesh peers. 
This could be performed prior to the message validation to further increase the effectiveness of the approach.    

On the other side a node maintains per-peer `dont_send_message_ids` set. Upon receiving `IDONTWANT` from 
a peer the `messageId` is added to the `dont_send_message_ids` set. 
When later relaying the `messageId` message to the mesh the peers found in `dont_send_message_ids` MUST be skipped. 

Old entries from `dont_send_message_ids` SHOULD be pruned during heartbeat processing. 
The prune strategy is outside of the spec scope and can be decided by implementations.

`IDONTWANT` message is supposed to be _optional_ for both receiver and sender. I.e. the sender MAY NOT utilize 
this message. The receiver in turn MAY ignore `IDONTWANT`: sending a message after the corresponding `IDONTWANT` 
should not be penalized.    

The `IDONTWANT` may have negative effect on small messages as it may increase the overall traffic and CPU load.
Thus it is better to utilize `IDONTWANT` for messages of a larger size.
The exact policy of `IDONTWANT` appliance is outside of the spec scope. Every implementation MAY choose whatever 
is more appropriate for it. Possible options are either choose a message size threshold and broadcast `IDONTWANT`
on per message basis when the size is exceeded or just use `IDONTWANT` for all messages on selected topics.

To prevent DoS the number of `IDONTWANT` control messages is limited to `max_idontwant_messages` per heartbeat  

### Cancelling `IWANT`

If a node requested a message via `IWANT` and then occasionally receives the message from other peer it MAY 
try to cancel its `IWANT` requests with the corresponding `IDONTWANT` message. It may work in cases when a
peer delays/queues `IWANT` requests and the `IWANT` request SHOULD be removed from the queue if not processed yet

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
    repeated ControlIDontWant idontwant = 5;
}

message ControlIDontWant {
    repeated bytes messageIDs = 1;
}

```

