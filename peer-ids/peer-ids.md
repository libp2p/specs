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

- [Peer Ids and Keys](#peer-ids-and-keys)
    - [Table of Contents](#table-of-contents)
    - [Overview](#overview)
    - [Keys](#keys)
        - [Where are keys used?](#where-are-keys-used)
    - [Peer Ids](#peer-ids)
        - [Note about deterministic encoding](#note-about-deterministic-encoding)
        - [String representation](#string-representation)
    - [How Keys are Encoded and Messages Signed](#how-keys-are-encoded-and-messages-signed)
        - [RSA](#rsa)
        - [Ed25519](#ed25519)
        - [Secp256k1](#secp256k1)
        - [ECDSA](#ecdsa)


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

Our key pairs are wrapped in a [simple protobuf](https://github.com/libp2p/go-libp2p-crypto/blob/master/pb/crypto.proto),
defined using the [Protobuf version 2 syntax](https://developers.google.com/protocol-buffers/docs/proto):

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
[described below](#how-keys-are-encoded-and-messages-signed).

Note that `PrivateKey` messages are never transmitted over the wire.
Current libp2p implementations store private keys on disk as a serialized
`PrivateKey` protobuf message. libp2p implementors who want to load existing
keys can use the `PrivateKey` message definition to deserialize private key
files.

### Where are keys used?

Keys are used in two places in libp2p.  The first is for signing messages.  Here are some examples of messages we sign:
 - IPNS records
 - PubSub messages
 - SECIO handshake

The second is for generating peer ids; this is discussed in the section below.

## Peer Ids

Here is the process by which we generate peer ids based on the public component of the keypairs described above:

  1. Encode the public key into a byte array according to the rules [described below](#how-keys-are-encoded-and-messages-signed)
  2. Construct a `PublicKey` protobuf message, setting the `Data` field to the encoded public key bytes, and also setting the correct `Type` field.
  3. Serialize the protobuf containing the public key into bytes using the [canonical protobuf encoding](https://developers.google.com/protocol-buffers/docs/encoding).
  4. If the length of the serialized bytes <= 42, then we compute the "identity" multihash of the serialized bytes.  In other words, no hashing is performed, but the [multihash format is still followed](https://github.com/multiformats/multihash) (byte plus varint plus serialized bytes).  The idea here is that if the serialized byte array is short enough, we can fit it in a multihash verbatim without having to condense it using a hash function.
  5. If the length is >42, then we hash it using it using the SHA256 multihash.

### Note about deterministic encoding

Deterministic encoding of the `PublicKey` message is desirable, as it ensures
the same public key will always result in the same peer id.

The Protobuf specification does not provide sufficient guidance to ensure
deterministic serialization of messages. Specifically, there are no guarantees
about field ordering, and it's possible to add any number of unknown fields to a
message.

A future revision to this spec may define a canonical encoding that is more
strict than the Protobuf encoding spec.

In the meantime, implementors SHOULD use a protobuf encoder that orders fields
by their field number. This is the default behavior in many protobuf encoders,
but should be verified before committing to an implementation.

Additionally, implementors MUST avoid extending the `PublicKey` message with
additional fields, as the ordering of unknown fields is currently undefined
behavior.

### String representation

Peer Ids are [multihashes][multihash] represented with [CIDs](https://github.com/ipld/cid) when encoded into strings.

CID is a multihash with a prefix that specifies things like base encoding, cid version and the type of data behind it:

```
<cidv1> ::= <multibase><cid-version><multicodec><multihash>
```

Encoding and decoding of string representation must follow [CID spec][cid-decoding].

#### libp2p-key CID

The canonical string representation of a Peer Id is a CID v1  
with `base32` [multibase][multibase] ([RFC4648](https://tools.ietf.org/html/rfc4648), without padding) and `libp2p-key` [multicodec][multicodec]:

| multibase | cid version |  multicodec  |
| --------- | ----------- | ------------ |
|  `base32` |         `1` | `libp2p-key` |

- `libp2p-key` multicodec is mandatory when serializing to text (ensures Peer Id is self-describing)
- `base32`  is the default multibase encoding: projects are free to use a different one if it is more suited to their needs

Examples:

- SHA256 Peer Id encoded as canonical [CIDv1][cid-versions]:   
  `bafzbeie5745rpv2m6tjyuugywy4d5ewrqgqqhfnf445he3omzpjbx5xqxe` ([inspect](http://cid.ipfs.io/#bafzbeie5745rpv2m6tjyuugywy4d5ewrqgqqhfnf445he3omzpjbx5xqxe))
- Peer Ids that do not start with a valid multibase prefix are assumed to be legacy [CIDv0][cid-versions]
(a multihash with implicit  [`base58btc`][base58btc] encoding, without any prefix).
An example of the same Peer Id as a legacy CIDv0: `QmYyQSo1c1Ym7orWxLYvCrM2EmxFTANf8wXmmE7DWjhx5N`


[multihash]: https://github.com/multiformats/multihash
[multicodec]: https://github.com/multiformats/multicodec
[multibase]: https://github.com/multiformats/multibase
[base58btc]: https://en.bitcoinwiki.org/wiki/Base58#Alphabet_Base58
[cid-decoding]: https://github.com/multiformats/cid#decoding-algorithm
[cid-versions]: https://github.com/multiformats/cid#versions

## How Keys are Encoded and Messages Signed

Four key types are supported:
 - RSA
 - Ed25519
 - Secp256k1
 - ECDSA

Implementations MUST support RSA and Ed25519. Implementations MAY support Secp256k1 and ECDSA, but nodes using those keys may not be able to connect to all other nodes.

In all cases, implementation MAY allow the user to enable/disable specific key types via configuration.
Note that disabling support for compulsory key types may hinder connectivity.

Keys are encoded into byte arrays and serialized into the `Data` field of the
protobuf messages described above.

The following sections describe each key type's encoding rules.

libp2p implementations MUST use the encoding described below when embedding
keys into the `PublicKey` and `PrivateKey` messages described above, whether
for transmission, Peer Id generation, or storage.

Implementations can use whatever in-memory representation is convenient,
provided the encodings described below are used at the "I/O boundary".

In addition to key encodings, the sections below cover the signing method used
when signing and verifying messages with each key type.

### RSA

We encode the public key using the DER-encoded PKIX format.

We encode the private key as a PKCS1 key using ASN.1 DER.

To sign a message, we first hash it with SHA-256 and then sign it using the [RSASSA-PKCS1-V1.5-SIGN](https://tools.ietf.org/html/rfc3447#section-8.2) method, as originally defined in [RSA PKCS#1 v1.5](https://tools.ietf.org/html/rfc2313).

### Ed25519

Ed25519 specifies the exact format for keys and signatures, so we do not do much additional encoding, except as noted below.

We do not do any special additional encoding for Ed25519 public keys.

The encoding for Ed25519 private keys is a little unusual. There are two formats that we encourage implementors to support:

 - Preferred method is a simple concatenation:  `[private key bytes][public key bytes]` (64 bytes)
 - Older versions of the libp2p code used the following format:  `[private key][public key][public key]` (96 bytes).  If you encounter this type of encoding, the proper way to process it is to compare the two public key strings (32 bytes each) and verify they are identical.  If they are, then proceed as you would with the preferred method.  If they do not match, reject or error out because the byte array is invalid.

Ed25519 signatures follow the normal [Ed25519 standard](https://tools.ietf.org/html/rfc8032#section-5.1).

### Secp256k1

We use the standard Bitcoin EC encoding for Secp256k1 public and private keys.

To sign a message, we hash the message with SHA 256, then sign it using the standard [Bitcoin EC signature algorithm (BIP0062)](https://github.com/bitcoin/bips/blob/master/bip-0062.mediawiki), and then use [standard Bitcoin encoding](https://github.com/bitcoin/bips/blob/master/bip-0062.mediawiki#der-encoding).

### ECDSA

We encode the public key using ASN.1 DER.

We encode the private key using DER-encoded PKIX.

To sign a message, we hash the message with SHA 256, and then sign it with the [ECDSA standard algorithm](https://tools.ietf.org/html/rfc6979), then we encode it using [DER-encoded ASN.1.](https://wiki.openssl.org/index.php/DER)
