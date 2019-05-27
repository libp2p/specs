# SECIO 1.0.0

> A stream security transport for libp2p. Streams wrapped by SECIO use secure
> sessions to encrypt all traffic.

| Lifecycle Stage | Maturity Level | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 3A              | Recommendation | Active | r0, 2019-05-27  |

Authors: [@jbenet][@jbenet], [@bigs][@bigs], [@yusefnapora][@yusefnapora]

Interest Group: [@Stebalien][@Stebalien],
[@richardschneider][@richardschneider], [@tomaka][@tomaka], [@raulk][@raulk]

[@jbenet]: https://github.com/jbenet
[@bigs]: https://github.com/bigs
[@yusefnapora]: https://github.com/yusefnapora
[@Stebalien]: https://github.com/Stebalien
[@richardschneider]: https://github.com/richardschneider
[@tomaka]: https://github.com/tomaka
[@raulk]: https://github.com/raulk

See the [lifecycle document](../00-framework-01-spec-lifecycle.md) for context
about maturity level and spec status.

## Table of Contents

- [SECIO 1.0.0](#secio-100)
    - [Table of Contents](#table-of-contents)
    - [Implementations](#implementations)
    - [Algorithm Support](#algorithm-support)
        - [Exchanges](#exchanges)
        - [Ciphers](#ciphers)
        - [Hashes](#hashes)
    - [Data Structures](#data-structures)
    - [Protocol](#protocol)
        - [Prerequisites](#prerequisites)
        - [Message framing](#message-framing)
        - [Proposal Generation](#proposal-generation)
        - [Determining Roles and Algorithms](#determining-roles-and-algorithms)
        - [Key Exchange](#key-exchange)
            - [Key marshaling](#key-marshaling)
        - [Shared Secret Generation](#shared-secret-generation)
        - [Key Stretching](#key-stretching)
        - [Creating the Cipher and HMAC signer](#creating-the-cipher-and-hmac-signer)
        - [Initiate Secure Channel](#initiate-secure-channel)
            - [Secure Message Framing](#secure-message-framing)
            - [Initial Packet Verification](#initial-packet-verification)

## Implementations

- [js-libp2p-secio](https://github.com/libp2p/js-libp2p-secio)
- [go-secio](https://github.com/libp2p/go-libp2p-secio)
- [rust-libp2p](https://github.com/libp2p/rust-libp2p/tree/master/protocols/secio)

## Algorithm Support

SECIO allows participating peers to support a subset of the following
algorithms.

### Exchanges

The following elliptic curves are used for ephemeral key generation:

- P-256
- P-384
- P-521

### Ciphers

The following symmetric ciphers are used for encryption of messages once
the SECIO channel is established:

- AES-256
- AES-128

Note that current versions of `go-libp2p` support the Blowfish cipher, however
support for Blowfish will be dropped in future releases and should not be
considered part of the SECIO spec.

### Hashes

The following hash algorithms are used for key stretching and for HMACs once
the SECIO channel is established:

- SHA256
- SHA512

## Data Structures

The SECIO wire protocol features two message types defined in the version 2 syntax of the
[protobuf description language](https://developers.google.com/protocol-buffers/docs/proto).

```protobuf
syntax = "proto2";

message Propose {
	optional bytes rand = 1;
	optional bytes pubkey = 2;
	optional string exchanges = 3;
	optional string ciphers = 4;
	optional string hashes = 5;
}

message Exchange {
	optional bytes epubkey = 1;
	optional bytes signature = 2;
}
```


These two messages, `Propose` and `Exchange` are the only serialized types
required to implement SECIO.

## Protocol

### Prerequisites

Prior to undertaking the SECIO handshake described below, it is assumed that
we have already established a dedicated bidirectional channel between both
parties, and that both have agreed to proceed with the SECIO handshake
using [multistream-select][multistream-select] or some other form of protocol
negotiation.

### Message framing

All messages sent over the wire are prefixed with the message length in bytes,
encoded as an unsigned variable length integer as defined
by the [multiformats unsigned-varint spec][unsigned-varint].

### Proposal Generation

SECIO channel negotiation begins with a proposal phase.

Each side will construct a `Propose` protobuf message (as defined [above](#data-structures)),
setting the fields as follows:

| field       | value                                                                                |
|-------------|--------------------------------------------------------------------------------------|
| `rand`      | A 16 byte random nonce, generated using the most secure means available              |
| `pubkey`    | The sender's public key, serialized [as described in the peer-id spec][peer-id-spec] |
| `exchanges` | A list of supported [key exchanges](#exchanges) as a comma-separated string          |
| `ciphers`   | A list of supported [ciphers](#ciphers) as a comma-separated string                  |
| `hashes`    | A list of supported [hashes](#hashes) as a comma-separated string                    |


Both parties serialize this message and send it over the wire. If either party
has prior knowledge of the other party's peer id, they may attempt to validate
that the given public key can be used to generate the same peer id, and may
close the connection if there is a mismatch.


### Determining Roles and Algorithms

Next, the peers use a deterministic formula to compute their roles in the coming
exchanges. Each peer computes:

```
oh1 := sha256(concat(remotePeerPubKeyBytes, myNonce))
oh2 := sha256(concat(myPubKeyBytes, remotePeerNonce))
```

Where `myNonce` is the `rand` component of the local peer's `Propose` message,
and `remotePeerNonce` is the `rand` field from the remote peer's proposal.

With these hashes, determine which peer's preferences to favor. This peer will
be referred to as the "preferred peer". If `oh1 == oh2`, then the peer is
communicating with itself and should return an error. If `oh1 < oh2`, use the
remote peer's preferences. If `oh1 > oh2`, prefer the local peer's preferences.

Given our preference, we now sort through each of the `exchanges`, `ciphers`,
and `hashes` provided by both peers, selecting the first item from our preferred
peer's set that is also shared by the other peer.

### Key Exchange

Now the peers prepare a key exchange. 

Both peers generate an ephemeral keypair using the elliptic curve algorithm that was
chosen from the proposed `exchanges` in the previous step.

With keys generated, both peers create an `Exchange` message. First, they start by
generating a "corpus" that they will sign.

```
corpus := concat(myProposalBytes, remotePeerProposalBytes, ephemeralPubKey)
```

The `corpus` is then signed using the permanent private key associated with the local
peer's peer id, producing a byte array `signature`.


| field       | value                                                                     |
|-------------|---------------------------------------------------------------------------|
| `epubkey`   | The ephemeral public key, marshaled as described [below](#key-marshaling) |
| `signature` | The `signature` of the `corpus` described above                           |


The peers serialize their `Exchange` messages and write them over the wire. Upon
receiving the remote peer's `Exchange`, the local peer will compute the remote peer's
expected `corpus` using the known proposal bytes and the ephemeral public key sent by
the remote peer in the `Exchange`. The `signature` can then be validated using the
permanent public key of the remote peer obtained in the initial proposal.

Peers MUST close the connection if the signature does not validate.

#### Key marshaling

Within the `Exchange` message, ephemeral public keys are marshaled into the
uncompressed form specified in section 4.3.6 of ANSI X9.62. 

This is the behavior provided by the go standard library's 
[`elliptic.Marshal`](https://golang.org/pkg/crypto/elliptic/#Marshal) function.

### Shared Secret Generation

Peers now generate their shared secret by combining their ephemeral private key with the
remote peer's ephemeral public key.

First, the remote ephemeral public key is unmarshaled into a point on the elliptic curve
used in the agreed-upon exchange algorithm. If the point is not valid for the agreed-upon
curve, secret generation fails and the connection must be closed.

The remote ephemeral public key is then combined with the local ephemeral private key
by means of elliptic curve scalar multiplication. The result of the multiplication is
the shared secret, which will then be stretched to produce MAC and cipher keys, as
described in the next section.

### Key Stretching

The key stretching process uses an HMAC algorithm to derive encryption and MAC keys
and a stream cipher initialization vector from the shared secret.

Key stretching produces the following three values for each peer:

- A MAC key used to initialize an HMAC algorithm for message verification
- A cipher key used to initialize a block cipher
- An initialization vector (IV), used to generate a CTR stream cipher from the block cipher

The key stretching function will return two data structures `k1` and `k2`, each containing
the three values above.

Before beginning the stretching process, the size of the IV and cipher key are determined
according to the agreed-upon cipher algorithm. The sizes (in bytes) used are as follows:

| cipher type | cipher key size | IV size |
|-------------|-----------------|---------|
| AES-128     | 16              | 16      |
| AES-256     | 32              | 16      |

The generated MAC key will always have a size of 20 bytes.

Once the sizes are known, we can compute the total size of the output we need to generate
as `outputSize := 2 * (ivSize + cipherKeySize + macKeySize)`.

The stretching algorithm will then proceed as follows:

First, an HMAC instance is initialized using the agreed upon hash function and shared secret.

A fixed seed value of `"key expansion"` (encoded into bytes as UTF-8) is fed into the HMAC
to produce an initial digest `a`.

Then, the following process repeats until `outputSize` bytes have been generated:

- reset the HMAC instance or generate a new one using the same hash function and shared secret
- compute digest `b` by feeding `a` and the seed value into the HMAC: 
  - `b := hmac_digest(concat(a, "key expansion"))`
- append `b` to previously generated output (if any).
  - if, after appending `b`, the generated output exceeds `outputSize`, the output is truncated to `outputSize` and generation ends.
- reset the HMAC and feed `a` into it, producing a new value for `a` to be used in the next iteration
  - `a = hmac_digest(a)`
- repeat until `outputSize` is reached

Having generated `outputSize` bytes, the output is then split into six parts to
produce the final return values `k1` and `k2`:

```
| k1.IV | k1.CipherKey | k1.MacKey | k2.IV | k2.CipherKey | k2.MacKey |
```

The size of each field is determined by the cipher key and IV sizes detailed above.

### Creating the Cipher and HMAC signer

With `k1` and `k2` computed, swap the two values if the remote peer is the
preferred peer. After swapping if necessary, `k1` becomes the local peer's key
and `k2` the remote peer's key.

Each peer now generates an HMAC signer using the agreed upon algorithm and the
`MacKey` produced by the key stretcher.

Each peer will also initialize the agreed-upon block cipher using the generated
`CipherKey`, and will then initialize a CTR stream cipher from the block cipher
using the generated initialization vector `IV`.

### Initiate Secure Channel

With the cipher and HMAC signer created, the secure channel is ready to be
opened. 

#### Secure Message Framing

To communicate over the channel, peers send packets containing an encrypted
body and an HMAC signature of the encrypted body.

The encrypted body is produced by applying the stream cipher initialized
previously to an arbitrary plaintext message payload. The encrypted data
is then fed into the HMAC signer to produce the HMAC signature.

Once the encrypted body and HMAC signature are known, they are concatenated
together, and their combined length is prefixed to the resulting payload.

Each packet is of the form:

```
[uint32 length of packet | encrypted body | hmac signature of encrypted body]
```

The packet length is in bytes, and it is encoded as an unsigned 32-bit integer
in network (big endian) byte order.

#### Initial Packet Verification

The first packet transmitted by each peer must be the remote peer's nonce.

Each peer will decrypt the message body and validate the HMAC signature,
comparing the decrypted output to the nonce recieved in the initial
`Propose` message. If either peer is unable to validate the initial
packet against the known nonce, they must abort the connection.

If both peers successfully validate the initial packet, the secure channel has
been opened and is ready for use, using the framing rules described
[above](#secure-message-framing).


[peer-id-spec]: https://github.com/libp2p/specs/peer-ids/peer-ids.md

[multistream-select]: https://github.com/multiformats/multistream-select
[unsigned-varint]: https://github.com/multiformats/unsigned-varint
