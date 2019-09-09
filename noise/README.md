# noise-libp2p - Secure Channel Handshake

> A libp2p transport secure channel handshake built with the Noise Protocol Framework.

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r0, 2019-08-05  |

Authors: [@yusefnapora]

Interest Group: [@raulk], [@tomaka], [@romanb], [@shahankhatch], [@Mikerah]

[@yusefnapora]: https://github.com/yusefnapora
[@raulk]: https://github.com/raulk
[@tomaka]: https://github.com/tomaka
[@romanb]: https://github.com/romanb
[@shahankhatch]: https://github.com/shahankhatch
[@Mikerah]: https://github.com/Mikerah


See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md


## Table of Contents

- [noise-libp2p - Secure Channel Handshake](#noise-libp2p---secure-channel-handshake)
    - [Table of Contents](#table-of-contents)
    - [Overview](#overview)
    - [Negotiation](#negotiation)
    - [The Noise Handshake](#the-noise-handshake)
        - [Static Key Authentication](#static-key-authentication)
        - [libp2p Data in Handshake Messages](#libp2p-data-in-handshake-messages)
            - [The libp2p Handshake Payload](#the-libp2p-handshake-payload)
        - [Supported Handshake Patterns](#supported-handshake-patterns)
            - [XX](#xx)
        - [Optimistic 0-RTT with Noise Pipes](#optimistic-0-rtt-with-noise-pipes)
            - [IK](#ik)
            - [XXfallback](#xxfallback)
            - [Noise Pipes Message Flow](#noise-pipes-message-flow)
    - [Cryptographic Primitives](#cryptographic-primitives)
    - [Valid Noise Protocol Names](#valid-noise-protocol-names)
    - [Wire Format](#wire-format)
    - [Encryption and I/O](#encryption-and-io)
    - [libp2p Interfaces and API](#libp2p-interfaces-and-api)
        - [Initialization](#initialization)
        - [Secure Transport Interface](#secure-transport-interface)
            - [NoiseConnection](#noiseconnection)
            - [SecureOutbound](#secureoutbound)
            - [SecureInbound](#secureinbound)
    - [Design Considerations](#design-considerations)
        - [No Negotiation of Noise Protocols](#no-negotiation-of-noise-protocols)
        - [Why ChaChaPoly?](#why-chachapoly)
        - [Distinct Noise and Identity Keys](#distinct-noise-and-identity-keys)
        - [Why Not Noise Signatures?](#why-not-noise-signatures)
    - [Future Work](#future-work)
        - [QUIC Support](#quic-support)
        - [Pre-shared Keys / Private Networking](#pre-shared-keys--private-networking)

## Overview

The [Noise Protocol Framework][npf] is a framework for building security
protocols by composing a small set of cryptographic primitives into patterns
with verifiable security properties.

This document specifies noise-libp2p, a libp2p channel security handshake built
using the Noise Protocol Framework. As a framework for building protocols rather
than a protocol itself, Noise presents a large decision space with many
tradeoffs. The [Design Considerations
section](#design-considerations) goes into detail about the
choices made when designing the protocol.

Secure channels in libp2p are established with the help of a transport upgrader,
a component that layers security and stream multiplexing over "raw" connections
like TCP sockets. When peers connect, the upgrader uses a protocol called
multistream-select to negotiate which security and multiplexing protocols to
use. The upgrade process is described in the [connection establishment
spec][conn-spec]. 

The transport upgrade process is likely to evolve soon, as we are in the process
of designing multiselect 2, a successor to multistream-select. Some noise-libp2p
features are designed to enable proposed features of multiselect 2, however
noise-libp2p is fully compatible with the current upgrade process and
multistream-select. See the [Negotiation section](#negotiation) for details
about protocol negotiation. 

Every Noise connection begins with a handshake between an initiating peer and a
responding peer, or in libp2p terms, a dialer and a listener. Over the course of
the handshake, peers exchange public keys and perform Diffie-Hellman exchanges
to arrive at a pair of symmetric keys that can be used to efficiently encrypt
traffic. The [Noise Handshake section](#the-noise-handshake) describes the
[supported handshake patterns](#supported-handshake-patterns) and [how
libp2p-specific data is exchanged during the
handshake](#libp2p-data-in-handshake-messages). 

By default, noise-libp2p uses the [`XX` handshake pattern](#xx), which provides
strong privacy and security guarantees and requires 1.5 round trip message
exchanges to be sound. Implementations may optionally support a compound
protocol called "Noise Pipes." Noise Pipes allows peers to attempt the more
efficient [`IK` handshake pattern](#ik) using a cached static key, falling back
to the `XX` pattern if the `IK` attempt fails. For details, see [Optimistic
0-RTT With Noise Pipes](#optimistic-0-rtt-with-noise-pipes).

During the handshake, the static DH key used for Noise is authenticated using
the libp2p identity keypair, as described in the [Static Key Authentication
section](#static-key-authentication).

Following a successful handshake, peers use the resulting encryption keys to
send ciphertexts back and forth. The format for transport messages and the wire
protocol used to exchange them is described in the [Wire Format
section](#wire-format). The cryptographic primitives used to secure the channel
are described in the [Cryptographic Primitives
section](#cryptographic-primitives).

The [libp2p Interfaces and API section](#libp2p-interfaces-and-api) goes into
detail about how noise-libp2p integrates with the libp2p framework and offers a
suggested API for implementations to adapt to their respective language idioms.

## Negotiation

libp2p has an existing protocol negotiation mechanism which is used to reach
agreement on the secure channel and multiplexing protocols used for new
connections. A description of the current protocol negotiation flow is available
in the [libp2p connections spec][conn-spec].

noise-libp2p is identified by the protocol ID string `/noise`. Peers using
multistream-select for protocol negotiation may send this protocol ID during
connection establishment to attempt to use noise-libp2p.

Future versions of this spec may define new protocol IDs using the `/noise`
prefix, for example `/noise/2`.

## The Noise Handshake

During the Noise handshake, peers perform an authenticated key exchange
according to the rules defined by a concrete Noise protocol. A concrete Noise
protocol is identified by the choice of handshake pattern and [cryptographic
primitives](#cryptographic-primitives) used to construct it.

This section covers the method of [authenticating the Noise static
key](#static-key-authentication), the [libp2p-specific
data](#libp2p-data-in-handshake-messages) that is exchanged in handshake message
payloads, and the set of [supported handshake
patterns](supported-handshake-patterns).

A brief overview of the payload security and identity hiding properties of each
handshake pattern is included in the description of each pattern, however,
readers are strongly encouraged to refer to the [Noise spec][npf] for a full
understanding.

### Static Key Authentication

The [Security Considerations section of the Noise spec][npf-security] says:

    * Authentication: A Noise protocol with static public keys verifies that the
    corresponding private keys are possessed by the participant(s), but it's up to
    the application to determine whether the remote party's static public key is
    acceptable. Methods for doing so include certificates which sign the public key
    (and which may be passed in handshake payloads), preconfigured lists of public
    keys, or "pinning" / "key-continuity" approaches where parties remember public
    keys they encounter and check whether the same party presents the same public
    key in the future.

All libp2p peers possess a cryptographic keypair which is used to [derive their
peer id][peer-id-spec], which we will refer to as their "identity keypair." To
avoid potential static key reuse, and to allow libp2p peers with any type of
identity keypair to use Noise, noise-libp2p uses a separate static keypair for
Noise that is distinct from the peer's identity keypair.

A given libp2p peer will have one or more static Noise keypairs throughout its
lifetime. Implementations MAY allow persisting static Noise keys across process
restarts, or they may generate new static Noise keys when initializing the
noise-libp2p module. 

Systems which enable the [Noise Pipes
pattern](#optimistic-0-rtt-with-noise-pipes) are likely to benefit from a longer
lifetime for static Noise keys, as the static key is used in the optimistic
case. Other systems may prefer to cycle static Noise keys frequently to reduce
exposure.

To authenticate the static Noise key used in a handshake, noise-libp2p includes
a signature of the static Noise public key in a [handshake
payload](#the-libp2p--handshake-payload). This signature is produced with the
private libp2p identity key, which proves that the sender was in possession of
the private identity key at the time the payload was generated.

### libp2p Data in Handshake Messages

In addition to authenticating the static Noise key, noise-libp2p implementations
MAY send additional "early data" in the handshake message payload. The contents
of this early data are opaque to noise-libp2p, however it is assumed that it
will be used to advertise supported stream multiplexers, thus avoiding a
round-trip negotiation after the handshake completes.

The use of early data MUST be restricted to internal libp2p APIs, and the early
data payload MUST NOT be used to transmit user or application data. Some
handshake messages containing the early data payload may be susceptible to
replay attacks, therefore the processing of early data must be idempotent. The
noise-libp2p implementation itself MUST NOT process the early data payload in
any way during the handshake, except to produce and validate the signature as
described below.

Early data provided by a remote peer should only be made available to other
libp2p components after the handshake is complete and the payload signature has
been validated. If the handshake fails for any reason, the early data payload
MUST be discarded immediately.

Any early data provided to noise-libp2p MUST be included in the [signed
handshake payload](#the-libp2p-handshake-payload) as a byte string without
alteration by the noise-libp2p implementation, and a valid signature of the
early data MUST be included as described below.

#### The libp2p Handshake Payload

libp2p-specific data, including the signature used for static key
authentication, is transmitted in Noise handshake message payloads. When
decrypted, the message payload has the structure described in [Encrypted
Payloads](#encrypted-payloads), consisting of a length-prefixed `body` field
followed by optional padding. The `body` of the payload contains a serialized
[protobuf][protobuf] message with the following schema:

``` protobuf
message NoiseHandshakePayload {
	bytes libp2p_key = 1;
	bytes noise_static_key_signature = 2;
    bytes libp2p_data = 3;
    bytes libp2p_data_signature = 4;
}
```

The `libp2p_key` field contains a serialized `PublicKey` message as defined in
the [peer id spec][peer-id-spec].

The `noise_static_key_signature` field is produced using the libp2p identity
private key according to the [signing rules in the peer id
spec][peer-id-spec-signing-rules]. The data to be signed is the UTF-8 string
`noise-libp2p-static-key:`, followed by the Noise static public key, encoded
according to the rules defined in [section 5 of RFC 7748][rfc-7748-sec-5].

The `libp2p_data` field contains the "early data" provided to the Noise module
when initiating the handshake, if any. The structure of this data is opaque to
noise-libp2p and is expected to be defined in a future iteration of the
connection establishment spec.

If `libp2p_data` is non-empty, the `libp2p_data_signature` field MUST contain a
signature produced with the libp2p identity key. The data to be signed is the
UTF-8 string `noise-libp2p-early-data:` followed by the contents of the
`libp2p_data` field.

Upon receiving the handshake payload, peers MUST decode the public key from the
`libp2p_key` field into a usable form. The key MUST be used to validate the
`noise_static_key_signature` field against the static Noise key received in the
handshake. If the signature is invalid, the connection MUST be terminated
immediately.

If the `libp2p_data` field is non-empty, the `libp2p_data_signature` MUST be
validated against the supplied `libp2p_data`. If the signature is invalid, the
connection MUST be terminated immediately.

If a noise-libp2p implementation does not expose an API for early data, they
MUST still validate the signature upon receiving a non-empty `libp2p_data`
field and abort the connection if it is invalid.

### Supported Handshake Patterns

Noise defines twelve [fundamental interactive handshake
patterns][npf-fundamental-patterns] for exchanging public keys between parties
and performing Diffie-Hellman computations. The patterns are named according to
whether static keypairs are used, and if so, by what means each party gains
knowledge of the other's static public key.

noise-libp2p supports two fundamental handshake patterns, one of which is
optional and may be enabled for efficiency.

The [XX handshake pattern](#xx) provides mutual authentication and encryption of
static keys and handshake payloads and is resistant to replay attacks. It is
the most "expensive" handshake, requiring 1.5 round trips in order to be sound,
however, the cost of sending the final handshake message may be amortized by
sending the initiator's first transport message within the same transmission
unit as the final handshake message. Implementations MUST support the XX
handshake pattern.

The [IK handshake pattern](#ik) is used in the context of [Optimistic 0-RTT with
Noise Pipes](#optimistic-0-rtt-with-noise-pipes) and is described in that
section along with the [`XXfallback`](#xxfallback) variation on the `XX`
pattern. Support for `IK` and `XXfallback` is optional, and they are only
supported in the context of the Noise Pipes pattern. Implementations that do not
support Noise Pipes should not support the `IK` handshake.

#### XX

``` 
XX:
  -> e
  <- e, ee, s, es
  -> s, se
```

In the `XX` handshake pattern, both parties send their static Noise public keys
to the other party.

The first handshake message contains the initiator's ephemeral public key, which
allows subsequent key exchanges and message payloads to be encrypted.

The second and third handshake messages include a [Noise handshake
payload](#the-libp2p-handshake-payload), which contains a signature
authenticating the sender's static Noise key as described in the [Static Key
Authentication section](#static-key-authentication) and may include other
internal libp2p data.

The XX handshake MUST be supported by noise-libp2p implementations.

A variation on the `XX` handshake, [`XXfallback`](#xxfallback) can be optionally
enabled to support [Optimistic 0-RTT with Noise
Pipes](#optimistic-0-rtt-with-noise-pipes) and is described in that context below.

### Optimistic 0-RTT with Noise Pipes

The Noise spec describes a [compound protocol][npf-compound-protocols] called
[Noise Pipes][npf-noise-pipes], which enables 0-RTT encryption in the optimistic
case, while allowing peers to fallback to a different Noise protocol if their
initial handshake attempt fails.

The Noise Pipes protocol consists of the [`XX`](#xx) and [`IK`](#ik) handshake
patterns, as well as a variation on `XX` called [`XXfallback`](#xxfallback).

The `XX` pattern is used for a **full handshake** when two peers have not
communicated using Noise before. Once the handshake completes, Alice can cache
Bob's static Noise key.

Later, Alice can open a new Noise connection to Bob using the `IK` pattern. This
is a **zero-RTT handshake** that uses the cached static key to encrypt the
initial handshake message.

If Alice attempts an `IK` handshake but Bob has changed his static Noise key,
Bob will fail to decrypt the handshake message. However, Bob may use the
ephemeral key from Alice's `IK` message to initiate a **switch handshake** with
Alice using the `XXfallback` pattern. Bob effectively treats Alice's `IK`
message _as if_ it were the first message in an `XX` handshake and proceeds
accordingly.

The handshake patterns unique to Noise Pipes, `IK` and `XXfallback`, are
described below. Noise Pipes is an optional feature of noise-libp2p, and
implementations that do support it SHOULD offer a single configuration option to
enable Noise Pipes, rather than separate options for enabling `IK` and
`XXfallback`.

Although Noise Pipes can be more efficient than the default `XX` pattern, it's
worth noting that in many real-world use cases the difference is not as large as
it would appear at a glance. While `XX` requires 1.5 round trips, the final
handshake message (sent by the initiator) can be immediately followed by a
transport message, both of which will almost certainly fit in the same network
packet or datagram. In cases where the initiator of the handshake is also the
party expected to send the first transport message (as in the common request /
reply scenario), the cost of the final handshake message is effectively
eliminated.

#### IK


``` 
IK:
      <- s
      ...
      -> e, es, s, ss
      <- e, ee, se
```

In the `IK` handshake pattern, the initiator has prior knowledge of the
responder's static Noise public key, indicated by the `<- s` token prior to the
`...` separator. This allows the initial handshake payload to be encrypted using
the known static key, and hides the identity of the initiator from passive
observers.

If the responder is unable to complete the `IK` handshake because their static
key has changed, they may initiate an [`XXfallback`](#xxfallback) handshake,
using the ephemeral public key from the failed `IK` handshake message as
pre-message knowledge.

Each handshake message will include a [libp2p handshake
payload](#the-libp2p-handshake-payload) that identifies the sender and
authenticates the static Noise key.

#### XXfallback

``` 
XXfallback:
  -> e
  ...
  <- e, ee, s, es
  -> s, se
```

The `XXfallback` handshake pattern is used when a peer fails to decrypt an
incoming `IK` handshake message that was prepared using a static Noise public
key that is no longer valid.

The *responder* for a failed `IK` handshake becomes the *initiator* of the
subsequent `XXfallback` handshake. For example, if Alice initiated an `IK`
handshake that Bob was unable to decrypt, Bob will initiate the `XXfallback`
handshake to Alice. This is reflected in the arrow direction above; fallback
handshake patterns are notated in the [so-called][npf-alice-and-bob]
"Bob-initiated form," with arrows reversed from the canonical (Alice-initiated)
form.

The handshake pattern is the same as in `XX`, however, Alice's ephemeral public
key is obtained from her initial `IK` message, moving it to the pre-message
section of the handshake pattern. Essentially, the failed `IK` message serves
the same role as the first handshake message in the standard `XX` pattern.

Each handshake message will include a [libp2p handshake
payload](#the-libp2p-handshake-payload) that identifies the sender and
authenticates the static Noise key.

#### Noise Pipes Message Flow

Noise Pipes is a compound protocol, and peers supporting Noise pipes need to be
able to distinguish between handshake messages from each pattern. We also wish
to impose no additional overhead on peers that do not support Noise Pipes.

There are four cases to support:

- Neither party supports Noise Pipes.
- Alice and Bob both support Noise Pipes.
- Bob supports Noise Pipes but Alice does not.
- Alice supports Noise Pipes but Bob does not.

If **neither party supports Noise Pipes**, they both use the `XX` handshake and
life is easy.

If **Alice and Bob both support Noise Pipes**, Alice's initial handshake message
to Bob may be either an `XX` or `IK` message. Bob, supporting Noise Pipes, will
attempt to handle _all_ initial handshake messages as `IK` messages.

If Alice sends an `IK` message to Bob to initiate a **zero-RTT handshake** and
Bob has not changed his static Noise key, Bob will successfully decrypt the
initial message and will respond with the next message in the `IK` sequence.

If Alice sends an `XX` message to initiate a **full handshake**, or if Bob's
static key has changed, Bob will fail to decrypt the initial message as an `IK`
message. Bob will then re-initialize his Noise handshake state using the
`XXfallback` pattern, using the ephemeral key from the initial message as
pre-message knowledge. This is semantically equivalent to re-initializing with
the `XX` pattern and re-processing Alice's message as the first in the `XX`
sequence.

If Alice sends an `XX` message, she will always receive an `XX`-compatible
response. However, if Alice sends an `IK` message, Bob may reply with either the
second `IK` message, or the first message in the `XXfallback` sequence (aka the
second message in `XX`). 

Alice will always attempt to process Bob's response to an `IK` handshake attempt
as an `IK` response. If this succeeds, the handshake is complete. If Alice fails
to decrypt Bob's response as an `IK` message, she will re-initialize her Noise
handshake state using the `XXfallback` pattern and re-process Bob's reply. She
will then respond with the final message in the `XXfallback` pattern, which also
corresponds to the final message in `XX`.

If **Bob supports Noise Pipes but Alice does not**, Alice's initial handshake
message will always be an `XX` message. Bob will first attempt to decrypt the
initial message as an `IK` message, which will fail. He will then re-initialize
his Noise state and respond with the first message in `XXfallback`, which is
equivalent to the second `XX` message that Alice was expecting. Alice will
complete the handshake by sending the final message in the `XX` sequence.

If **Alice supports Noise Pipes but Bob does not**, Alice may send an initial
`IK` message to Bob. Bob, not knowing anything about Noise Pipes, will treat
this as the initial message in the `XX` sequence. This will succeed, because the
only required information from the initial `XX` message is the ephemeral public
key, which is also present in the `IK` message. Bob's response will be the
second message in the `XX` sequence. Alice will first try to decrypt this as an
`IK` response, which will fail. She then re-initializes her Noise state to use
`XXfallback` as in the case where Bob also supports Noise Pipes but cannot
complete an `IK` handshake. She then completes the handshake by sending the
third message in the `XX` sequence that Bob was expecting.

## Cryptographic Primitives

The Noise framework allows protocol designers to choose from a small set of
Diffie-Hellman key exchange functions, symmetric ciphers, and hash functions.

For simplicity, and to avoid the need to explicitly negotiate Noise protocols,
noise-libp2p defines a single "cipher suite".

noise-libp2p implementations MUST support the [25519 DH
functions][npf-dh-25519], [ChaChaPoly cipher functions][npf-cipher-chachapoly],
and [SHA256 hash function][npf-hash-sha256] as defined in the Noise spec.

## Valid Noise Protocol Names

This section lists the [Noise protocol names][npf-protocol-names] that are valid
according to the definitions in this spec. While these names are useful
internally when working with Noise, they are never sent "on the wire" or used
for any kind of handshake negotiation and are provided for reference.

Because only a single set of cryptographic primitives is supported, the Noise
protocol name depends on the handshake pattern in use.

The `Noise_XX_25519_ChaChaPoly_SHA256` protocol MUST be supported by all
implementations.

Implementations that support Noise Pipes will also support the following Noise protocols:

- `Noise_IK_25519_ChaChaPoly_SHA256`
- `Noise_XXfallback_25519_ChaChaPoly_SHA256`


## Wire Format

noise-libp2p defines a simple message framing format for sending data back and
forth over the underlying transport connection.

All data is segmented into messages with the following structure:

| `noise_message_len` | `noise_message` |
|---------------------|-----------------|
| 2 bytes             | variable length |

The `noise_message_len` field stores the length in bytes of the `noise_message`
field, encoded as a 16-bit big-endian unsigned integer.

The `noise_message` field contains a [Noise Message as defined in the Noise
spec][npf-message-format], which has a maximum length of 65535 bytes. 

During the handshake phase, `noise_message` will be a Noise handshake message.
Noise handshake messages may contain encrypted payloads. If so, the decrypted
handshake payload will have the format described in [The libp2p Hanshake
Payload](#the-libp2p-handshake-payload).

After the handshake completes, `noise_message` will be a Noise transport
message, which is defined as an AEAD ciphertext consisting of an encrypted
payload plus 16 bytes of authentication data. The decrypted plaintext of the
encrypted payload will contain up to 65535 bytes of "application layer" data.
It is the responsibilty of the noise-libp2p implementation to segment
application data into chunks that will fit into a Noise transport message when
sending, and to buffer and recombine chunks when receiving.


## Encryption and I/O

During the handshake phase, the initiator (Alice) will initialize a Noise
[`HandshakeState` object][npf-handshake-state] with their preferred [concrete
Noise protocol](#valid-noise-protocol-names). 

If Alice does not support [Noise Pipes](#optimistic-0-rtt-with-noise-pipes),
this will be `Noise_XX_25519_ChaChaPoly_SHA256`. With Noise pipes, the initial
protocol may use the `IK` handshake pattern instead of `XX`.

Alice and Bob exchange handshake messages, during which they [authenticate each
other's static Noise keys](#static-key-authentication). Handshake messages are
framed as described in the [Wire Format section](#wire-format), and if a
handshake message contains a payload, it will have the structure described in
[Encrypted Payloads](#encrypted-payloads).

Following a successful handshake, each peer will possess two Noise
[`CipherState` objects][npf-cipher-state]. One is used to encrypt outgoing
data to the remote party, and the other is used to decrypt incoming data.

After the handshake, peers continue to exchange messages in the format described
in the [Wire Format section](#wire-format). However, instead of containing a
Noise handshake message, the contents of the `noise_message` field will be Noise
transport message, which is an AEAD ciphertext consisting of an encrypted
payload plus 16 bytes of authentication data, as [defined in the Noise
spec][npf-message-format].

When decrypted, the payload of a Noise transport message will contain up to
65535 bytes of plaintext "application layer" data. This should be buffered by
the reciever and exposed as a continuous readable stream of binary data.
Likewise, when sending data, the noise-libp2p module should expose a writable
streaming interface. The segmentation of data into Noise transport messages
should be "invisible" outside of the noise-libp2p module.

In the unlikely event that peers exchange more than `2^64 - 1` messages, they
MUST terminate the connection to avoid reusing nonces, in accordance with the
[Noise spec][npf-security].

## libp2p Interfaces and API

This section describes an abstract API for noise-libp2p. Implementations may
alter this API to conform to language idioms or patterns used by the targeted
libp2p implementation. Examples are written in pseudo-code that vaguely
resembles Swift.

### Initialization

The noise-libp2p module accepts the following inputs at initialization.

- The private libp2p identity key
- [optional] An early data payload to be sent in handshake messages
- [optional] The private Noise static key
- [optional] If Noise Pipes is supported, a flag to enable at runtime

The private libp2p identity key is required for [static key
authentication](#static-key-authentication) and signing of early data (if
provided).

Implementations that support sending [early data in handshake
messages](#libp2p-data-in-handshake-messages) should accept this data at
initialization time, rather than accepting an early data payload for each new
connection. This ensures that no user or connection-specific data can be present
in the early data payload.

If a noise-libp2p implementation supports persisting the static Noise key, the
constructor for the noise-libp2p module must accept a stored key.

If a noise-libp2p implementation supports [Noise
Pipes](#optimistic-0-rtt-with-noise-pipes), they may expose a configuration flag
to selectively enable Noise Pipes at runtime.

A minimal constructor could look like:

``` 
init(libp2pKey: PrivateKey) -> NoiseLibp2p
```

While one supporting all options might look like:

```
init(libp2pKey: PrivateKey, noiseKey: ByteString, earlyData: ByteString,
useNoisePipes: bool) -> NoiseLibp2p
```

### Secure Transport Interface

noise-libp2p is designed to work with libp2p's **transport upgrade** pattern.
libp2p security modules conform to a secure transport interface, which provides
the `SecureOutbound` and `SecureInbound` methods described below.

`SecureOutbound` and `SecureInbound` each accept an `InsecureConnection` and
return a `NoiseConnection` on success. 

The details of the `InsecureConnection` type are libp2p-implementation
dependent, but it is assumed to expose a bidirectional, reliable streaming
interface.

#### NoiseConnection

A `NoiseConnection` must conform to the libp2p secure transport interface in the
noise-libp2p implementation language by defining `SecureOutbound` and
`SecureInbound` connections, described below.

In addition to the secure transport interface defined by the libp2p framework, a
`NoiseConnection` MAY have an additional method to expose early data transmitted
by the remote peer during the handshake phase, if any. For example:

```
remoteEarlyData() -> ByteString?
```

Following a successful handshake, a `NoiseConnection` will transmit and receive
data over the `InsecureConnection` as described in [Encryption and
I/O](#encryption-and-io).

#### SecureOutbound

```
SecureOutbound(insecure: InsecureConnection, remotePeer: PeerId) -> Result<NoiseConnection, Error>
```

`SecureOutbound` initiates a noise-libp2p connection to `remotePeer` over the
provided `InsecureConnection`.

The `remotePeer` PeerId argument MUST be validated against the libp2p public
identity sent by the remote peer during the handshake. If a remote peer sends a
public key that is not capable of deriving their expected peer id, the
connection MUST be aborted.

Note that the interface does not allow the user to choose the Noise handshake
pattern. Implementations that support Noise Pipes must decide whether to use an
`XX` or `IK` handshake based on whether they possess a cached static Noise key
for the remote peer.

#### SecureInbound

```
SecureInbound(insecure: InsecureConnection) -> Result<NoiseConnection, Error>
```

`SecureInbound` attempts to complete a noise-libp2p handshake initiated by a
remote peer over the given `InsecureConnection`.

## Design Considerations

### No Negotiation of Noise Protocols

Supporting a single cipher suite allows us to avoid negotiating which concrete
Noise protocol to use for a given connection. This removes a huge source of
incidental complexity and makes implementations much simpler. Changes to the
cipher suite will require a new version of noise-libp2p, but this should happen
infrequently enough to be a non-issue.

Users who require cipher agility are encouraged to adopt TLS 1.3, which supports
negotiation of cipher suites.

### Why ChaChaPoly?

We debated supporting AESGCM in addition to or instead of ChaChaPoly. The desire
for a simple protocol without explicit negotiation of ciphers and handshake
patterns led us to support a single cipher, so the question became which to
support.

While AES has broad hardware support that can lead to significant performance
improvements on some platforms, secure and performant software
implementations are hard to come by. To avoid excluding runtime platforms
without hardware AES support, we chose the ChaChaPoly cipher, which is possible
to implement in software on all platforms.

### Distinct Noise and Identity Keys

Using a separate keypair for Noise adds complexity to the protocol by requiring
signature validation and transmission of libp2p public keys during the
handshake.

However, none of the key types supported by libp2p for use as identity keys are
fully compatible with Noise. While it is possible to convert an ed25519 key into
the X25519 format used with Noise, it is not possible to do the reverse. This
makes it difficult to use any libp2p identity key directly as the Noise static
key.

Also, Noise [recommends][npf-security] only using Noise static keys with other
Noise protocols using the same hash function. Since we can't guarantee that
users won't also use their libp2p identity keys in other contexts (e.g. SECIO
handshakes, signing pubsub messages, etc), requiring separate keys seems
prudent.

### Why Not Noise Signatures?

Since we're using signatures for authentication, the [Noise Signatures
extension][noise-signatures-spec] is a natural candidate for adoption.

Unfortunately, the Noise Signatures spec requires both parties to use the same
signature algorithm, which would prevent peers with different identity key types
to complete a Noise Signatures handshake. Also, only Ed25519 signatures are
currently supported by the spec, while libp2p identity keys may be of other
unsupported types like RSA.

## Future Work

This section will outline some things we'd like to accomplish in the future but
were ommitted from this draft because the path forward isn't yet clear.

### QUIC Support

go-libp2p has recently added support for [QUIC][ietf-quic-spec], a UDP-based
protocol with many excellent properties, including native support for
multiplexing and encryption. The current QUIC draft spec uses TLS 1.3 to secure
connections. However, it is possible to extend QUIC to use Noise, as
demonstrated by [nQUIC][nquic-paper], an experimental variant of the QUIC spec.

We would like to explore the possiblity of integrating the Noise handshake into
libp2p's QUIC transport. This would likely build upon the nQUIC work, and may
involve extending nQUIC to support more than the `IK` handshake specified in the
nQUIC paper.

### Pre-shared Keys / Private Networking

Noise supports a "psk" variant of all the fundamental handshake patterns, which
uses an additional pre-shared key to secure traffic. This could potentially
provide an alternative to the current [private networking][libp2p-psk-spec]
functionality in libp2p, in which a pre-shared key is used to encrypt all data
within a given libp2p network.

The current libp2p private network feature operates independently of the secure
handshake protocol, encrypting all traffic even before the secure channel
protocol has been negotiated. As a result, using Noise to implement private
networks may require changes to internal libp2p APIs, the scope of which aren't
yet clear.

[peer-id-spec]: ../peer-ids/peer-ids.md
[peer-id-spec-signing-rules]: ../peer-ids/peer-ids.md#how-keys-are-encoded-and-messages-signed

[conn-spec]: ../connections/README.md
[multiselect-2-pr]: https://github.com/libp2p/specs/pull/95

[npf]: https://noiseprotocol.org/noise.html
[npf-prologue]: https://noiseprotocol.org/noise.html#prologue

[npf-handshake-basics]: https://noiseprotocol.org/noise.html#handshake-pattern-basics
[npf-fundamental-patterns]: https://noiseprotocol.org/noise.html#interactive-handshake-patterns-fundamental
[npf-compound-protocols]: https://noiseprotocol.org/noise.html#compound-protocols
[npf-noise-pipes]: https://noiseprotocol.org/noise.html#noise-pipes
[npf-protocol-names]: https://noiseprotocol.org/noise.html#protocol-names-and-modifiers
[npf-dh-25519]: https://noiseprotocol.org/noise.html#the-25519-dh-functions
[npf-cipher-chachapoly]: https://noiseprotocol.org/noise.html#the-chachapoly-cipher-functions
[npf-hash-sha256]: https://noiseprotocol.org/noise.html#the-sha256-hash-function
[npf-security]: https://noiseprotocol.org/noise.html#security-considerations
[npf-message-format]: https://noiseprotocol.org/noise.html#message-format
[npf-alice-and-bob]: https://noiseprotocol.org/noise.html#alice-and-bob
[npf-handshake-indistinguishability]: https://noiseprotocol.org/noise.html#handshake-indistinguishability
[npf-handshake-state]: https://noiseprotocol.org/noise.html#the-handshakestate-object
[npf-cipher-state]: https://noiseprotocol.org/noise.html#the-cipherstate-object


[rfc-7748-sec-5]: https://tools.ietf.org/html/rfc7748#section-5
[protobuf]: https://developers.google.com/protocol-buffers/
[noise-socket-spec]: https://github.com/noisesocket/spec
[noise-signatures-spec]: https://github.com/noiseprotocol/noise_sig_spec/blob/master/output/noise_sig.pdf
[ietf-quic-spec]: https://datatracker.ietf.org/doc/draft-ietf-quic-transport/
