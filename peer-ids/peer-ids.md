# Peer Ids and Keys

| Lifecycle Stage | Maturity Level | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 3A              | Recommendation | Active | r1, 2019-08-15  |

**Authors**: [@mgoelzer], [@yusefnapora], [@lidel]

**Interest Group**: [@raulk], [@vyzo], [@Stebalien]

[@mgoelzer]: https://github.com/mgoelzer
[@yusefnapora]: https://github.com/yusefnapora
[@raulk]: https://github.com/raulk
[@vyzo]: https://github.com/vyzo
[@Stebalien]: https://github.com/Stebalien
[@lidel]: https://github.com/lidel

See the [lifecycle document](../00-framework-01-spec-lifecycle.md) for context
about maturity level and spec status.

## Table of Contents

- [Overview](#overview)
- [Keys](#keys)
    - [Where are keys used?](#where-are-keys-used)
    - [Key Types](#key-types)
        - [RSA](#rsa)
        - [Ed25519](#ed25519)
        - [Secp256k1](#secp256k1)
        - [ECDSA](#ecdsa)
- [Peer Ids](#peer-ids)
    - [String representation](#string-representation)
        - [Encoding](#encoding)
        - [Decoding](#decoding)

## Overview

libp2p uses cryptographic key pairs to sign messages and derive unique
peer identities (or "peer ids").

This document describes the types of keys supported, how keys are serialized
for transmission, and how peer ids are generated from the hash of serialized
public keys.

Although private keys are not transmitted over the wire, the serialization
format used to store keys on disk is also included as a reference for libp2p
implementors who would like to import existing libp2p key pairs.

Key encodings and message signing semantics are
[covered below](#how-keys-are-encoded-and-messages-signed).

## Keys

Libp2p encodes keys in a [protobuf](https://github.com/libp2p/go-libp2p-core/blob/master/crypto/pb/crypto.proto)
containing a key _type_ and the encoded key (where the encoding depends on the type).

Specifically:

```protobuf
syntax = "proto2";

enum KeyType {
	RSA = 0;
	Ed25519 = 1;
	Secp256k1 = 2;
	ECDSA = 3;
}

message PublicKey {
	required KeyType Type = 1;
	required bytes Data = 2;
}

message PrivateKey {
	required KeyType Type = 1;
	required bytes Data = 2;
}
```

The `PublicKey` and `PrivateKey` messages contain a `Data` field with serialized
keys, and a `Type` enum that specifies the type of key.

Each key type has its own serialization format within the `Data` field,
[described below](#key-types).

Finally, libp2p places a stronger requirement on the protobuf encoder than the
protobuf spec: encoding must be deterministic. To achieve this, libp2p imposes
two additional requirements:

1. Fields must be minimally encoded. That is, varints must use the minimal
   representation (fewest bytes that can encode the given number).
2. Fields must be encoded in tag order (i.e., key type, then the key data).
3. All fields must be included.
4. No additional fields may be defined.

Note that `PrivateKey` messages are never transmitted over the wire.
Current libp2p implementations store private keys on disk as a serialized
`PrivateKey` protobuf message. libp2p implementors who want to load existing
keys can use the `PrivateKey` message definition to deserialize private key
files.

### Where are keys used?

Keys are used in two places in libp2p. The first is for signing messages. Here
are some examples of messages we sign:
 - IPNS records
 - PubSub messages
 - SECIO handshake

The second is for generating peer ids; this is discussed in the section below.

### Key Types

Four key types are supported:
 - RSA
 - Ed25519
 - Secp256k1
 - ECDSA

Implementations MUST support RSA and Ed25519. Implementations MAY support
Secp256k1 and ECDSA, but nodes using those keys may not be able to connect to
all other nodes.

In all cases, implementation MAY allow the user to enable/disable specific key
types via configuration. Note that disabling support for compulsory key types
may hinder connectivity.

The following sections describe:

1. How each key type is encoded into the libp2p key's Data field.
2. How each key type creates and validates signatures.

Implementations may use whatever in-memory representation is convenient,
provided the encodings described below are used at the "I/O boundary".

#### RSA

We encode the public key using the DER-encoded PKIX format.

We encode the private key as a PKCS1 key using ASN.1 DER.

To sign a message, we first hash it with SHA-256 and then sign it using the
[RSASSA-PKCS1-V1.5-SIGN](https://tools.ietf.org/html/rfc3447#section-8.2)
method, as originally defined in [RSA PKCS#1
v1.5](https://tools.ietf.org/html/rfc2313).

#### Ed25519

Ed25519 specifies the exact format for keys and signatures, so we do not do much
additional encoding, except as noted below.

We do not do any special additional encoding for Ed25519 public keys.

The encoding for Ed25519 private keys is a little unusual. There are two formats
that we encourage implementors to support:

 - Preferred method is a simple concatenation: `[private key bytes][public key
   bytes]` (64 bytes)
 - Older versions of the libp2p code used the following format: `[private
   key][public key][public key]` (96 bytes). If you encounter this type of
   encoding, the proper way to process it is to compare the two public key
   strings (32 bytes each) and verify they are identical. If they are, then
   proceed as you would with the preferred method. If they do not match, reject
   or error out because the byte array is invalid.

Ed25519 signatures follow the normal [Ed25519 standard](https://tools.ietf.org/html/rfc8032#section-5.1).

#### Secp256k1

We use the standard Bitcoin EC encoding for Secp256k1 public and private keys.

To sign a message, we hash the message with SHA 256, then sign it using the
standard [Bitcoin EC signature algorithm
(BIP0062)](https://github.com/bitcoin/bips/blob/master/bip-0062.mediawiki), and
then use [standard Bitcoin
encoding](https://github.com/bitcoin/bips/blob/master/bip-0062.mediawiki#der-encoding).

#### ECDSA

We encode the public key using ASN.1 DER.

We encode the private key using DER-encoded PKIX.

To sign a message, we hash the message with SHA 256, and then sign it with the
[ECDSA standard algorithm](https://tools.ietf.org/html/rfc6979), then we encode
it using [DER-encoded ASN.1.](https://wiki.openssl.org/index.php/DER)

## Peer Ids

Peer IDs are derived by hashing the encoded public key with
[multihash][multihash]. Keys that serialize to more than 42 bytes must be hashed
using sha256 multihash, keys that serialize to at most 42 bytes must be hashed
using the "identity" multihash codec.

Specifically, to compute a peer ID of a key:

1. Encode the public key as described in the [keys](#keys) section.
4. If the length of the serialized bytes is less than or equal to 42, compute
   the "identity" multihash of the serialized bytes. In other words, no
   hashing is performed, but the [multihash format is still
   followed][multihash] (byte plus varint plus serialized bytes). The idea
   here is that if the serialized byte array is short enough, we can fit it in
   a multihash verbatim without having to condense it using a hash function.
5. If the length is greater than 42, then hash it using it using the SHA256
   multihash.

### String representation

There are two ways to represent peer IDs in text: as a raw
[base58btc][base58btc] encoded multihash (e.g., `Qm...`, `1...`) and as a
[multibase][multibase] encoded [CID][cid] (e.g., `bafz...`). Libp2p is slowly
transitioning from the first (legacy) format to the second (new).

Implementations MUST support parsing both forms of peer IDs. Implementations
SHOULD display peer IDs using the first (raw base58btc encoded multihash) format
until the second format is widely supported.

Peer IDs encoded as CIDs must be encoded using CIDv1 and must use the
`libp2p-key` [multicodec][multicodec] (0x72). By default, such peer IDs SHOULD
be encoded in using the base32 multibase
([RFC4648](https://tools.ietf.org/html/rfc4648), without padding).

For reference, CIDs (encoded in text) have the following format

```
<multibase-prefix><cid-version><multicodec><multihash>
```

#### Encoding

To encode a peer ID using the legacy format, simply encode it with base58btc.

To encode a peer ID using the new format, create a CID with the `libp2p-key` multicodec and encode it using multibase.

#### Decoding

To decode a peer ID:

* If it starts with `1` or `Qm`, it's a bare [base58btc][base58btc] encoded
  [multihash][multihash]. Decode it according to the base58btc algorithm.
* If it starts with a [multibase][multibase] prefix, it's a CIDv1
  CID. Decode it according to the multibase and [CID spec][cid-decoding].
  * Once decoded, verify that the CIDs multicodec is `libp2p-key`.
  * Finally, extract the multihash from the CID. This is the peer ID.
* Otherwise, it's not a valid peer ID.

Examples:

- `bafzbeie5745rpv2m6tjyuugywy4d5ewrqgqqhfnf445he3omzpjbx5xqxe` -- Peer ID (sha256) encoded as a CID
  ([inspect](http://cid.ipfs.io/#bafzbeie5745rpv2m6tjyuugywy4d5ewrqgqqhfnf445he3omzpjbx5xqxe)).
- `QmYyQSo1c1Ym7orWxLYvCrM2EmxFTANf8wXmmE7DWjhx5N` -- Peer ID (sha256) encoded as a raw base58btc multihash.
- `12D3KooWD3eckifWpRn9wQpMG9R9hX3sD158z7EqHWmweQAJU5SA` -- Peer ID (ed25519, using the "identity" multihash) encoded as a raw base58btc multihash.

[multihash]: https://github.com/multiformats/multihash
[multicodec]: https://github.com/multiformats/multicodec
[multibase]: https://github.com/multiformats/multibase
[base58btc]: https://en.bitcoinwiki.org/wiki/Base58#Alphabet_Base58
[cid]: https://github.com/multiformats/cid
[cid-decoding]: https://github.com/multiformats/cid#decoding-algorithm
[protobuf-encoding]: https://developers.google.com/protocol-buffers/docs/encoding
