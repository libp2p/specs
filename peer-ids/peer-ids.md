# Spec: Peer Ids and Keys

Status: **DRAFT**

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

#### Where it's used?

Keys are used in two places in libp2p.  The first is for signing messages.  Here are some examples of messages we sign:
 - IPNS records
 - PubSub messages
 - SECIO handshake

The second is for generating peer ids; this is discussed in the section below.

## Peer Ids

Here is the process by which we generate peer id's based on the public/private keypairs described above:

  1. Encode the public key into the protobuf.
  2. Serialize the protobuf containing the public key into bytes using the [canonical protobuf encoding](https://developers.google.com/protocol-buffers/docs/encoding).
  3.  If the length of the serialized bytes <= 42, then we compute the "identity" multihash of the serialized bytes.  In other words, no hashing is performed, but the [multihash format is still followed](https://github.com/multiformats/multihash) (byte plus varint plus serialized bytes).  The idea here is that if the serialized byte array is short enough, we can fit it in a multihash verbatim without having to condense it using a hash function.
  4. If the length is >42, then we hash it using it using the SHA256 multihash.

Peer Ids are multihashes, and they are often encoded into strings.
The canonical string representation of a Peer Id is a base58 encoding with
[the alphabet used by bitcoin](https://en.bitcoinwiki.org/wiki/Base58#Alphabet_Base58).
This encoding is sometimes abbreviated as `base58btc`.

An example of a `base58btc` encoded SHA256 peer id: `QmYyQSo1c1Ym7orWxLYvCrM2EmxFTANf8wXmmE7DWjhx5N`.

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
