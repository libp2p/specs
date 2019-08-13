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
        - [Negotiating Whether to Use Noise](#negotiating-whether-to-use-noise)
        - [Negotiating a Specific Noise Protocol](#negotiating-a-specific-noise-protocol)
            - [Skipping Noise Protocol Negotiation to Prevent Deep Packet Inspection](#skipping-noise-protocol-negotiation-to-prevent-deep-packet-inspection)
            - [Noise Socket Negotiation Data](#noise-socket-negotiation-data)
            - [Noise Socket Negotiation Flow](#noise-socket-negotiation-flow)
    - [The Noise Handshake](#the-noise-handshake)
        - [Static Key Authentication](#static-key-authentication)
        - [libp2p Data in Handshake Messages](#libp2p-data-in-handshake-messages)
            - [The libp2p Signed Handshake Payload](#the-libp2p-signed-handshake-payload)
        - [Supported Handshake Patterns](#supported-handshake-patterns)
            - [XX](#xx)
            - [IX](#ix)
        - [Optimistic 0-RTT with Noise Pipes](#optimistic-0-rtt-with-noise-pipes)
            - [IK](#ik)
            - [XXfallback](#xxfallback)
    - [Cryptographic Primitives](#cryptographic-primitives)
        - [DH Functions](#dh-functions)
        - [Cipher Functions](#cipher-functions)
        - [Hash Functions](#hash-functions)
    - [Valid Noise Protocol Names](#valid-noise-protocol-names)
    - [Wire Format](#wire-format)
        - [Noise Socket Handshake Messages](#noise-socket-handshake-messages)
        - [Noise Socket Transport Messages](#noise-socket-transport-messages)
        - [Noise Socket Encrypted Payloads](#noise-socket-encrypted-payloads)
    - [libp2p Interfaces and API](#libp2p-interfaces-and-api)
    - [Design Considerations](#design-considerations)
        - [Why Noise Socket?](#why-noise-socket)
        - [Separate Negotiation for Noise Protocols](#separate-negotiation-for-noise-protocols)
        - [No Version Number in Protocol ID](#no-version-number-in-protocol-id)
        - [Distinct Noise and Identity Keys](#distinct-noise-and-identity-keys)
        - [Why Not Noise Signatures?](#why-not-noise-signatures)

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
about protocol and Noise handshake negotiation. 

Every Noise connection begins with a handshake between an initiating peer and a
responding peer, or in libp2p terms, a dialer and a listener. Over the course of
the handshake, peers exchange public keys and perform Diffie-Hellman exchanges
to arrive at a pair of symmetric keys that can be used to efficiently encrypt
traffic. The [Noise Handshake section](#the-noise-handshake) describes the
[supported handshake patterns](#supported-handshake-patterns) and [how
libp2p-specific data is exchanged during the
handshake](#libp2p-data-in-handshake-messages). 

During the handshake, the static
DH key used for Noise is authenticated using the libp2p identity keypair, as
described in the [Static Key Authentication section](#static-key-authentication).

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

noise-libp2p consists of several Noise protocols, each of which is defined by
its choice of [handshake pattern](#supported-handshake-patterns) and
[cryptographic primitives](#cryptographic-primitives). While it would be
possible to use the existing protocol negotiation process to select individual
Noise protocols, noise-libp2p does not expose that level of granularity to
libp2p's protocol negotiation framework.

Instead, we expect libp2p to [negotiate _whether to use
Noise_](#negotiating-whether-to-use-noise), while the noise-libp2p
implementation itself is responsible for [negotiating the specific Noise
protocol](#negotiating-a-specific-noise-protocol). The rationale for this is
described in Design Considerations section under [Separate Negotiation for Noise
Protocols](#separate-negotiation-for-noise-protocols).

### Negotiating Whether to Use Noise

noise-libp2p is identified by the protocol ID string `/noise`. Peers using
multistream-select for protocol negotiation may send this protocol ID during
connection establishment to attempt to use noise-libp2p.

Note that the protocol ID does not contain a version component. Instead, the
version of noise-libp2p in use is included in the [Noise Socket Negotiation
Data](#noise-socket-negotiation-data).

### Negotiating a Specific Noise Protocol

A concrete Noise protocol is identified by the choice of [Noise handshake
pattern](#noise-handshake-patterns) and [Diffie-Hellman, cipher, and hash
functions](#cryptographic-primitives) used.

The names of each "component" of the protocol is combined into a Noise protocol
name, as specified in the [Noise Protocol Names section of the Noise
spec][npf-protocol-names]. For example, an XX handshake using the 25519 DH
functions, AESGCM cipher and SHA256 hash functions would have the name
`Noise_XX_25519_AESGCM_SHA256`.

noise-libp2p supports multiple handshake patterns and cipher functions,
resulting in several [valid concrete Noise
protocols](#valid-noise-protocol-names). Peers negotiate which Noise protocol to
use by sending plaintext negotiation data as a preamble to their initial Noise
handshake message. This negotiation data identifies the Noise protocol that the
initiating peer would _prefer_ to use. If the responding peer accepts, they will
process the initial handshake message according to the rules of the identified
protocol. Otherwise, the responding peer MAY initiate a new handshake over the
existing connection as described in the [Noise Socket Negotiation Flow
section](#noise-socket-negotiation-flow).

noise-libp2p's negotiation process conforms to the [Noise Socket
spec][noise-socket-spec]. The Noise Socket protocol specifies how the
negotiation data is framed on the wire, but does not specify the format of the
negotiation data itself. The framing of Noise Socket messages (including
negotiation data) is covered in the [Wire Format section](#wire-format), while
this section describes the format and contents of the negotiation data itself.

Although the Noise Socket `negotiation_data` field is sent in plaintext, all
negotiation data is fed into the [Noise prologue][npf-prologue], which is
authenticated to ensure both parties have an identical view of it. This prevents
a man-in-the-middle from altering negotiation data and potentially forcing a
downgrade to an attacker-chosen Noise protocol.

#### Skipping Noise Protocol Negotiation to Prevent Deep Packet Inspection

The use of plaintext negotiation data makes noise-libp2p traffic identifiable
via deep packet inspection, which could allow network censors to block libp2p
traffic.

An initiating peer can preempt the Noise protocol negotiation process by sending
no `negotiation_data` with their initial Noise Socket message. 

If the Noise Socket message for an initial connection attempt has a
`negotiation_data_len` field equal to zero, the Noise protocol is assumed to be
`Noise_XX_25519_AESGCM_SHA256`, and no fallback protocol is possible.

Note that a Noise Socket message without negotiation data will not be entirely
indistinguishable from random data, as it will always contain two leading zero
bytes (the value of the `negotiation_data_len` field). 

If this is unacceptable, we could potentially impose an invariant that the
`negotiation_data` field have some arbitrary maximum length below the real
maximum of 65535. For example, we could define the maximum length as 16
kilobytes or so (16384 bytes). A peer wishing to skip negotiation can choose a
random value between 16385 and 65535 for `negotiation_data_len` and leave the
`negotiation_data` field empty. Upon receiving a `negotiation_data_len` greater
than the cutoff, a peer will act as if it had received a length of zero and
proceed to use the default Noise protocol.

#### Noise Socket Negotiation Data

To agree on a concrete Noise protocol, a [protobuf][protobuf] message with the
following schema is encoded and sent in the `negotiation_data` field of the
initial Noise Socket message.

```protobuf
message NoiseSocketNegotiation {
    uint32          noise_libp2p_version = 1;
    repeated uint32 alt_noise_libp2p_versions = 2;
    string          selected_proto = 3;
    repeated string alt_protos = 4;
    string          error_msg = 5;
}
```

The `noise_libp2p_version` field contains an integer that identifies the version
of this specification used to inform the implementation. The current version number
is `1`. If a peer receives a `NoiseSocketNegotiation` message containing an
unsupported or unknown version number, they MUST abort the handshake.

noise-libp2p implementations MAY support multiple versions of this spec, in
which case the `alt_noise_libp2p_versions` field should be non-empty and include
a list of supported versions. If a peer receives a `NoiseSocketNegotiation`
message with an unsupported `noise_libp2p_version`, they MAY select a supported
version from the `alt_noise_libp2p_versions` list and attempt to initiate a new
handshake using the supported version.

The `selected_proto` field is required, and MUST be set to the full Noise
protocol name that the initiating peer would like to use to complete the
handshake.

The `alt_protos` field is a list of Noise protocol names that are supported by
the sending peer, excluding `selected_proto`. If the sender only supports a
single Noise protocol, this field MUST be left empty.

The `error_msg` field is used for explicit rejection of an unsupported Noise
protocol, and MUST be blank in all other cases. The contents of the field are
implementation-specific and should be human-readable. Any non-empty value
indicates a failed handshake attempt and MUST result in terminating the
connection.

The Noise protocol names sent in the `selected_proto` and `alt_protos` fields
MUST be included in the [Valid Noise Protocol Names
section](#valid-noise-protocol-names).

As mentioned above, peers may wish to preempt the Noise protocol negotiation
process to thwart deep packet inspection techniques. This is done by sending an
initial Noise Socket message with an empty `negotiation_data` field and
`negotiation_data_len` set to zero. Upon receiving an initial Noise Socket
message without `negotiation_data`, peers SHOULD act as if they had received a
`NoiseSocketNegotiation` message with the following default values:

| field                       | default value                  |
|-----------------------------|--------------------------------|
| `noise_libp2p_version`      | `1`                            |
| `alt_noise_libp2p_versions` | empty                          |
| `selected_proto`            | `Noise_XX_25519_AESGGM_SHA256` |
| `alt_protos`                | empty                          |
| `error_msg`                 | empty                          |


#### Noise Socket Negotiation Flow

Upon receiving an initial Noise Socket message containing negotiation data and
an initial handshake message, the responding peer can choose between four
options. Because the iniatiator / responder roles may change throughout the
interaction, we'll call the peer that first attempts to establish the connection
Alice, and the peer she's connecting to will be Bob.

- **Accept**: Bob supports the Noise protocol in Alice's `selected_proto` field. Bob
  sends a Noise Socket message with an empty `negotiation_data` field, and a
  `noise_message` field containing the next handshake message in the sequence
  defined by the selected Noise protocol.
- **Switch**: Bob is unable to complete the handshake that Alice initially
  proposed, but is able to fallback to a different Noise protocol using an
  ephemeral key obtained from Alice's initial message. Bob sends a Noise Socket
  message with a new `selected_proto`, chosen from Alice's `alt_protos` list.
  This fallback message MUST include a `NoiseSocketNegotiation` message
  indicating the new protocol, as well as the initial handshake message for the
  new handshake.
- **Explicit Reject**: Bob is unable or unwilling to complete the handshake, and
  would like to inform Alice about the reason. Bob sends a Noise Socket message
  containing a `NoiseSocketNegotiation` message with a non-empty `error_msg`
  field describing the rejection reason. The Noise Socket `noise_message` field
  MUST be empty. After sending the rejection message, Bob closes the connection.
- **Silent Reject**: Bob closes the network connection abruptly without
  informing Alice.
 
The [Noise Socket spec][noise-socket-spec] also describes a fifth option,
Request Retry, which is useful when Bob would like to fallback to a Noise
protocol with a different Diffie-Hellman function that Alice supports but did
not send an ephemeral key for in her initial message. As noise-libp2p currently
only [supports](#cryptographic-primitives) the 25519 DH functions, this option
is not used.

Implementations MAY support the Explicit Reject option, or they may simply close
the connection silently to abort the handshake.

The Switch option is most useful when combined with the [`XXfallback` handshake
pattern](#xxfallback), which allows efficient recovery from a failed 0-RTT
handshake attempt without incurring wasteful roundtrips. This pattern is
described in [Optimistic 0-RTT with Noise
Pipes](#optimistic-0-rtt-with-noise-pipes).

## The Noise Handshake

During the Noise handshake, peers perform an authenticated key exchange
according to the rules defined by a concrete Noise protocol. 

Because noise-libp2p supports multiple concrete Noise protocols, the initial
handshake message contains negotiation data used to select a specific protocol,
as described [above](#negotiating-a-specific-noise-protocol).

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
payload](#the-libp2p-signed-handshake-payload). This signature is produced with
the private libp2p identity key, which proves that the sender was in possession
of the private identity key at the time the payload was generated.

### libp2p Data in Handshake Messages

In addition to authenticating the static Noise key, noise-libp2p implementations
MAY send additional "early data" in the handshake message payload. The contents
of this early data are opaque to noise-libp2p, however it is assumed that it
will be used to advertise supported stream multiplexers, thus avoiding a
round-trip negotiation after the handshake completes.

Any early data provided to noise-libp2p when initiating a connection MUST be
included in the [signed handshake payload](#the-libp2p-signed-handshake-payload)
as a byte string without alteration by the noise-libp2p implementation, and a
valid signature of the early data MUST be included as described below.

#### The libp2p Signed Handshake Payload

The noise-libp2p handshake payload is contained within a Noise handshake
message. It has the structure described in [Noise Socket Encrypted
Payloads](#noise-socket-encrypted-payloads). The `body` of the payload contains
a serialized [protobuf][protobuf] message with the following schema:

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

### Supported Handshake Patterns

Noise defines twelve [fundamental interactive handshake
patterns][npf-fundamental-patterns] for exchanging public keys between parties
and performing Diffie-Hellman computations.

The patterns are named according to whether static keypairs are used, and if so,
by what means each party gains knowledge of the other's static public key.

From the [fundamental patterns section of the Noise spec][npf-fundamental-patterns]:

```
The first character refers to the initiator's static key:

    * N = No static key for initiator
    * K = Static key for initiator Known to responder
    * X = Static key for initiator Xmitted ("transmitted") to responder
    * I = Static key for initiator Immediately transmitted to responder, despite reduced or absent identity hiding

The second character refers to the responder's static key:

    * N = No static key for responder
    * K = Static key for responder Known to initiator
    * X = Static key for responder Xmitted ("transmitted") to initiator
```

noise-libp2p supports three fundamental handshake patterns, each with a set of
[payload security][npf-payload-security] and [identity
hiding][npf-identity-hiding] properties.

The [XX handshake pattern](#xx) provides mutual authentication and encryption of
static keys and handshake payloads. It is the most "expensive" handshake,
requiring 1.5 round trips in order to be sound. Implementations MUST support the
XX handshake pattern.

The [IX handshake pattern](#ix) is similar to the XX handshake in that both
parties exchange static keys during the handshake. However, the first handshake
message is sent in plain text, exposing the public keys and [signed identity
payload](#the-libp2p-signed-identity-payload) of the initiator to passive
observers. In exchange, it requires only 1 round trip, compared to the 1.5 round
trips required for XX.

Implementations SHOULD support the `IX` handshake pattern, but it MUST NOT be
enabled by default. Users who are comfortable exposing the initiator's identity
in plaintext can enable the `IK` handshake when configuring noise-libp2p. This
tradeoff MUST be clearly communicated in developer-facing documentation to allow
an informed decision.

The [IK handshake pattern](#ik) is used in the context of [Optimistic 0-RTT with
Noise Pipes](#optimistic-0-rtt-with-noise-pipes) and is described in that
section along with the [`XXfallback`](#xxfallback) variation on the `XX`
pattern.

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

The second and third handshake messages include a [signed handshake
payload](#the-libp2p-signed-handshake-payload), which contains a signature
authenticating the sender's static Noise key as described in the [Static Key
Authentication section](#static-key-authentication).

The XX handshake MUST be supported by noise-libp2p implementations, and SHOULD
be enabled by default.

A variation on the `XX` handshake, [`XXfallback`](#xxfallback) can be optionally
enabled to support [Optimistic 0-RTT with Noise
Pipes](#optimistic-0-rtt-with-noise-pipes) and is described in that context below.

#### IX

``` 
IX:
      -> e, s
      <- e, ee, se, s, es
```

In the `IX` handshake pattern, the initiator sends their public Noise keys
(ephemeral and static) in plain text. This first message also contains the
initiator's [signed handshake payload](#the-libp2p-signed-handshake-payload),
which contains the public libp2p identity of the initiator and may include
other libp2p-specific data. 

The `IX` pattern MAY be supported by noise-libp2p implementations, but MUST NOT
be enabled by default. The lack of initiator privacy MUST be communicated in
developer documentation, so that users can opt-in to `IX` if they are
comfortable with the trade off in privacy.

### Optimistic 0-RTT with Noise Pipes

The Noise spec describes a [compound protocol][npf-compound-protocol] called
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

The Noise Pipes pattern in libp2p is implemented using the [Noise Socket
Negotiation Flow](#noise-socket-negotiation-flow) described above. 

When attempting a zero-RTT handshake, Alice's negotiation data will include a
`selected_proto` based on the `IK` handshake pattern, for example,
`Noise_IK_25519_AESGCM_SHA256`. If this is acceptable to Bob, he will **Accept**
the attempt by sending a Noise Socket message with no negotiation data
containing the next handshake message in the `IK` pattern.

If Bob can't decrypt the `IK` message, and Alice has included a Noise protocol
using the `XX` handshake pattern in her `alt_protos` list, Bob will attempt to
**Switch** to an `XXfallback` handshake. Bob sends a Noise Socket message whose
negotiation data includes a `selected_proto` that uses the `XXfallback`
handshake pattern. For example, Bob may send
`Noise_XXfallback_25519_AESGCM_SHA256` as his `selected_proto`. Following the
negotiation data, Bob sends the first message of the `XXfallback` pattern, which
corresponds to the second message in the traditional `XX` pattern.

When Alice receives Bob's `XXfallback` message, she will attempt to use the
ephemeral key from her initial `IK` attempt to complete the handshake. Alice
sends a Noise Socket message with no negotiation data and the final handshake
message in the `XX` pattern.


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

## Cryptographic Primitives

The Noise framework allows protocol designers to choose from a small set of
Diffie-Hellman key exchange functions, symmetric ciphers, and hash functions.

The functions currently supported by noise-libp2p are:

### DH Functions

noise-libp2p implementations MUST support the [25519 DH functions][npf-dh-25519]
as defined in the Noise spec.

### Cipher Functions

noise-libp2p implementations MUST support the [AESGCM cipher
functions][npf-cipher-aesgcm] and SHOULD support the [ChaChaPoly cipher
functions][npf-cipher-chachapoly] as defined in the Noise spec.

### Hash Functions

noise-libp2p implementations MUST support the [SHA256 hash
function][npf-hash-sha256] as defined in the Noise spec.

## Valid Noise Protocol Names

This section lists the [Noise protocol names][npf-protocol-names] that are valid
according to the definitions in this spec.

This list contains all possible combinations of the supported [handshake
patterns](#supported-handshake-patterns) and [cryptographic
primitives](#cryptographic-primitives).

The `Noise_XX_25519_AESGCM_SHA256` protocol MUST be supported by all
implementations. Other protocols SHOULD or MAY be supported according to the
recommendations given elsewhere in this spec. For example, implementations
SHOULD support the ChaChaPoly cipher and thus SHOULD support the
`Noise_XX_25519_ChaChaPoly_SHA256` Noise protocol.

As some protocols are only useful in the context of the [Noise
Pipes pattern](#optimistic-0-rtt-with-noise-pipes), they are listed separately
below.

These are the protocols that are unrelated to Noise Pipes:

- `Noise_XX_25519_AESGCM_SHA256`
- `Noise_XX_25519_ChaChaPoly_SHA256`
- `Noise_IX_25519_AESGCM_SHA256`
- `Noise_IX_25519_ChaChaPoly_SHA256`

These are the protocols relevant to Noise Pipes:

- `Noise_IK_25519_AESGCM_SHA256`
- `Noise_IK_25519_ChaChaPoly_SHA256`
- `Noise_XXfallback_25519_AESGCM_SHA256`
- `Noise_XXfallback_25519_ChaChaPoly_SHA256`


## Wire Format

The [Noise Socket spec][noise-socket-spec] defines the format of Noise Socket
handshake and transport messages, and noise-libp2p adopts this format. For
completeness, the structure of all messages is listed below.

### Noise Socket Handshake Messages

A Noise Socket handshake message has the following structure:

| `negotiation_data_len` | `negotiation_data` | `noise_message_len` | `noise_message` |
|------------------------|--------------------|---------------------|-----------------|
| 2 bytes                | variable length    | 2 bytes             | variable length |

`negotiation_data_len` and `noise_message_len` store the length in bytes of the
`negotiation_data` and `noise_message` fields, encoded as 16-bit big-endian
unsigned integers.

The Noise handshake message contained in the `noise_message` field may have an
encrypted payload. If so, it will have the structure described in [Noise Socket
Encrypted Payloads](#noise-socket-encrypted-payloads).

### Noise Socket Transport Messages

A Noise Socket transport message has the following structure:

| `noise_message_len` | `noise_message` |
|---------------------|-----------------|
| 2 bytes             | variable length |

The `noise_message_len` field stores the length in bytes of the `noise_message`
field, encoded as a 16-bit big-endian unsigned integer.

All Noise Socket transport messages have a single encrypted payload, described below.

### Noise Socket Encrypted Payloads

All Noise Socket transport messages have a single encrypted payload, contained
within the `noise_message` field. Noise Socket handshake messages may have an
encrypted payload, or may contain a plaintext payload.

Once decrypted, the plaintext of an encrypted payload will have this structure:

| `body_len` | `body`          | `padding`       |
|------------|-----------------|-----------------|
| 2 bytes    | variable length | variable length |

The `body_len` field stores the length in bytes of the `body` field as an
unsigned 16-bit big-endian integer.

All data following the `body` field consists of padding bytes, which must be
ignored by the recipient. Senders SHOULD use a source of random data to populate
the padding field and may use any length of padding that does not cause the
total length of the Noise message to exceed 65535 bytes.

## Encryption and I/O

During the handshake phase, the initiator (Alice) will choose their preferred
Noise protocol, e.g. `Noise_IX_25519_AESGCM_SHA256`, and will initialize a Noise
[`HandshakeState` object][npf-handshake-state] with the corresponding
parameters.

Alice will construct negotiation data as described in [Noise Socket Negotiation
Data](#noise-socket-negotiation-data) and serialize it to a byte array. She will
then construct a [Noise Socket Handshake
Message](#noise-socket-handshake-messages), setting the `negotiation_data_len`
and `negotiation_data` fields to store the negotiation data. The `noise_message`
field will contain the initial Noise handshake message in the chosen handshake
pattern.

Alice sets the [Noise prologue][npf-prologue] for the handshake using data from
her initial message. The prologue data consists of the following values
concatenated together:

- The UTF-8 string `NoiseSocketInit1`
- Alice's initial `negotiation_data_len`
- Alice's initial `negotiation_data`

Upon receiving an initial Noise Socket handshake message, Bob will "peek" at the
negotiation data by decoding `negotiation_data_len`, reading `negotiation_data`
and decoding the serialized negotiation data. They will then either accept the
proposed protocol and send the next handshake message, or they will attempt to
switch to a new Noise protocol.

If Bob accepts Alice's preferred protocol, he will derive Noise prologue data
from her initial message as described above.

If Bob would like to switch to a fallback protocol, his first response to Alice
will include a non-empty `negotiation_data` field. Alice will re-initialize her
Noise `HandshakeState` with the new fallback protocol, taking care to preserve
the ephemeral key sent in her initial message. She will then respond with the
next handshake message in the pattern used by the fallback protocol.

When switching to Bob's new protocol, both parties derive Noise prologue data
by concatenating the following values:

- The UTF-8 string `NoiseSocketInit2`
- Alice's initial `negotiation_data_len`
- Alice's initial `negotiation_data`
- Alice's initial `noise_message_len`
- Alice's initial `noise_message`
- Bob's responding `negotiation_data_len`
- Bob's responding `negotiation_data`

Whether Bob accepts Alice's initial protocol or switches to a new protocol,
Alice and Bob will continue to exchange handshake messages until the chosen
pattern is complete.

Following a successful handshake, each peer will possess two Noise
[`CipherState` objects][npf-cipher-state]. One is used to encrypt outgoing
data to the remote party, and the other is used to decrypt incoming data.

After the handshake, all data exchanged between peers is framed into [Noise
Socket Transport Messages](#noise-socket-transport-messages). A Noise Socket
transport message contains a `noise_message` field, which is an AEAD ciphertext
consisting of an encrypted payload plus 16 bytes of authentication data, as
[defined in the Noise spec][npf-message-format].

When decrypted, the payload of a Noise Socket transport message will have the
structure described in [Noise Socket Encrypted
Payloads](#noise-socket-encrypted-payloads). Receivers MUST decode the
`body_len` field from the decrypted payload, and MUST ignore any additional
padding following the `body` field.

In the unlikely event that peers exchange more than `2^64 - 1` messages, they
MUST terminate the connection to avoid reusing nonces, in accordance with the
[Noise spec][npf-security].

## libp2p Interfaces and API

TK: 

- describe internal API & how noise-libp2p fits in with the transport upgrade
pattern.

- API must be compatible with current transport upgrader
- should optionally allow injection of "early data" into the handshake for use by
  multiselect 2

## Design Considerations

### Why Noise Socket?

See below for why it's nice to separate out Noise protocol negotiation from the
rest of libp2p.

Apart from negotiation, Noise Socket has a clean and simple message framing
format that's easy to steal, which is a nice bonus.

In my mind the biggest drawback is that plaintext negotiation data makes us
vulnerable to deep packet inspection. I tried to address that with a default "no
negotiation" case, but that's still possibly too identifiable, and it locks
people who highly value anonymity into using a single default Noise protocol.

I think it is possible to have some flexibility in the choice of Noise protocol
without exposing plaintext negotiation data. The Noise spec
[describes][npf-handshake-indistinguishability] a Noise Pipes variant that makes
handshake types indistinguishable to an observer.

This is a possibility, although it's less flexible than explicit negotiation.
For example, it doesn't let us choose between `AESGCM` and `ChaChaPoly`.

A potential alternative that I thought about is to have multiaddrs contain
concrete Noise protocols, and have peers advertise supported protocols out of
band. So a peer supporting `XX` and both `AESGCM` and `ChaChaPoly` could
advertise e.g.:

- `/ip4/1.2.3.4/tcp/42/noise/Noise_XX_25519_AESGCM_SHA256`
- `/ip4/1.2.3.4/tcp/42/noise/Noise_XX_25519_ChaChaPoly_SHA256`

However, the listening peer will not have access to the multiaddr used to dial,
and will need to be able to infer the Noise protocol from the contents of the
initial message. This is at odds with a desire to keep handshakes
indistinguishable to an observer.

### Separate Negotiation for Noise Protocols

While libp2p has an existing protocol negotiation system called
multistream-select, it's due for replacement and the new design is being shaped
up now.

Negotiating Noise protocols within the domain of the Noise transport module
makes us minimally dependent on the current multistream-select design and
doesn't impose any new requirements on multiselect 2. 

If we end up putting crypto channels into multiaddrs, having a single entry
point lets us have nice addresses like `/ip4/1.2.3.4/tcp/42/noise`.

### No Version Number in Protocol ID

Similar to the separate negotiation point, this is motivated by the possibility
of using multiaddr instead of protocol negotiation to select noise-libp2p. If
we go that route, we don't want to have to define a new multicodec for each
version of the spec, e.g. `/noise-1.0`, etc.

It does add a fair bit of complexity by having version numbers in the
negotiation data, especially the bit where you can potentially support multiple
versions.

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
users won't also use their libp2p identity keys in other contexts (e.g. SECIO),
requiring separate keys seems prudent.

### Why Not Noise Signatures?

Since we're using signatures for authentication, the [Noise Signatures
extension][noise-signatures-spec] is a natural candidate for adoption.

Unfortunately, the Noise Signatures spec requires both parties to use the same
signature algorithm, which would prevent peers with different identity key types
to complete a Noise Signatures handshake. Also, only Ed25519 signatures are
currently supported by the spec, while libp2p identity keys may be of other
unsupported types like RSA.

[peer-id-spec]: ../peer-ids/peer-ids.md
[peer-id-spec-key-rules]: ../peer-ids/peer-ids.md#how-keys-are-encoded-and-messages-signed

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
