# Partial Messages Extension

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r0, 2025-06-23  |

Authors: [@marcopolo], [@cskiraly]

Interest Group: [@jxs], [@dknopik], [@sukunrt], [@raulk]

[@marcopolo]: https://github.com/marcopolo
[@cskiraly]: https://github.com/cskiraly
[@jxs]: https://github.com/jxs
[@raulk]: https://github.com/raulk
[@dknopik]: https://github.com/dknopik
[@sukunrt]: https://github.com/sukunrt

See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Overview

Partial Messages Extensions allow users to transmit only a small part of a
message rather than a full message. This is especially useful in cases where
there is a large message and a peer is missing only a small part of the
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

The following section specifies the semantics of each field in the protocol
message.

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

The `SubOpts` message is how a peer subscribes to a topic.

Partial Messages uses the same mesh as normal Gossipsub messages. It is a
replacement to "full" messages. A node requests a peer to send partial messages
for a specific topic by setting the `requestsPartial` field in the `SubOpts`
message to true. A node signals support for sending partial messages on a given
topic by setting the `supportsSendingPartial` field in `SubOpts` to true. A node can
support sending partial messages without wanting to receive them.

If a node requests partial messages, it MUST support sending partial messages.

A node uses a peer's `supportsSendingPartial` setting to know if it can send a
partial message request to a peer. It uses its `requestsPartial` setting to know
whether to send the peer a full message or a partial message.

If a peer supports partial messages on a topic but did not request them, a node
MUST omit the `partialMessage` field of the `PartialMessagesExtension` message
when sending a message to this peer. In other words, it MUST NOT send this peer
encoded partialMessage data since it did not request it.

If a node does not support the partial message extension, it MUST ignore the
`requestPartial` and `supportsPartial` fields. This is the default behavior of
protobuf parsers.

The `requestPartial` and `supportsPartial` fields value MUST be ignored when a
peer sends an unsubscribe message `SubOpts.subscribe=false`.

#### Behavior table

The following table describes the expected behavior of receiver of a `SubOpts`
message for a given topic.

| SubOpts.requestsPartial | behavior of receiver that supports partial messages for the topic                                 |
| ------------------------ | ------------------------------------------------------------------------------------------------- |
| true                     | The receiver SHOULD send partial messages (data and metadata) to this peer.                       |
| false                    | receiver MUST NOT send partial message data to this peer. The receiver SHOULD send full messages. |

| SubOpts.requestsPartial | behavior of receiver that does not support partial messages for the topic |
| ------------------------ | ------------------------------------------------------------------------- |
| \*                       | The receiver SHOULD send full messages.                                   |

| SubOpts.supportsSendingPartial | behavior of receiver that requested partial messages for the topic                                               |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| true                     | The receiver expects the peer to respond to partial message requests, and receive `partsMetadata` from the peer. |
| false                    | The receiver expects full messages.                                                                              |

| SubOpts.supportsSendingPartial | behavior of receiver that did not request partial messages for the topic |
| ------------------------ | ------------------------------------------------------------------------ |
| \*                       | The receiver expects full messages                                       |


## Partial Message Gossip

Partial Messages can replace Gossipsub's IHAVE/IWANT with a message that
provides more context (via the Group ID) and allows for partial responses.

When Gossiping, a node that supports partial messages SHOULD NOT send an `IHAVE`
to a peer that requested partial messages. The node SHOULD send a partial message
instead.

## Implementation Recommendations

The following section is not intended to be normative, it is only meant to
provide rough recommendations to implementations.

### Sending `partsMetadata`

Implementations should send their `partsMetadata` whenever it changes. The goal
being to provide an up-to-date view of its parts to its peers. Implementations
should not send duplicate `partsMetadata` to peers when nothing has changed.

If a node has previously sent a peer its `partsMetadata`, and that peer has
responded with parts, the node can assume the peer's view of itself is the union
of the its previously sent `partsMetadata `and the remote peer's
`partsMetadata`. The node does not need to send this peer its updated
`partsMetadata` if its `partsMetadata` has not changed since the previously sent
`partsMetadata`.

