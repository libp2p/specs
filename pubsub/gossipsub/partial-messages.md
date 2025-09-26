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

### partialMessage

The `partialMessage` field encodes one or more parts of the full message. The
encoding is application defined.

### partsMetadata

The `partsMetadata` field encodes the parts a peer has and wants. The encoding
is application defined. An unset value carries no information besides that the
peer did not send a value.

Upon receiving a `partsMetadata` a node SHOULD respond with only parts the peer
wants.

A later `partsMetadata` replaces a prior one.

`partsMetadata` can be used during heartbeat gossip to inform non-mesh topic
peers about parts this node has.

Implementations are free to select when to send an update to their peers based
on signaling bandwidth tradeoff considerations.

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

This specific interface is not intended to be normative to implementations, it
is only an example of one possible API.

Message contents are application defined, thus splitting a message must be
application defined. Applications should provide a Partial Message type that
supports the following operations:

1. `.GroupID() -> GroupID: bytes`
2. `.PartialMessageBytes(partsMetadata: bytes) -> Result<(EncodedPartialMessage: bytes, newPartsMetadata: bytes), Error>`
  a. The method should return an encoded partial message with just the parts the
     peer requested.
  b. The returned `newPartsMetadata` can be used to track parts that could not
     be fulfilled. This allows the GossipSub library to avoid sending duplicate
     parts to the same peer.
3. `.PartsMetadata() -> bytes`

Gossipsub in turn provides a `.PublishPartial(PartialMessage)` method.

## Protobuf

Refer to the protobuf registry at `./extensions/extensions.proto`

## Open Questions

- Do we want to add a TTL to PartialIWANTs? This would allow us to cancel them after some time.
- Should we rename the metadata bytes to iwant and ihave?
- In the bitmap usecase, iwant/ihave are simply inverses of each other. Do we need to send them both?
- There's a bit of extra complexity around assuming opaque metadata, is it worth it?

[1]: https://ethresear.ch/t/is-data-available-in-the-el-mempool/22329
[2]: https://ethresear.ch/t/fulldas-towards-massive-scalability-with-32mb-blocks-and-beyond/19529#possible-extensions-13
