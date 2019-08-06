# noise-libp2p - Channel Security Protocol

> A libp2p transport security protocol built with the Noise Protocol Framework.

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r0, 2019-08-05  |

Authors: [@yusefnapora]

Interest Group: [@raulk], [@tomaka], [@romanb]

[@yusefnapora]: https://github.com/yusefnapora
[@raulk]: https://github.com/raulk
[@tomaka]: https://github.com/tomaka
[@romanb]: https://github.com/romanb

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Overview

The [Noise Protocol Framework][npf] is a framework for building security
protocols by composing a small set of cryptographic primitives into patterns
with verifiable security properties.

This document specifies noise-libp2p, a libp2p transport security protocol built
using the Noise Protocol Framework. As a framework for building protocols rather
than a protocol itself, Noise presents a large decision space with many
tradeoffs. The [Design Considerations
section](#design-considerations-and-tradeoffs) covers the rationale behind the
presented design.

libp2p peers have an "identity keypair" which is used to derive their peer id,
as described in the [peer id spec][peer-id-spec]. noise-libp2p uses the identity
keypair to authenticate a separate static key which is used only for
noise-libp2p. This is described in the [Static Key Authentication
section](#static-key-authentication).

## Message Framing

noise-libp2p sends all data over the wire in the form of Noise messages, which
are [defined][npf-message-format] with a maximum length of 65535 bytes.

Noise messages are sent prefixed with their length in bytes, encoded as an
unsigned 16-bit integer in network (big-endian) byte order.

## Supported DH Functions, Ciphers, and Hash Functions

The Noise framework allows protocol designers to choose from a small set of
Diffie-Hellman functions, symmetric ciphers, and hash functions.

For simplicity, noise-libp2p currently supports one function from each category:

### Supported DH Functions

noise-libp2p supports the 25519 DH functions [as defined in the Noise
spec][npf-dh-25519].

### Supported Cipher Functions

noise-libp2p supports the ChaChaPoly cipher functions [as defined in the Noise
spec][npf-cipher-chachapoly].

### Supported Hash Functions

noise-libp2p supports the SHA256 hash function [as defined in
the Noise spec][npf-hash-sha256].

## Supported Handshake Patterns

Noise defines twelve [fundamental interactive handshake
patterns][npf-fundamental-patterns] for exchanging public keys between parties and performing
Diffie-Hellman computations.

The patterns are named according to whether static keypairs are used, and if so,
by what means each party gains knowledge of the other's static public key.

From the [fundamental patterns section of the Noise spec][npf-fundamental-patterns]:

    The first character refers to the initiator's static key:

       * N = No static key for initiator
       * K = Static key for initiator Known to responder
       * X = Static key for initiator Xmitted ("transmitted") to responder
       * I = Static key for initiator Immediately transmitted to responder, despite reduced or absent identity hiding

    The second character refers to the responder's static key:

      * N = No static key for responder
      * K = Static key for responder Known to initiator
      * X = Static key for responder Xmitted ("transmitted") to initiator

noise-libp2p supports a [compound protocol][npf-compound-protocols] consisting
of two fundamental handshake patterns, `XX` and `IK`. A variation of the `XX`
pattern, `XXfallback` is used to gracefully recover from a failed `IK`
handshake attempt.

This pattern of using `XX`, `IK` and `XXfallback` is described in the Noise spec
as the [Noise Pipes compound protocol][npf-noise-pipes].

The`XX` pattern is used when the initiator (or in libp2p terms, the dialing peer)
does not have knowledge of the static Noise key for the responder (the listening
peer). As Noise static keys are distinct from libp2p identity keys, this is
likely to be the case for the first Noise connection between two peers.

Following a successful `XX` handshake, both peers may store the static Noise
public key of the other. Future connections can attempt the `IK` handshake using
the stored static key, which offers the benefits of zero-RTT encryption and
fewer message round-trips.

In the event that a responder has changed their static Noise keypair, they will
fail to decrypt inbound `IK` handshake attempts that were encrypted with an
older static public key. In that case, the responder will attempt to fallback to
an `XX` handshake, this time acting in the initiator role. Because the initial
(failed) `IK` message contains an ephemeral public key, the `XXfallback` variant
is used, in which the ephemeral key is specified as pre-message data.

Below is a brief description of each handshake pattern. The compact notation
used for message tokens is defined in the [Handshake Pattern
Basics][npf-handshake-basics] section of the Noise spec.

### XX

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

The second and third handshake messages include a [noise-libp2p handshake
payload](#the-noise-libp2p-handshake-payload), which contains a signature
authenticating the sender's static Noise key as described in the [Static Key
Authentication section](#static-key-authentication).

### IK

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
the known static key.

If the responder is unable to complete the `IK` handshake because their static
key has changed, they may initiate an `XXfallback` handshake, using the
ephemeral public key from the failed `IK` handshake message as pre-message
knowledge.

The `IK` handshake pattern consists of two handshake messages, both of which
include a [noise-libp2p handshake payload](#the-noise-libp2p-handshake-payload),
which contains a signature authenticating the sender's static Noise key as
described in the [Static Key Authentication
section](#static-key-authentication).

### XXfallback

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

Both messages (not counting the initial failed `IK` message) include a
[noise-libp2p handshake payload](#the-noise-libp2p-handshake-payload), which contains
a signature authenticating the sender's static Noise key as described in the
[Static Key Authentication section](#static-key-authentication).

## Handshake Negotiation

Peers agree upon which Noise handshake to use by leveraging libp2p's existing
protocol negotiation system. At the time of writing, protocol negotiation uses
multistream-select 1.0, as described in the [connection establishment
spec][conn-spec], although [work is in progress][multiselect-2-pr] on defining
a new version.

### Protocol IDs

A concrete Noise protocol is identified by the combination of handshake pattern,
DH function, cipher, and hash function used. These elements combine to form a
[Noise protocol name][npf-protocol-names]. 

For example, the IK handshake using [the 25519 DH functions][npf-dh-25519],
[ChaChaPoly cipher][npf-cipher-chachapoly] and [SHA-256 hash
function][npf-hash-sha256] would have the Noise protocol name
`Noise_IK_25519_ChaChaPoly_SHA256`.

noise-libp2p protocol IDs have a similar format to Noise protocol names, adapted
to libp2p naming conventions. A valid noise-libp2p protocol ID consists of the
following elements, separated by `/` characters:

- the string `/noise`
- the name of the handshake pattern, lowercased
- the name of the DH function, lowercased
- the name of the cipher, lowercased
- the name of the hash function, lowercased
- the version of the noise-libp2p spec that defines the protocol

If any of the names used to construct the protocol ID contains a `/` character
(for example, `SHA3/256`), the `/` will be replaced with a `-` to avoid
ambiguity with the separator character. In practice, none of the currently
supported functions contain a `/` in their names, so this is likely to remain a
non-issue.

Using the [supported handshake patterns](#supported-handshake-patterns) and
[supported DH function, cipher and
hash](#supported-dh-functions-ciphers-and-hash-functions), the following are
valid noise-libp2p protocol IDs:

- `/noise/xx/25519/chachapoly/sha256/1.0.0`
- `/noise/xxfallback/25519/chachapoly/sha256/1.0.0`
- `/noise/ik/25519/chachapoly/sha256/1.0.0`

The final component of the protocol ID refers to the version of the noise-libp2p
spec used to implement the protocol and must be `1.0.0`. Future revisions of
this specification may define new version numbers.

## Static Key Authentication

The [Security Considerations section of the Noise spec][npf-security] says:

    * Authentication: A Noise protocol with static public keys verifies that the
    corresponding private keys are possessed by the participant(s), but it's up to
    the application to determine whether the remote party's static public key is
    acceptable. Methods for doing so include certificates which sign the public key
    (and which may be passed in handshake payloads), preconfigured lists of public
    keys, or "pinning" / "key-continuity" approaches where parties remember public
    keys they encounter and check whether the same party presents the same public
    key in the future.
    
And also:

    * Static key reuse: A static key pair used with Noise should be used with a single
    hash algorithm. The key pair should not be used outside of Noise, nor with
    multiple hash algorithms. It is acceptable to use the static key pair with
    different Noise protocols, provided the same hash algorithm is used in all of
    them. (Reusing a Noise static key pair outside of Noise would require extremely
    careful analysis to ensure the uses don't compromise each other, and security
    proofs are preserved).

All libp2p peers possess a cryptographic keypair which is used to [derive their
peer id][peer-id-spec], which we will refer to as their "identity keypair." To
avoid potential static key reuse, and to allow libp2p peers with any type of
identity keypair to use Noise, noise-libp2p uses a separate static keypair for
Noise that is distinct from the peer's identity keypair.

To authenticate the static Noise key, peers include a [noise-libp2p handshake
payload](#the-noise-libp2p-handshake-payload) with their encrypted handshake
messages. The payload includes the peer's public libp2p identity key, and a
signature over the static Noise public key, produced with the identity key. This
simple certificate proves that the possessor of the Noise static keypair is also
in possession of the private libp2p identity key.

The lifetime of the Noise static keypair is not specified. Implementations MAY
allow noise-libp2p to be initialized with a stored static key to extend the key
lifetime beyond a single invocation of a given application, in which case it is
the application's responsibility to store the key. If no static key is provided
at initialization, noise-libp2p will generate a new X25519 keypair and use it
for the lifetime of the process.

### The noise-libp2p Handshake Payload

As mentioned, noise-libp2p uses a static keypair that is distinct from the
"identity keypair" used to derive a peer's peer id. As a result, we must
authenticate Noise static keys in a way that proves they belong to the correct
libp2p peer. To do so, noise-libp2p includes a simple "certificate" in the
payload of Noise handshake messages.

The noise-libp2p handshake payload is a [protobuf][protobuf] message with the
following schema:

``` protobuf
message Identity {
	bytes pubkey = 1;
	bytes signature = 2;
}

```

The `pubkey` field contains the public libp2p identity key, encoded as described
in the [peer id spec][peer-id-spec].

The `signature` field contains a signature of the Noise static public key,
produced by the private libp2p identity key. The Noise static key is encoded
into a byte array according to the rules defined in [section 5 of RFC
7748][rfc-7748-sec-5] and signed as described in the [peer id
spec][peer-id-spec].

Each peer MUST send the noise-libp2p handshake payload in the first encrypted
Noise handshake message that they send. Encrypting the handshake payload is
required to avoid replay attacks, as there is no timestamp or other validity
criteria in the payload itself apart from the signature.

Noise handshake payloads are encrypted if they occur after at least one DH
exchange. For the `XX` handshake, the first handshake message is sent in
plaintext with no payload, and encrypted payloads are sent with the following
two messages.

Below are the supported handshake patterns annotated with the payload that is
sent during each message (if any).

Because the initiator and responder roles may change during the `IK` /
`XXfallback` pattern, [Alice and Bob][npf-alice-and-bob] terminology is used. In
all cases, Alice initiates the first handshake attempt (either `XX` or `IK`).
Bob MAY initiate an `XXfallback` handshake following a failed `IK` attempt. The
`XXfallback` handshake is written in "Bob-initiated form," with the direction of
the arrows reversed from the canonical (Alice-initiated) notation.

```
XX:
  -> e
  <- e, ee, s, es   [Bob's identity payload]
  -> s, se          [Alice's identity payload]
  

IK:
  <- s
  ...
  -> e, es, s, ss   [Alice's identity payload]
  <- e, ee, se      [Bob's identity payload]
      
XXfallback:
  -> e
  ...
  <- e, ee, s, es   [Bob's identity payload]
  -> s, se          [Alice's identity payload]
```

Upon receiving the identity payload, peers MUST validate the signature against
the static Noise public key. If the signature is invalid, the connection MUST be
terminated immediately.


## Design Considerations and Tradeoffs

TK:

- rationale for signing with libp2p identity keys
  - why not just ed25519?
  - why not Noise Signatures

- rationale for handshake choices
  - Noise Pipes (0-RTT with efficient fallback)
  
- why not feed negotiation data into [Noise
  prologue](https://noiseprotocol.org/noise.html#prologue)?

[peer-id-spec]: ../peer-ids/peer-ids.md
[conn-spec]: ../connections/README.md
[multiselect-2-pr]: https://github.com/libp2p/specs/pull/95

[npf]: https://noiseprotocol.org/noise.html
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

[rfc-7748-sec-5]: https://tools.ietf.org/html/rfc7748#section-5
[protobuf]: https://developers.google.com/protocol-buffers/
