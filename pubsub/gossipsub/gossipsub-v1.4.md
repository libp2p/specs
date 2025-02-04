# gossipsub v1.4: Message preamble to limit duplicate transmissions of large messages

| Lifecycle Stage | Maturity                  | Status | Latest Revision |
|-----------------|---------------------------|--------|-----------------|
| 1A              | Working Draft             | Active | r0, 2024-12-17  |

Authors: [@ufarooqstatus], [@kaiserd]

Interest Group: TBD

[@kaiserd]: https://github.com/kaiserd
[@ufarooqstatus]: https://github.com/ufarooqstatus

See the [lifecycle document][lifecycle-spec] for context about maturity level and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

# Overview

This document outlines small extensions to the [gossipsub 
v1.2](https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/gossipsub-v1.2.md) 
protocol to improve performance when handling large message transmissions. 
The extensions are optional, fully compatible with v1.2 of the protocol, 
and involve minor modifications to peer behavior when receiving or forwarding large messages.  

The proposed modifications address the issue that the number of IWANT requests and duplicates increases significantly with the message size. 
This happens because sending a large message can take considerable time, 
and during this time, the receiver is unaware of the IDs of the messages it is receiving.

Under the current arrangement, if IHAVE announcements are received for a message that is already being received, 
the receiver may generate multiple IWANT requests, triggering unnecessary retransmissions of the same message. 
Higher message reception time also increases the probability of simultaneously receiving the same message from many peers. 

Prepending a preamble while sending a large message can allow receivers 
to immediately gain insights into the IDs and lengths of the messages they are receiving.  
This can allow receivers to defer IWANT requests for messages they are currently receiving, 
thereby reducing the number of unnecessary IWANT requests.

At the same time, receivers may inform their mesh members about ongoing message reception.
For this purpose, a new control message (IMReceiving) is introduced, 
indicating that the peer sending IMReceiving message is currently receiving messages identified by their message IDs, 
and sending duplicates might be unnecessary.

On receiving an IMReceiving message, a peer should defer sending of messages identified by the message IDs in IMReceiving message.
This can lead to a significant reduction in bandwidth utilization and message latency.  

# Specification

## Protocol Id

Nodes that support this Gossipsub extension should additionally advertise the
version number `1.4.0`. Gossipsub nodes can advertise their own protocol-id
prefix, by default this is `meshsub` giving the default protocol id:
- `/meshsub/1.4.0`

## Parameters

This section lists the configuration parameters that clients need to agree on to avoid peer penalizations.

| Parameter                | Description                                                      | Reasonable Default |
|--------------------------|------------------------------------------------------------------|--------------|
| `peer_preamble_announcements` | The maximum number of preamble announcements for unfinished transfers per peer | 1???  |
| `mesh_preamble_announcements` | The maximum number of preamble announcements to accept for unfinished transfers per topic per heartbeat interval | 3???  |
| `max_iwant_requests` | The maximum number of simultaneous IWANT requests for a message | 1???  |
| `preamble_threshold` | The smallest message size to use message preamble | 200KB???  |



## Message Preamble

### Basic scenario

When a peer starts relaying a message that exceeds the preamble_threshold size, 
it may include a control message (called message preamble) at the start of the message.

The purpose of the preamble is to allow receivers to instantly learn about the incoming message. 
The preamble must include the message ID and length, 
providing receivers with immediate access to critical information about the incoming message. 
The receiver must immediately process a message preamble without waiting to download the entire message.

On receiving a preamble that advertises a message ID not present in the seen cache, 
a receiver should add that message ID to the ongoing_receives list.
The ongoing_receives list is crucial in limiting IWANT requests and simultaneous reception of the same message from mesh peers.
 
The receiver may use message length to leniently estimate message download time.
If the message is successfully downloaded before the estimated download time has elapsed, 
the message ID is removed from the ongoing_receives list and added to the seen cache. 

If the download takes longer than the estimated download time, 
the sender may be penalized through P4 to discourage peers from intentionally delaying message transmission.

The message preamble is considered _optional_ for both the sender and the receiver. 
This means that the sender may choose not to prepend the preamble, 
and the receiver may also opt to ignore it.
Adding a message preamble may increase control overhead for small messages. 
Therefore, it is preferable to use it only for messages that exceed the preamble_threshold.


### Limiting IWANT Requests

When a peer receives an IHAVE announcement for a message ID not present in the seen cache, 
the peer must also check the  ongoing_receives list before making an IWANT request. 

If the message ID is found in the ongoing_receives list, 
the peer should postpone sending the IWANT request for a defer_interval. 
The defer_interval may be based on the message download time.

If the message download completes before the defer_interval expires, 
the IWANT request for that message will not be generated. 
However, if the defer_interval elapses and the download has not completed, 
the peer can proceed to make the IWANT request for the missing message. 

The total number of outstanding IWANT requests for a single message should not exceed max_iwant_requests.
Every peer must respond to the received IWANT requests. 
Failing to do so may result in behavioural penalty through P7. 
This will discourage peers from intentionally not replying to IWANT requests.

### IMReceiving Message

The IMReceiving message serves a distinct purpose compared to the IDONTWANT message. 
An IDONTWANT can only be transmitted after receiving the entire message. 
In contrast, an IMReceiving should be transmitted immediately after receiving a preamble indicating a large message transfer. 
The IMReceiving message requests peers to refrain from resending a large message that is already being received.

When a peer receives a message preamble indicating a message ID that is not present in the seen cache, 
it should send an IMReceiving message to the nodes in its full message mesh. 
On receiving an IMReceiving from a peer, 
a node should postpone sending the messages indicated by the IMReceiving to that peer. 
The defer_interval can be leniently estimated based on the message length. 

An IDONTWANT from the peer will indicate successful reception of the message. 
If an IDONTWANT for the deferred message is not received and the defer_interval has elapsed, 
the node may proceed to transmit the message.


## Protobuf Extension

The protobuf messages are identical to those specified in the [gossipsub v1.2
specification](https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/gossipsub-v1.2.md)
with the following  control message modifications:

```protobuf
message RPC {
 // ... see definition in the gossipsub specification
}

message ControlMessage {
    // ... see definition in the gossipsub specification
    repeated ControlPreamble preamble = 6;
    repeated ControlIMReceiving imreceiving = 7;
}

message ControlPreamble {
    optional bytes messageID = 1;
    optional int32 messageLength = 2;
}

message ControlIMReceiving {
    optional bytes messageID = 1;
    optional int32 messageLength = 2;
}

```

