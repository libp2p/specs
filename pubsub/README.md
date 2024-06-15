# PubSub interface for libp2p

> Generalized publish/subscribe interface for libp2p.

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 3A              | Recommendation | Active | r3, 2020-09-25  |

Authors: [@whyrusleeping], [@protolambda], [@raulk], [@vyzo].

Interest Group: [@yusefnapora], [@raulk], [@vyzo], [@Stebalien], [@jamesray1], [@vasco-santos]

[@whyrusleeping]: https://github.com/whyrusleeping
[@yusefnapora]: https://github.com/yusefnapora
[@raulk]: https://github.com/raulk
[@vyzo]: https://github.com/vyzo
[@Stebalien]: https://github.com/Stebalien
[@jamesray1]: https://github.com/jamesray1
[@vasco-santos]: https://github.com/vasco-santos
[@protolambda]: https://github.com/protolambda

See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Table of Contents

- [PubSub interface for libp2p](#pubsub-interface-for-libp2p)
    - [Table of Contents](#table-of-contents)
    - [Overview](#overview)
    - [Implementations](#implementations)
    - [The RPC](#the-rpc)
    - [The Message](#the-message)
    - [Message Signing](#message-signing)
      - [Signature Policy](#signature-policy)
    - [Message Identification](#message-identification)
    - [The Topic Descriptor](#the-topic-descriptor)
        - [AuthOpts](#authopts)
            - [AuthMode 'NONE'](#authmode-none)
            - [AuthMode 'KEY'](#authmode-key)
            - [AuthMode 'WOT'](#authmode-wot)
        - [EncOpts](#encopts)
            - [EncMode 'NONE'](#encmode-none)
            - [EncMode 'SHAREDKEY'](#encmode-sharedkey)
            - [EncMode 'WOT'](#encmode-wot)
    - [Topic Validation](#topic-validation)


## Overview

This is the specification for generalized pubsub over libp2p. Pubsub in libp2p
is currently still experimental and this specification is subject to change.
This document does not go over specific implementation of pubsub routing
algorithms, it merely describes the common wire format that implementations
will use.

libp2p pubsub currently uses reliable ordered streams between peers. It assumes
that each peer is certain of the identity of each peer it is communicating
with.  It does not assume that messages between peers are encrypted, however
encryption defaults to being enabled on libp2p streams.

You can find information about the PubSub research and notes in the following repos:

- https://github.com/libp2p/research-pubsub
- https://github.com/libp2p/pubsub-notes

## Implementations
- FloodSub, simple flooding pubsub (2017)
  - [libp2p/go-libp2p-pubsub/floodsub.go](https://github.com/libp2p/go-libp2p-pubsub/blob/master/floodsub.go);
  - [libp2p/js-libp2p-floodsub](http://github.com/libp2p/js-libp2p-floodsub);
  - [libp2p/rust-libp2p/floodsub](https://github.com/libp2p/rust-libp2p/tree/master/protocols/floodsub)
  - [status-im/nim-libp2p/floodsub](https://github.com/status-im/nim-libp2p/blob/master/libp2p/protocols/pubsub/floodsub.nim)
- GossipSub, extensible baseline pubsub (2018)
  - [gossipsub](https://github.com/libp2p/specs/tree/master/pubsub/gossipsub#implementation-status)
- [EpiSub](https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/episub.md), an epidemic broadcast tree router (defined 2018, not yet started as of Oct 2018)

## Stream management

Data should be exchanged between peers using two separately negotiated streams,
one inbound, one outbound. These streams are treated as unidirectional streams.
The outbound stream is used only to write data. The inbound stream is used only
to read data.

## The RPC

All communication between peers happens in the form of exchanging protobuf RPC
messages between participating peers.

The `RPC` protobuf is as follows:

```protobuf
syntax = "proto2";
message RPC {
	repeated SubOpts subscriptions = 1;
	repeated Message publish = 2;

	message SubOpts {
		optional bool subscribe = 1;
		optional string topicid = 2;
	}
}
```

This is a relatively simple message containing zero or more subscription
messages, and zero or more content messages. The subscription messages contain
a topicid string that specifies the topic, and a boolean signifying whether to
subscribe or unsubscribe to the given topic. True signifies 'subscribe' and
false signifies 'unsubscribe'.

## The Message

The RPC message can contain zero or more messages of type 'Message'. The Message protobuf looks like this:

```protobuf
syntax = "proto2";
message Message {
	optional string from = 1;
	optional bytes data = 2;
	optional bytes seqno = 3;
        required string topic = 4;
	optional bytes signature = 5;
	optional bytes key = 6;
}
```

The `optional` fields may be omitted, depending on the
[signature policy](#message-signing) and
[message ID function](#message-identification).

The `from` field (optional) denotes the author of the message. This is the peer
who initially authored the message, and NOT the peer who propagated it. Thus, as
the message is routed through a swarm of pubsubbing peers, the original
authorship is preserved.

The `seqno` field (optional) is a 64-bit big-endian uint that is a linearly
increasing number that is unique among messages originating from each given
peer. No two messages on a pubsub topic from the same peer should have the same
`seqno` value, however messages from different peers may have the same sequence
number. In other words, this number is not globally unique. It is used in
conjunction with `from` to derive a unique `message_id` (in the default
configuration).

Henceforth, we define the term **origin-stamped messaging** to refer to messages
whose `from` and `seqno` fields are populated.

The `data` (optional) field is an opaque blob of data representing the payload.
It can contain any data that the publisher wants it to.

The `topic` field specifies a topic that this message is being
published to.

The `signature` and `key` fields (optional) are used for message signing, if
such feature is enabled, as explained below.

The size of the `Message` should be limited, say to 1 MiB, but could also
be configurable, for more information see
[issue 118](https://github.com/libp2p/specs/issues/118), while messages should be
rejected if they are over this size.
Note that for applications where state such as messages is
stored, such as blockchains, it is suggested to have some kind of storage
economics (see e.g.
[here](https://ethresear.ch/t/draft-position-paper-on-resource-pricing/2838),
[here](https://ethresear.ch/t/ethereum-state-rent-for-eth-1-x-pre-eip-document/4378)
and
[here](https://ethresear.ch/t/improving-the-ux-of-rent-with-a-sleeping-waking-mechanism/1480)).

## Message Identification

Pubsub requires to uniquely identify messages via a message ID. This enables
a wide range of processes like de-duplication, tracking, scoring,
circuit-breaking, and others.

**The `message_id` is calculated from the `Message` struct.**

By default, **origin-stamping** is in force. This strategy relies on the string
concatenation of the `from` and `seqno` fields, to uniquely identify a message
based on the *author*.

Alternatively, a user-defined `message_id_fn` may be supplied, where
`message_id_fn(Message) => message_id`. Such a function could compute the hash
of the `data` field within the `Message`, and thus one could reify
**content-addressed messaging**.

If fabricated collisions are not a concern, or difficult enough within the
window the message is relevant in, a `message_id` based on a short digest of
inputs may benefit performance.

> **[[ Margin note ]]:** There's a potential caveat with using hashes instead of
> seqnos: the peer won't be able to send identical messages (e.g. keepalives)
> within the timecache interval, as they will get treated as duplicates. This
> consequence may or may not be relevant to the application at hand.
> Reference: [#116](https://github.com/libp2p/specs/issues/116).

**Note that the availability of these fields on the `Message` object will depend
on the [signature policy](#signature-policy) configured for the topic.**

Whichever the choice, it is crucial that **all peers** participating in a topic
implement identical message ID calculation logic, or the topic will malfunction.

## Message Signing

Signature behavior is configured in two axes: signature creation, and signature
verification.

**Signature creation.** There are two configurations possible:

* `Sign`: when publishing a message, perform **origin-stamping** and produce a
  signature.
* `NoSign`: when publishing a message, do not perform **origin-stamping** and
  do not produce a signature.

For signing purposes, the `signature` and `key` fields are used:
- The `signature` field contains the signature.
- The `key` field contains the signing key when it cannot be inlined in
  the source peer ID (`from`). When present, it must match the peer ID.

The signature is computed over the marshalled message protobuf _excluding_ the
`signature` field itself.

This includes any fields that are not recognized, but still included in the
marshalled data.

The protobuf blob is prefixed by the string `libp2p-pubsub:` before signing.

> **[[ Margin note: ]]** Protobuf serialization is non-deterministic/canonical,
> and the same data structure may result in different, valid serialised bytes
> across implementations, as well as other issues. In the near future, the
> signature creation and verification algorithm will be made deterministic.

**Signature verification.** There are two configurations possible:

* `Strict`: either expect or not expect a signature.
* `Lax` (legacy, insecure, underterministic, to be deprecated): accept a signed
  message if the signature verification passes, or if it's unsigned.

When signature validation fails for a signed message, the implementation must
drop the message and omit propagation. Locally, it may treat this event in
whichever manner it wishes (e.g. logging, penalization, etc.).

#### Signature Policy Options

The usage of the `signature`, `key`, `from`, and `seqno` fields in `Message`
is configurable per topic.

> **[[ Implementation note ]]:** At the time of writing this section,
> go-libp2p-pubsub (reference implementation of this spec) allows for
> configuring the signature policy at the **global pubsub instance level**.
> This needs to be pushed down to topic-level configuration.
> Other implementations should support topic-level configuration, as this spec
> mandates.

The intersection of signing behaviours across the two axes (signature creation
and signature verification) gives way to four signature policy options:

* `StrictSign`, `StrictNoSign`. Deterministic, usage encouraged.
* `LaxSign`, `LaxNoSign`. Non-deterministic, legacy, usage discouraged. Mostly
  for backwards compatibility. Will be deprecated. If the implementation decides
  to support these, their use should be discouraged through deprecation warnings.

**`StrictSign` option**

On the producing side:
  - Build messages with the `signature`, `key` (`from` may be enough for
    certain inlineable public key types), `from` and `seqno` fields.

On the consuming side:
  - Enforce the fields to be present, reject otherwise.
  - Propagate only if the fields are valid and signature can be verified,
    reject otherwise.

**`StrictNoSign` option**

On the producing side:
  - Build messages without the `signature`, `key`, `from` and `seqno` fields.
  - The corresponding protobuf key-value pairs are absent from the marshalled
    message, not just empty.

On the consuming side:
  - Enforce the fields to be absent, reject otherwise.
  - Propagate only if the fields are absent, reject otherwise.
  - A `message_id` function will not be able to use the above fields, and should
    instead rely on the `data` field. A commonplace strategy is to calculate
    a hash.

**`LaxSign` legacy option**

_Not required for backwards-compatibility. Considered insecure, nevertheless
defined for completeness._

Always sign, and verify incoming signatures, but accept unsigned messages.

On the producing side:
  - Build messages with the `signature`, `key` (`from` may be enough), `from`
    and `seqno` fields.

On the consuming side:
  - `signature` may be absent, and not verified.
  - Verify `signature`, iff the `signature` is present, then reject if
    `signature` is invalid.

**`LaxNoSign` option**

_Previous default for 'no signature verification' mode_.

Do not sign nor origin-stamp, but verify incoming signatures, and accept
unsigned messages.

On the producing side:
  - Build messages without the `signature`, `key`, `from` and `seqno` fields.

On the consuming side:
  - Accept and propagate messages with above fields.
  - Verify `signature`, if the `signature` is present, then reject if
    `signature` is invalid.

> **[[ Margin note: ]]** For content-addressed messaging, `StrictNoSign` is the
> most appropriate policy option, coupled with a user-defined `message_id_fn`,
> and a validator function to verify protocol-defined signatures.
>
> When publisher anonymity is being sought, `StrictNoSign` is also the most
> appropriate policy, as it refrains from outputting the `from` and `seqno`
> fields.

## The Topic Descriptor

The topic descriptor message is used to define various options and parameters
of a topic. It currently specifies the topic's human readable name, its
authentication options, and its encryption options. The `AuthOpts` and `EncOpts`
of the topic descriptor message are not used in current implementations, but
may be used in future. For clarity, this is added as a comment in the file,
and may be removed once used.

The `TopicDescriptor` protobuf is as follows:

```protobuf
syntax = "proto2";
message TopicDescriptor {
	optional string name = 1;
	// AuthOpts and EncOpts are unused as of Oct 2018, but
	// are planned to be used in future.
	optional AuthOpts auth = 2;
	optional EncOpts enc = 3;

	message AuthOpts {
		optional AuthMode mode = 1;
		repeated bytes keys = 2;

		enum AuthMode {
			NONE = 0;
			KEY = 1;
			WOT = 2;
		}
	}

	message EncOpts {
		optional EncMode mode = 1;
		repeated bytes keyHashes = 2;

		enum EncMode {
			NONE = 0;
			SHAREDKEY = 1;
			WOT = 2;
		}
	}
}
```

The `name` field is a string used to identify or mark the topic. It can be
descriptive or random or anything that the creator chooses.

Note that instead of using `TopicDescriptor.name`, for privacy reasons the
`TopicDescriptor` struct may be hashed, and used as the topic ID. Another
option is to use a CID as a topic ID. While a consensus has not been reached,
for forwards and backwards compatibility, using an enum `TopicID` that allows
custom types in variants (i.e. `Name`, `hashedTopicDescriptor`, `CID`)
may be the most suitable option if it is available within an implementation's
language (otherwise it would be implementation defined).

The `auth` field specifies how authentication will work for this topic. Only
authenticated peers may publish to a given topic. See 'AuthOpts' below for
details.

The `enc` field specifies how messages published to this topic will be
encrypted. See 'EncOpts' below for details.

### AuthOpts

The `AuthOpts` message describes an authentication scheme. The `mode` field
specifies which scheme to use, and the `keys` field is an array of keys. The
meaning of the `keys` field is defined by the selected `AuthMode`.

There are currently three options defined for the `AuthMode` enum:

#### AuthMode 'NONE'
No authentication, anyone may publish to this topic.

#### AuthMode 'KEY'
Only peers whose peerIDs are listed in the `keys` array may publish to this
topic, messages from any other peer should be dropped.

#### AuthMode 'WOT'
Web Of Trust: any trusted peer may publish to the topic. A trusted peer is one
whose peerID is listed in the `keys` array, or any peer who is 'trusted' by
another trusted peer. The mechanism of signifying trust in another peer is yet
to be defined.


### EncOpts

The `EncOpts` message describes an encryption scheme for messages in a given
topic. The `mode` field denotes which encryption scheme will be used, and the
`keyHashes` field specifies a set of hashes of keys whose purpose may be
defined by the selected mode.

There are currently three options defined for the `EncMode` enum:

#### EncMode 'NONE'
Messages are not encrypted, anyone can read them.

#### EncMode 'SHAREDKEY'
Messages are encrypted with a preshared key. The salted hash of the key used is
denoted in the `keyHashes` field of the `EncOpts` message. The mechanism for
sharing the keys and salts is undefined.

#### EncMode 'WOT'
Web Of Trust publishing. Messages are encrypted with some certificate or
certificate chain shared amongst trusted peers. (Spec writer's note: this is the
least clearly defined option and my description here may be wildly incorrect,
needs checking).

## Topic Validation

Implementations MUST support attaching _validators_ to topics.

_Validators_ have access to the `Message` and can apply any logic to determine its validity.
When propagating a message for a topic, implementations will invoke all validators attached
to that topic, and will only continue propagation if, and only if all, validations pass.

In its simplest form, a _validator_ is a function with signature `(peer.ID, *Message) => bool`,
where the return value is `true` if validation passes, and `false` otherwise.

Local handling of failed validation is left up to the implementation (e.g. logging).

Implementations MAY allow dynamically adding and removing _validators_ at runtime.
