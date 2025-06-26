# Partial Messages Extension

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r0, 2025-06-23  |

Authors: [@marcopolo, @cskiraly]

Interest Group: TODO

[@marcopolo]: https://github.com/marcopolo
[@cskiraly]: https://github.com/cskiraly

See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Overview

Partial Messages Extensions allow users to transmit only a small part of a
message rather than a full message. This is especially useful in cases where
this a large messages and a peer is missing only a small part of the message.

Much of the complexity around partial messages is contained by the Gossipsub
implementation. Applications require little changes to benefit from this
extension.

## Motivation

The main motivation for this extension is optimizing Ethereum's Data
Availability Sampling (DAS) protocol. In Ethereum's upcoming fork, Fusaka,
custodied data is laid out in a matrix, where the rows represent user data
(called blobs), and the columns represent a slice across all blobs (each blob
slice is called a cell). These columns are propagated with Gossipsub. At the
time of writing it is common for a node to already have all the blobs from its
mempool, but in cases where it doesn't (~38%[1]) have _all_ of the blobs it
almost always has _most_ blobs (today, it almost always has all but one [1]).

This extension would allow nodes to only request the column message part
belonging to the missing blob. Reducing the network resource usage
significantly. As an example, if there are 32 blob cells in a column and the
node has all but one cell, this would result in a transfer of 2KiB rather than
64KiB per column. and since nodes custody at least 8 columns, the total savings
per slot is around 500KiB, or 4 Megabits per slot.

Later, partial messages could enable further optimizations:
- If cells can be validated individually, as in the case of DAS, partial messages
could also be forwarded, allowing us to reduce the store-and-forward delay [2].
- Finally, in the FullDAS construct, where both row and column topics are
defined, partial messages allow cross-forwarding cells between these topics [2].

## Protocol Messages

The following section specifies the semantics of each new protocol message.

### PartialIWANT

Partial IWants signal to a receiver that the sending peer only wants a part of
some message.

The message to which the peer is requesting a part of is identified by the
`groupID` identifier. This is similar to a complete message's `MessageID`, but,
in contrast to a content-based message id, does not require the full message to
compute. For example, in the Ethereum use case, this could simply be the hash of
the signed block header.

The `topicID` references the Gossipsub topic a message, and thus its parts,
belong to.

The `metadata` field is opaque application defined metadata associated with this
request. This can be a bitmap, a list of ranges, or a bloom filter. The
application generates this and consumes this.


Nodes SHOULD assume a `partialIWANT `implies a `IDONTWANT `for the full message.

### PartialIDONTWANT

PartialIDONTWANT serves to cancel any pending PartialIWANTs

### PartialIHAVE

Partial IHave allow nodes to signal HAVE information before receiving all
segments, unlocking the use of partialIWANT in more contexts.

Partial IHAVE messages can be used both in the context of lazy push, notifying
peers about reception progress, and in the context of heartbeats, sending
also Partial IHAVEs.

The structure of PartialIHAVE is analogous to that of PartialIWANT.

Part status (the metadata) is set and updated by the upper layer.
Implementations are free to select when to send an update to their peers based
on signaling bandwidth tradeoff considerations.

## Application Interface

Message contents are application defined. Thus splitting a message must be
application defined. Here is a list of operations an application is expected to
provide to Gossipsub to enable partial message delivery.

1. Splitting a message into partial message.
2. Given two partial messages, merge them into a more complete partial message.
  2a. If merging results in a complete message, return the complete message.
3. Encode and decode a partial message.
4. Given a partial message, encode a request for the rest of the message.
5. Given the request above and a complete message, return relevant parts of the
   message.


TODO, think about this more.

## Protobuf

```protobuf
syntax = "proto2";

message PartialMessagesExtension {
  optional PartialMessage message = 1;
  optional PartialIWANT iwant = 2;
  optional PartialIDONTWANT idontwant = 3;
  optional PartialIHAVE ihave = 4;
}

message PartialMessage {
	optional bytes topicID = 1;
  optional bytes data = 2;
}

message PartialIWANT {
  optional bytes topicID = 1;
  optional bytes groupID = 2;
  optional bytes metadata = 3;
}

message PartialIDONTWANT {
	optional bytes topicID = 1;
  optional bytes groupID = 2;
  optional bytes metadata = 3;
}

message PartialIHAVE {
  optional bytes topicID = 1;
  optional bytes groupID = 2;
  optional bytes metadata = 3;
}

```

[1]: https://ethresear.ch/t/is-data-available-in-the-el-mempool/22329
[2]: https://ethresear.ch/t/fulldas-towards-massive-scalability-with-32mb-blocks-and-beyond/19529#possible-extensions-13
