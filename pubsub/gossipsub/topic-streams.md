# Topic Streams Extension

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r0, 2026-06-29  |

Authors: [@marcopolo]

Interest Group: [@sukunrt], `TODO: expand`

[@marcopolo]: https://github.com/marcopolo
[@sukunrt]: https://github.com/sukunrt

See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Overview

Gossipsub v1.3 uses a single stream per direction for all RPCs. This introduces
some problems: unnecessary head of line blocking between messages (especially
problematic when a large message in one topic delays small messages in another
topic) and topic name overhead on each message.

The Topic Streams Extension addresses these problems. It moves topic scoped
application messages to separate long-lived streams.

## Negotiation

Peers MUST use this extension with each other when both sides advertise support
for this extension in the `ControlExtensions` message.

The `ControlExtensions` message is the first message a peer sends and comes at
the same time or earlier than a peer's subscriptions. Since a publisher should
not publish messages to a peer before learning of its subscriptions, there is
no window when a publisher wishes to publish a message, but does not know if
the peer supports Topic Streams.

Because streams are multiplexed independently, a peer MAY receive an inbound
topic stream before receiving the opening peer's `ControlExtensions` message.
If the receiving peer supports Topic Streams, it MUST assume that the opening
peer supports Topic Streams and accept and process the stream. If the receiving
peer later receives a `ControlExtensions` message indicating that the opening
peer does not support Topic Streams, it MUST treat this as a protocol violation
and abort the connection as described in [Aborting the Connection on Protocol
Violation](#aborting-the-connection-on-protocol-violation).

## Aborting the Connection on Protocol Violation

If a receiver receives a message that violates a MUST condition,
the receiver MUST reset the connection to the peer and send error code
`0xd52505` when the transport allows it. This code signifies a Topic Streams
Protocol Violation error, and is derived from the first 3 bytes of the sha256
hashsum of the string `gossipsub-topic-streams`. (i.e. `echo -n
"gossipsub-topic-streams" | sha256sum | head -c 6`)

## Topic Streams

A peer MUST open a bidirectional stream for each topic that it wishes to send
application messages for. Despite being bidirectional streams, they are treated
as unidirectional streams. If both sides wish to publish messages for a given
topic, both sides MUST open a bidirectional stream.

The responder of the bidirectional stream MUST NOT write on the stream after
protocol negotiation completes.

The protocol id for a topic stream is `/gsts/v0beta`.

### Control Stream

When this extension is negotiated, the original gossipsub stream becomes the
control stream. Subscriptions, `IHAVE`, `IWANT`, `GRAFT`, `PRUNE`, `IDONTWANT`,
`ControlExtensions`, and any other non-application RPC or control traffic MUST
remain on this stream.

A stream opened with protocol id `/gsts/v0beta` and identified by a
`TopicRPCHeader` is a topic stream. Application publish payloads (`Message`,
represented on the wire by `TopicScopedMessage`, and
`PartialMessagesExtension`) MUST be sent on a topic stream and MUST NOT be
published on the control stream.

### Topic Stream Header

Upon opening the topic stream, the initiator MUST send a single length-prefixed
`TopicRPCHeader` protobuf message. The `TopicRPCHeader` MUST contain a topic. The receiver uses this to identify the topic associated with the stream.
Afterwards, only length-prefixed `TopicRPC` protobuf messages are allowed.

If the receiver does not receive a topic header within a reasonable timeout, it
SHOULD reset the stream. One second is a reasonable timeout for most
applications.

`TopicRPC` messages MUST NOT be empty. They MUST contain either a partial or
publish message. The data length of the application message MUST be non zero.

The initiator MUST close the existing topic stream for a topic before it opens
a new one. Because the transport can reorder packets, the receiver can get a
new stream before the close of the old one. This is not a violation. The
receiver MUST accept up to 3 open streams for a topic and SHOULD process them
in the sequence opened. If there are more than 3, the receiver SHOULD reset
the excess streams and downscore the peer.

If the receiver receives a topic stream for a topic it is not subscribed to and
has not recently published partial messages to (via fanout), it SHOULD
downscore the peer. The receiver MUST NOT downscore a peer for opening a topic
stream for a topic the receiver recently unsubscribed from, as the peer may not
have received the unsubscribe message before opening the topic stream.

### Lifecycle

A topic stream is created when a node publishes a topic message to a peer. It is
closed when either the peer unsubscribes from the topic, or the publisher will
no longer publish on the topic. Either side may close the stream.

Implementations MAY choose to keep topic streams open only for mesh and fanout
peers and use a short-lived stream when responding to `IWANTs`.

### Topic Scoped Messages

A stream opened with protocol id `/gsts/v0beta` and identified by a
`TopicRPCHeader` is a topic stream. The original gossipsub stream is the
[control stream](#control-stream) after negotiation.

When a peer wishes to publish an application `Message`, it MUST send it as a
`TopicScopedMessage` on the topic stream and MUST NOT publish it on the control
stream. `PartialMessagesExtension` application payloads likewise MUST be sent
on the topic stream and MUST NOT be published on the control stream. All
subscriptions and other non-application RPC or control traffic MUST remain on
the control stream.

Implementations MUST NOT set the topic name when sending the message over the
wire.

When verifying a message's signature or deriving a message's ID,
implementations MUST reconstruct the full `Message` by setting `topic` to the
value from the stream's `TopicRPCHeader`, and verify the signature against
that. Implementations SHOULD also populate the `topic` before delivering the
message to the application.

### Partial Messages

If the partial message extension has been negotiated with this extension, peers
MUST send each other Partial Messages on the topic stream.
Peers MUST NOT send Partial Messages on the control stream.

`PartialMessagesExtension` protobuf messages MUST omit the `topicID` field when
sent over the wire. Implementations MUST set the `topicID` field after
reading the message from the wire.

NB: Protobuf bytes and strings are interchangeable; implementations are free to
choose the representation that works better for them.
