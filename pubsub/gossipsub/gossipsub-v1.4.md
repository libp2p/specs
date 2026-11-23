# gossipsub v1.4: PREAMBLE and IMRECEIVING to limit duplicate transmissions of large messages

| Lifecycle Stage | Maturity                  | Status | Latest Revision |
|-----------------|---------------------------|--------|-----------------|
| 1A              | Working Draft             | Active | r1, 2025-05-01  |

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

Sending a short control message, called PREAMBLE, before every large message transmission 
can allow receivers to immediately gain insights into the IDs and lengths of the messages they are receiving. 
This allows receivers to defer IWANT requests for messages they are already receiving,  
thereby reducing the number of unnecessary IWANT requests.

At the same time, receivers may inform their mesh members about ongoing message reception.
For this purpose, a new control message (IMRECEIVING) is introduced, 
indicating that the peer sending IMRECEIVING is currently receiving a message identified by the announced message ID, 
and sending duplicates might be unnecessary.

On receiving an IMRECEIVING message, a peer should refrain from sending the message identified by the announced message ID.
This can lead to a significant reduction in bandwidth utilization and message latency.
The [Safety Strategy](#safety-strategy) below safeguards against malicious behavior.  

# Specification

## Protocol Id

Nodes that support this Gossipsub extension should additionally advertise the
version number `1.4.0`. Gossipsub nodes can advertise their own protocol-id
prefix, by default this is `meshsub` giving the default protocol id:
- `/meshsub/1.4.0`

## Parameters

This section lists the configuration parameters that clients need to agree on to avoid peer penalizations.

| Parameter                | Description                                                      |
|--------------------------|------------------------------------------------------------------|
| `peer_preamble_announcements` | The maximum number of PREAMBLE announcements for unfinished transfers per peer |
| `max_iwant_requests` | The maximum number of simultaneous IWANT requests for a message |
| `preamble_threshold` | The minimum message size (in bytes) required to enable the use of a message PREAMBLE |
| `fallback_mode` | Message fetching strategy (pull or push) to use when a peer fails to deliver the message after sending a PREAMBLE. |



## Message PREAMBLE

### Basic scenario

When a peer starts relaying a message that exceeds the preamble_threshold size, 
it should transmit a preceding control message called PREAMBLE.

PREAMBLE serves as a commitment from the sender, 
indicating that the promised data message will follow without delay. 
A PREAMBLE must include the message ID and length, 
providing receivers with immediate access to critical information about the incoming message. 
The receiver must immediately process a PREAMBLE without waiting to download the entire message.

On receiving a PREAMBLE that advertises a message ID not present in the seen cache, 
a receiver should add that message ID to the ongoing_receives list.
The ongoing_receives list is crucial in limiting IWANT requests and simultaneous receptions of the same message from mesh peers.

The receiver may use message length to conservatively estimate message download duration.
If the message is successfully downloaded before the estimated download duration has elapsed, 
the message ID is removed from the ongoing_receives list and added to the seen cache. 

If the download takes longer than the estimated download time, 
the sender may be penalized through a behavioral penalty to discourage peers from intentionally delaying message transmission. 
See also [Safety Strategy](#safety-strategy) below.

PREAMBLE is considered _optional_ for both the sender and the receiver. 
This means that the sender can choose not to send the PREAMBLE, 
and the receiver can also opt to ignore it.
Adding a PREAMBLE may increase control overhead for small messages. 
Therefore, it is preferable to use it only for messages that exceed the preamble_threshold.


### Limiting IWANT Requests

When a peer receives an IHAVE announcement for a message ID not present in the seen cache, 
the peer must also check the ongoing_receives list before making an IWANT request. 

If the message ID is found in the ongoing_receives list, 
the peer should postpone sending the IWANT request for a defer_interval. 
The defer_interval may be based on the estimated message download duration.

If the message download completes before the defer_interval expires, 
the IWANT request for that message will not be generated. 
However, if the defer_interval elapses and the download has not completed, 
the peer can proceed to make the IWANT request for the missing message. 

The total number of outstanding IWANT requests for a single message must not exceed max_iwant_requests.
Every peer must respond to incoming IWANT requests as long as the number of responses remains within the limits 
defined by [gossipsub v1.1](https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/gossipsub-v1.1.md).
Failing to do so should result in a behavioral penalty. 
This will discourage peers from intentionally not replying to IWANT requests.

### IMRECEIVING Message

The IMRECEIVING message serves a distinct purpose compared to the IDONTWANT message. 
An IDONTWANT can only be transmitted after receiving the entire message. 
In contrast, an IMRECEIVING should be transmitted immediately after receiving a PREAMBLE, indicating an ongoing large message reception.
The IMRECEIVING message requests peers in the full message mesh to refrain from resending a large message that is already being received.

When a peer receives a PREAMBLE indicating a message ID that is not present in the seen cache and ongoing_receives list, 
it should send IMRECEIVING messages to the nodes in its full message mesh. 
On receiving an IMReceiving from a peer, 
a node should refrain from sending the message indicated by the IMRECEIVING to that peer.  

A corresponding IDONTWANT from the peer that issued IMRECEIVING will indicate successful reception of the message. 
Otherwise, the peers in the full message may proceed with a push-based or a pull-based operation depending upon the selected fallback_mode.
See [Safety Strategy](#safety-strategy) below.


## Safety Strategy

A malicious peer can attempt to exploit this approach by sending a PREAMBLE but 
never completing (or deliberately delaying) the promised message transfer or 
by misrepresenting the message size, 
potentially hindering the message propagation across the network.
A simple defense mechanism can remedy this problem.

- A peer must accept and process a PREAMBLE only from mesh members and only once for any message ID.
- A peer must limit the maximum number of PREAMBLE announcements for unfinished message transfers to peer_preamble_announcements.
- A peer must extract the message ID and length from PREAMBLE to report in IMRECEIVING announcements.
- A peer must ignore a received IMRECEIVING message if the reported length field does not correspond to the announced message ID.
- If a peer identifies a misrepresented length field in a received PREAMBLE, it must penalize the sender for an invalid message.

Upon receiving a PREAMBLE, a peer uses the length field to conservatively estimate message transfer duration, 
ensuring sufficient time allocation for message reception. 
If a message transfer is not complete during the estimated duration, 
the sender is penalized through a behavioral penalty, 
and message retrieval is performed based on a pull-based or a push-based strategy, 
as selected by the fallback_mode.

In a pull-based strategy, the peer receiving the message uses an IWANT request to fetch the message. 
The peer can infer message availability at mesh members through received IDONTWANT announcements.
In a push-based model, mesh members proactively send the message 
if they do not receive a corresponding IDONTWANT announcement within the estimated message transfer duration. 
Mesh members can derive a conservative estimate for duration based on the length field.

Negative scoring helps prune non-conforming peers, 
whereas the fallback strategy helps recover from incomplete message transfers.

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

