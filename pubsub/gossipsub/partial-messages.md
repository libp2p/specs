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
there is a large messages and a peer is missing only a small part of the
message.

## Terms and Definitions

**Full Message**: A Gossipsub Message.

**Message Part**: The smallest verifiable part of a message.

**Partial Message**: A group of one or more message parts.

**Group ID**: An identifier to some Full Message. This must not depend on
knowing the full message, so it can not simply be a hash of the full message.

## Motivation

The main motivation for this extension is optimizing Ethereum's Data
Availability (DA) protocol. In Ethereum's upcoming fork, Fusaka, custodied data
is laid out in a matrix per block, where the rows represent user data (called
blobs), and the columns represent a slice across all blobs included in the block
(each blob slice in the column is called a cell). These columns are propagated
with Gossipsub. At the time of writing it is common for a node to already have
all the blobs from its mempool, but in cases where it doesn't (~38%[1]) have
_all_ of the blobs it almost always has _most_ of the blobs (today, it almost
always has all but one [1]). More details of how this integrates with Ethereum
can be found at the [consensus-specs
repo](https://github.com/ethereum/consensus-specs/pull/4558)

This extension would allow nodes to only request the column message part
belonging to the missing blob. Reducing the network resource usage
significantly. As an example, if there are 32 blob cells in a column and the
node has all but one cell, this would result in a transfer of 2KiB rather than
64KiB per column. and since nodes custody at least 8 columns, the total savings
per slot is around 500KiB.

Later, partial messages could enable further optimizations:
- If cells can be validated individually, as in the case of DAS, partial
  messages could also be forwarded, allowing us to reduce the store-and-forward
  delay [2].
- Finally, in the FullDAS construct, where both row and column topics are
  defined, partial messages allow cross-forwarding cells between these topics
  [2].

## Advantage of Partial Messages over smaller Gossipsub Messages

Partial Messages within a group imply some structure and correlation. Thus,
multiple partial messages can be referenced succinctly. For example, parts can
be referenced by bitmaps, ranges, or a bloom filter.

The structure of partial messages in a group, as well as how partial messages
are referenced is application defined.

If, in some application, a group only ever contained a single partial message,
then partial messages would be the same as smaller messages.


## Protocol Messages

The following section specifies the semantics of each new protocol message.

### PartialIWANT

A `PartialIWANT` signal to a receiver that the sending peer only wants a part of
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

A later `PartialIWANT` serve to refine the request of prior a prior `PartialIWANT`.

Nodes SHOULD assume a `PartialIWANT` implies a `IDONTWANT` for the full message.

### PartialIHAVE

A `PartialIHAVE` allows nodes to signal HAVE information before receiving all
segments, unlocking the use of `PartialIWANT` in more contexts.

In the context of partial messages, it is more useful than IHAVE as it includes
the group ID. In contrast, an IHAVE does not. A receiving peer has no way to
link an IHAVE's message ID with a group ID, without having the full message.

A `PartialIHAVE` message can be used both in the context of lazy push, notifying
peers about available parts, and in the context of heartbeats as a replacement
to IHAVEs.

The structure of `PartialIHAVE` is analogous to that of `PartialIWANT`.

The metadata, as in a `PartialIWANT`, is application defined. It is some encoding
that represents the parts the sender has.

Implementations are free to select when to send an update to their peers based
on signaling bandwidth tradeoff considerations.

Receivers MUST treat a `PartialIHAVE` as a signal that the peer does not want
the indicated part.

### Changes to `SubOpts` and interaction with the existing Gossipsub mesh.

Partial Messages uses the same mesh as normal Gossipsub messages. It is a
replacement to "full" messages. A node requests a peer to use partial messages
for a specific topic by setting the `partial` field in the `SubOpts` message.
The `SubOpts` message is how a peer subscribes to a topic.

If a node receives a subscribe request with the `partial` field set to true, it
MUST send partial messages instead of full messages.

It is an error to set the partial field true if the peer does not support
partial extensions.

The partial field value MUST be ignored when a peer sends an unsubscribe message
`SubOpts.subscribe=false`.

## Application Interface

Message contents are application defined. Thus splitting a message must be
application defined. Applications should provide a Partial Message type that
supports the following operations:

1. `.GroupID() -> GroupID: bytes`
2. `.PartialMessageBytesFromMetadata(metadata: bytes) -> Result<(EncodedPartialMessage: bytes, metadata: bytes), Error>` (When responding to a `PartialIWANT` or eagerly pushing a partial message)
  a. The returned metadata represents the still missing parts. For example, if a
     peer is only able to fulfill a part of the the request, the returned
     metadata represents the parts it couldn't fulfill.
3. `.ExtendFromEncodedPartialMessage(data: bytes) -> Result<(), Error>` (When receiving a `PartialMessage`)
4. `.MissingParts() -> Result<metadata: bytes, Error>` (For `PartialIWANT`)
5. `.AvailableParts() -> Result<metadata: bytes, Error>` (For `PartialIHAVE`)

Gossipsub in turn provides a `.PublishPartial(PartialMessage)` method.

Note that this specific interface is not intended to be normative to
implementations, rather, it is high level summary of what each layer should
provide.

## Protobuf

Refer to the protobuf registry at `./extensions/extensions.proto`

## Open Questions

- Do we want to add a TTL to PartialIWANTs? This would allow us to cancel them after some time.
- Should we rename the metadata bytes to iwant and ihave?
- In the bitmap usecase, iwant/ihave are simply inverses of each other. Do we need to send them both?
- There's a bit of extra complexity around assuming opaque metadata, is it worth it?

[1]: https://ethresear.ch/t/is-data-available-in-the-el-mempool/22329
[2]: https://ethresear.ch/t/fulldas-towards-massive-scalability-with-32mb-blocks-and-beyond/19529#possible-extensions-13
