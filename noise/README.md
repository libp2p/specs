# noise-libp2p - Secure Channel Handshake

> A libp2p transport secure channel handshake built with the Noise Protocol
> Framework.

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 3A              | Working Draft | Active | r2, 2020-03-30  |

Authors: [@yusefnapora]

Interest Group: [@raulk], [@tomaka], [@romanb], [@shahankhatch], [@Mikerah],
[@djrtwo], [@dryajov], [@mpetrunic], [@AgeManning], [@morrigan], [@araskachoi],
[@mhchia]

[@yusefnapora]: https://github.com/yusefnapora
[@raulk]: https://github.com/raulk
[@tomaka]: https://github.com/tomaka
[@romanb]: https://github.com/romanb
[@shahankhatch]: https://github.com/shahankhatch
[@Mikerah]: https://github.com/Mikerah
[@djrtwo]: https://github.com/djrtwo
[@dryajov]: https://github.com/dryajov
[@mpetrunic]: https://github.com/mpetrunic
[@AgeManning]: https://github.com/AgeManning
[@morrigan]: https://github.com/morrigan
[@araskachoi]: https://github.com/araskachoi
[@mhchia]: https://github.com/mhchia


See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md


## Table of Contents

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->


- [Overview](#overview)
- [Negotiation](#negotiation)
- [The Noise Handshake](#the-noise-handshake)
  - [Static Key Authentication](#static-key-authentication)
  - [libp2p Data in Handshake Messages](#libp2p-data-in-handshake-messages)
    - [The libp2p Handshake Payload](#the-libp2p-handshake-payload)
  - [Handshake Pattern](#handshake-pattern)
    - [XX](#xx)
- [Cryptographic Primitives](#cryptographic-primitives)
- [Noise Protocol Name](#noise-protocol-name)
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
  - [Why the XX handshake pattern?](#why-the-xx-handshake-pattern)
  - [Why ChaChaPoly?](#why-chachapoly)
  - [Distinct Noise and Identity Keys](#distinct-noise-and-identity-keys)
  - [Why Not Noise Signatures?](#why-not-noise-signatures)
- [Changelog](#changelog)
  - [r1 - 2020-01-20](#r1---2020-01-20)
  - [r2 - 2020-03-30](#r2---2020-03-30)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Overview

The [Noise Protocol Framework][npf] is a framework for building security
protocols by composing a small set of cryptographic primitives into patterns
with verifiable security properties.

This document specifies noise-libp2p, a libp2p channel security handshake built
using the Noise Protocol Framework. As a framework for building protocols rather
than a protocol itself, Noise presents a large decision space with many
tradeoffs. The [Design Considerations section](#design-considerations) goes into
detail about the choices made when designing the protocol.

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
[handshake pattern](#handshake-pattern) and [how libp2p-specific data is
exchanged during the handshake](#libp2p-data-in-handshake-messages).

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
payloads, and the [supported handshake pattern](#handshake-pattern).

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
lifetime. Because the static key is authenticated using the libp2p identity key,
it is not necessary for the key to actually be "static" in the traditional
sense, and implementations MAY generate a new static Noise keypair for each new
session. Alternatively, a single static keypair may be generated when
noise-libp2p is initialized and used for all sessions. Implementations SHOULD
NOT store the static Noise key to disk, as there is no benefit and a hightened
risk of exposure.

To authenticate the static Noise key used in a handshake, noise-libp2p includes
a signature of the static Noise public key in a [handshake
payload](#the-libp2p-handshake-payload). This signature is produced with
the private libp2p identity key, which proves that the sender was in possession
of the private identity key at the time the payload was generated.

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

Any early data provided to noise-libp2p MUST be included in the [handshake
payload](#the-libp2p-handshake-payload) as a byte string without alteration by
the noise-libp2p implementation.

#### The libp2p Handshake Payload

The Noise Protocol Framework caters for sending early data alongside handshake
messages. We leverage this construct to transmit:

1. the libp2p identity key along with a signature, to authenticate each party to
   the other.
2. arbitrary data private to the libp2p stack. This facility is not exposed to
   userland. Examples of usage include streamlining muxer selection.

These payloads MUST be inserted into the first message of the handshake pattern
**that guarantees secrecy**. In practice, this means that the initiator must not
send a payload in their first message. Instead, the initiator will send its
payload in message 3 (closing message), whereas the responder will send theirs
in message 2 (their only message).

When decrypted, the payload contains a serialized [protobuf][protobuf]
`NoiseHandshakePayload` message with the following schema:

``` protobuf
message NoiseHandshakePayload {
  bytes identity_key = 1;
  bytes identity_sig = 2;
  bytes data         = 3;
}
```

The `identity_key` field contains a serialized `PublicKey` message as defined
in the [peer id spec][peer-id-spec].

The `identity_sig` field is produced using the libp2p identity private key
according to the [signing rules in the peer id
spec][peer-id-spec-signing-rules]. The data to be signed is the UTF-8 string
`noise-libp2p-static-key:`, followed by the Noise static public key, encoded
according to the rules defined in [section 5 of RFC 7748][rfc-7748-sec-5].

The `data` field contains the "early data" provided to the Noise module when
initiating the handshake, if any. The structure of this data is opaque to
noise-libp2p and is defined in the connection establishment specs.

Upon receiving the handshake payload, peers MUST decode the public key from the
`identity_key` field into a usable form. The key MUST then be used to validate
the `identity_sig` field against the static Noise key received in the handshake.
If the signature is invalid, the connection MUST be terminated immediately.

### Handshake Pattern

Noise defines twelve [fundamental interactive handshake
patterns][npf-fundamental-patterns] for exchanging public keys between parties
and performing Diffie-Hellman computations. The patterns are named according to
whether static keypairs are used, and if so, by what means each party gains
knowledge of the other's static public key.

`noise-libp2p` supports the [XX handshake pattern](#xx), which provides mutual
authentication and encryption of static keys and handshake payloads and is
resistant to replay attacks. 

Prior revisions of this spec included a compound protocol involving the `IK` and
`XXfallback `patterns, but this was [removed](#why-the-xx-handshake-pattern) due
to the benefits not justifying the considerable additional complexity.

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

The second and third handshake messages include a [handshake
payload](#the-libp2p-handshake-payload), which contains a signature
authenticating the sender's static Noise key as described in the [Static Key
Authentication section](#static-key-authentication) and may include other
internal libp2p data.

The XX handshake MUST be supported by noise-libp2p implementations.

## Cryptographic Primitives

The Noise framework allows protocol designers to choose from a small set of
Diffie-Hellman key exchange functions, symmetric ciphers, and hash functions.

For simplicity, and to avoid the need to explicitly negotiate Noise protocols,
noise-libp2p defines a single "cipher suite".

noise-libp2p implementations MUST support the [25519 DH
functions][npf-dh-25519], [ChaChaPoly cipher functions][npf-cipher-chachapoly],
and [SHA256 hash function][npf-hash-sha256] as defined in the Noise spec.

## Noise Protocol Name

A Noise `HandshakeState` is initialized with the hash of a [Noise protocol
name][npf-protocol-names], which defines the handshake pattern and cipher suite
used. Because `noise-libp2p` supports a single cipher suite and handshake
pattern, the Noise protocol name MUST be: `Noise_XX_25519_ChaChaPoly_SHA256`.

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
Noise handshake messages may contain encrypted payloads. If so, they will have
the structure described in the [Encrypted Payloads
section](#encrypted-payloads).

After the handshake completes, `noise_message` will be a Noise transport
message, which is defined as an AEAD ciphertext consisting of an encrypted
payload plus 16 bytes of authentication data.

## Encryption and I/O

During the handshake phase, the initiator (Alice) will initialize a Noise
[`HandshakeState` object][npf-handshake-state] with the [Noise protocol
name](#noise-protocol-name) `Noise_XX_25519_ChaChaPoly_SHA256`. 

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

The private libp2p identity key is required for [static key
authentication](#static-key-authentication) and signing of early data (if
provided).

Implementations that support sending [early data in handshake
messages](#libp2p-data-in-handshake-messages) should accept this data at
initialization time, rather than accepting an early data payload for each new
connection. This ensures that no user or connection-specific data can be present
in the early data payload.

A minimal constructor could look like:

``` 
init(libp2pKey: PrivateKey) -> NoiseLibp2p
```

While one supporting all options might look like:

```
init(libp2pKey: PrivateKey, earlyData: ByteStringl) -> NoiseLibp2p
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

### Why the XX handshake pattern?

An earlier draft of this spec included a compound protocol called [Noise
Pipes][npf-noise-pipes] that uses the `IK` and `XXfallback` handshake patterns
to enable a slightly more efficient handshake when the remote peer's static
Noise key is known _a priori_. During development of the Go and JavaScript
implementations, this was determined to add too much complexity to be worth the
benfit, and the benefit turned out to be less than originally hoped. See [the
discussion on github][issue-rm-noise-pipes] for more context.


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

## Changelog

### r1 - 2020-01-20

- Renamed protobuf fields
- Edited for clarity

### r2 - 2020-03-30

- Removed Noise Pipes and related handshake patterns
- Removed padding within encrypted payloads


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
[npf-channel-binding]: https://noiseprotocol.org/noise.html#channel-binding

[rfc-7748-sec-5]: https://tools.ietf.org/html/rfc7748#section-5
[protobuf]: https://developers.google.com/protocol-buffers/
[noise-socket-spec]: https://github.com/noisesocket/spec
[noise-signatures-spec]: https://github.com/noiseprotocol/noise_sig_spec/blob/master/output/noise_sig.pdf
[issue-rm-noise-pipes]: https://github.com/libp2p/specs/issues/249