On the other side, when a node responds to a peer's request for parts, it should
update the peer's `partsMetadata` with the union of its `partsMetadata` and the
peers `partsMetadata`.

Due to the distributed nature of peers, this might result in a period of time
where a peer's `partsMetadata` is not exactly correct, but it should become
eventually consistent.

### Merging Eager Data with a peer's `partsMetadata`.

When eagerly sending data, a node should track which parts it has sent to the
peer in order to update its view of the peer's `partsMetadata`. This allows the
node to avoid sending duplicate data in the case that a peer concurrently sends
a `partsMetadata` that requests data already eagerly sent.

### Reacting to `IHAVE`

If a node requests partial messages and is connected partial message capable
peers, it MAY prefer to delay reacting to a peer's `IHAVE` message in order to
give the opportunity for a partial message request to finish and provide the
missing message more efficiently.

### DoS Resiliency

- Limit the amount of peer initiated state you track.

### Eager pushing data

If you have a peer's `partsMetadata` you should use that to decide what to send
to the peer. The corollary is that you do not eager push data to a peer that has
given you its `partsMetadata`.

### Example Application Interface

Message contents are application defined, thus splitting a message must be
application defined. Applications should provide a Partial Message type that
supports the following operations:

1. `.GroupID() -> GroupID: bytes`
2. `.PartialMessageBytes(partsMetadata: bytes) -> Result<(EncodedPartialMessage: bytes), Error>`
   1. The method should return an encoded partial message with just the parts the
      peer requested.
3. `.EagerPartialMessageBytes() -> Result<(EncodedPartialMessage: bytes, partsMetadata: bytes), Error>`
   1. The method should return an encoded partial message of eager data that
      should be sent, along with the partsMetadata a peer would have after
      receiving the encoded partial message.
4. `.PartsMetadata() -> bytes`: The parts this partial message has.

Gossipsub in turn provides a `.PublishPartial(PartialMessage)` method. This
method should be idempotent. The application should be able to call it multiple
times, and the library should make sure not to send redundant or duplicate
messages to peers.

When Gossipsub receives a partial message it MUST forward it to the application.
The application decides if it should act on the message by either requesting
parts or forwarding the message. Both are done with `.PublishPartial`.

Gossipsub MUST forward all messages to the application, not just messages from
mesh peers.

### Fanout and Gossip messages

Fanout and Gossip messages by definition come from non-mesh peers. Partial
messages, without eager data, require an exchange of bitmaps before parts are
transferred. In order for fanout and gossip messages to be useful, the Gossipsub
implementation SHOULD include the peers that sent them in the list of peers to
publish partial messages to. This allows the application to simply call
`PublishPartial` to respond to both mesh and non mesh peers.

## Upgrading a topic to use partial messages

Rolling out partial messages on an existing topic allows for incremental
migration with backwards compatibility. The steps are as follows:

1. Deploy nodes that support partial messages, but do not request them for the
   target topic. The goal is to seed support for partial messages before making
   the switch. Nodes signal their support for partial messages by setting the
   subscribe option `supportsSendingPartial` to true.
2. Slowly deploy and monitor nodes that request (and implicitly support) partial
   messages. These nodes should find peers that send them partial messages from
   the previous step. Nodes request partial messages by setting the subscribe
   option `requestPartial` to true.

### Supporting both full and partial messages for a topic

Partial messages use the same mesh as "full" messages. Supporting both is
straightforward. If a peer subscribes to a topic with a "requestPartial", the
node SHOULD send the peer partial messages. Otherwise, send the node full
messages.

On the receiving side, if the node is in a mixed network of partial and full
messages, and it requests partial messages, the node MUST support receiving full
messages.

## Creating a topic to only use partial messages

There is currently no mechanism to requre that a topic only be used for partial
messages. A future extension may define this.

With this extension nodes can choose to only graft peers that support partial
messages, and prune those that do not.

## Protobuf

Refer to the protobuf registry at `./extensions/extensions.proto`

[1]: https://ethresear.ch/t/is-data-available-in-the-el-mempool/22329
[2]: https://ethresear.ch/t/fulldas-towards-massive-scalability-with-32mb-blocks-and-beyond/19529#possible-extensions-13
