# Peer Ids and Keys

| Lifecycle Stage | Maturity Level | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 3A              | Recommendation | Active | r2, 2021-04-30  |

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

Key encodings and message signing semantics are covered below.

## Keys

Libp2p encodes keys in a [protobuf](https://github.com/libp2p/go-libp2p/blob/master/core/crypto/pb/crypto.proto)
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

Implementations MUST support Ed25519. Implementations SHOULD support RSA if they wish to
interoperate with the mainline IPFS DHT and the default IPFS bootstrap nodes. Implementations MAY
support Secp256k1 and ECDSA, but nodes using those keys may not be able to connect to all other
nodes.

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

### Test vectors

The following test vectors are hex-encoded bytes of the above described protobuf encoding.
The provided public key belongs to the private key.
Implementations SHOULD check that they can produce the provided public key from the private key.

| Key                   | bytes                                                                                                                                                                                                                                                      |
|-----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ECDSA private key     | 08031279307702010104203E5B1FE9712E6C314942A750BD67485DE3C1EFE85B1BFB520AE8F9AE3DFA4A4CA00A06082A8648CE3D030107A14403420004DE3D300FA36AE0E8F5D530899D83ABAB44ABF3161F162A4BC901D8E6ECDA020E8B6D5F8DA30525E71D6851510C098E5C47C646A597FB4DCEC034E9F77C409E62 |
| ECDSA public key      | 0803125b3059301306072a8648ce3d020106082a8648ce3d03010703420004de3d300fa36ae0e8f5d530899d83abab44abf3161f162a4bc901d8e6ecda020e8b6d5f8da30525e71d6851510c098e5c47c646a597fb4dcec034e9f77c409e62                                                             |
| ED25519 private key   | 080112407e0830617c4a7de83925dfb2694556b12936c477a0e1feb2e148ec9da60fee7d1ed1e8fae2c4a144b8be8fd4b47bf3d3b34b871c3cacf6010f0e42d474fce27e                                                                                                                   |
| ED25519 public key    | 080112201ed1e8fae2c4a144b8be8fd4b47bf3d3b34b871c3cacf6010f0e42d474fce27e                                                                                                                                                                                   |
| secp256k1 private key | 0802122053DADF1D5A164D6B4ACDB15E24AA4C5B1D3461BDBD42ABEDB0A4404D56CED8FB                                                                                                                                                                                   |
| secp256k1 public key  | 08021221037777e994e452c21604f91de093ce415f5432f701dd8cd1a7a6fea0e630bfca99                                                                                                                                                                                 |
| rsa private key | 080012ae123082092a0201000282020100e1beab071d08200bde24eef00d049449b07770ff9910257b2d7d5dda242ce8f0e2f12e1af4b32d9efd2c090f66b0f29986dbb645dae9880089704a94e5066d594162ae6ee8892e6ec70701db0a6c445c04778eb3de1293aa1a23c3825b85c6620a2bc3f82f9b0c309bc0ab3aeb1873282bebd3da03c33e76c21e9beb172fd44c9e43be32e2c99827033cf8d0f0c606f4579326c930eb4e854395ad941256542c793902185153c474bed109d6ff5141ebf9cd256cf58893a37f83729f97e7cb435ec679d2e33901d27bb35aa0d7e20561da08885ef0abbf8e2fb48d6a5487047a9ecb1ad41fa7ed84f6e3e8ecd5d98b3982d2a901b4454991766da295ab78822add5612a2df83bcee814cf50973e80d7ef38111b1bd87da2ae92438a2c8cbcc70b31ee319939a3b9c761dbc13b5c086d6b64bf7ae7dacc14622375d92a8ff9af7eb962162bbddebf90acb32adb5e4e4029f1c96019949ecfbfeffd7ac1e3fbcc6b6168c34be3d5a2e5999fcbb39bba7adbca78eab09b9bc39f7fa4b93411f4cc175e70c0a083e96bfaefb04a9580b4753c1738a6a760ae1afd851a1a4bdad231cf56e9284d832483df215a46c1c21bdf0c6cfe951c18f1ee4078c79c13d63edb6e14feaeffabc90ad317e4875fe648101b0864097e998f0ca3025ef9638cd2b0caecd3770ab54a1d9c6ca959b0f5dcbc90caeefc4135baca6fd475224269bbe1b02030100010282020100a472ffa858efd8588ce59ee264b957452f3673acdf5631d7bfd5ba0ef59779c231b0bc838a8b14cae367b6d9ef572c03c7883b0a3c652f5c24c316b1ccfd979f13d0cd7da20c7d34d9ec32dfdc81ee7292167e706d705efde5b8f3edfcba41409e642f8897357df5d320d21c43b33600a7ae4e505db957c1afbc189d73f0b5d972d9aaaeeb232ca20eebd5de6fe7f29d01470354413cc9a0af1154b7af7c1029adcd67c74b4798afeb69e09f2cb387305e73a1b5f450202d54f0ef096fe1bde340219a1194d1ac9026e90b366cce0c59b239d10e4888f52ca1780824d39ae01a6b9f4dd6059191a7f12b2a3d8db3c2868cd4e5a5862b8b625a4197d52c6ac77710116ebd3ced81c4d91ad5fdfbed68312ebce7eea45c1833ca3acf7da2052820eacf5c6b07d086dabeb893391c71417fd8a4b1829ae2cf60d1749d0e25da19530d889461c21da3492a8dc6ccac7de83ac1c2185262c7473c8cc42f547cc9864b02a8073b6aa54a037d8c0de3914784e6205e83d97918b944f11b877b12084c0dd1d36592f8a4f8b8da5bb404c3d2c079b22b6ceabfbcb637c0dbe0201f0909d533f8bf308ada47aee641a012a494d31b54c974e58b87f140258258bb82f31692659db7aa07e17a5b2a0832c24e122d3a8babcc9ee74cbb07d3058bb85b15f6f6b2674aba9fd34367be9782d444335fbed31e3c4086c652597c27104938b47fa10282010100e9fdf843c1550070ca711cb8ff28411466198f0e212511c3186623890c0071bf6561219682fe7dbdfd81176eba7c4faba21614a20721e0fcd63768e6d925688ecc90992059ac89256e0524de90bf3d8a052ce6a9f6adafa712f3107a016e20c80255c9e37d8206d1bc327e06e66eb24288da866b55904fd8b59e6b2ab31bc5eab47e597093c63fab7872102d57b4c589c66077f534a61f5f65127459a33c91f6db61fc431b1ae90be92b4149a3255291baf94304e3efb77b1107b5a3bda911359c40a53c347ff9100baf8f36dc5cd991066b5bdc28b39ed644f404afe9213f4d31c9d4e40f3a5f5e3c39bebeb244e84137544e1a1839c1c8aaebf0c78a7fad590282010100f6fa1f1e6b803742d5490b7441152f500970f46feb0b73a6e4baba2aaf3c0e245ed852fc31d86a8e46eb48e90fac409989dfee45238f97e8f1f8e83a136488c1b04b8a7fb695f37b8616307ff8a8d63e8cfa0b4fb9b9167ffaebabf111aa5a4344afbabd002ae8961c38c02da76a9149abdde93eb389eb32595c29ba30d8283a7885218a5a9d33f7f01dbdf85f3aad016c071395491338ec318d39220e1c7bd69d3d6b520a13a30d745c102b827ad9984b0dd6aed73916ffa82a06c1c111e7047dcd2668f988a0570a71474992eecf416e068f029ec323d5d635fd24694fc9bf96973c255d26c772a95bf8b7f876547a5beabf86f06cd21b67994f944e7a5493028201010095b02fd30069e547426a8bea58e8a2816f33688dac6c6f6974415af8402244a22133baedf34ce499d7036f3f19b38eb00897c18949b0c5a25953c71aeeccfc8f6594173157cc854bd98f16dffe8f28ca13b77eb43a2730585c49fc3f608cd811bb54b03b84bddaa8ef910988567f783012266199667a546a18fd88271fbf63a45ae4fd4884706da8befb9117c0a4d73de5172f8640b1091ed8a4aea3ed4641463f5ff6a5e3401ad7d0c92811f87956d1fd5f9a1d15c7f3839a08698d9f35f9d966e5000f7cb2655d7b6c4adcd8a9d950ea5f61bb7c9a33c17508f9baa313eecfee4ae493249ebe05a5d7770bbd3551b2eeb752e3649e0636de08e3d672e66cb90282010100ad93e4c31072b063fc5ab5fe22afacece775c795d0efdf7c704cfc027bde0d626a7646fc905bb5a80117e3ca49059af14e0160089f9190065be9bfecf12c3b2145b211c8e89e42dd91c38e9aa23ca73697063564f6f6aa6590088a738722df056004d18d7bccac62b3bafef6172fc2a4b071ea37f31eff7a076bcab7dd144e51a9da8754219352aef2c73478971539fa41de4759285ea626fa3c72e7085be47d554d915bbb5149cb6ef835351f231043049cd941506a034bf2f8767f3e1e42ead92f91cb3d75549b57ef7d56ac39c2d80d67f6a2b4ca192974bfc5060e2dd171217971002193dba12e7e4133ab201f07500a90495a38610279b13a48d54f0c99028201003e3a1ac0c2b67d54ed5c4bbe04a7db99103659d33a4f9d35809e1f60c282e5988dddc964527f3b05e6cc890eab3dcb571d66debf3a5527704c87264b3954d7265f4e8d2c637dd89b491b9cf23f264801f804b90454d65af0c4c830d1aef76f597ef61b26ca857ecce9cb78d4f6c2218c00d2975d46c2b013fbf59b750c3b92d8d3ed9e6d1fd0ef1ec091a5c286a3fe2dead292f40f380065731e2079ebb9f2a7ef2c415ecbb488da98f3a12609ca1b6ec8c734032c8bd513292ff842c375d4acd1b02dfb206b24cd815f8e2f9d4af8e7dea0370b19c1b23cc531d78b40e06e1119ee2e08f6f31c6e2e8444c568d13c5d451a291ae0c9f1d4f27d23b3a00d60ad |
| rsa public key | 080012a60430820222300d06092a864886f70d01010105000382020f003082020a0282020100e1beab071d08200bde24eef00d049449b07770ff9910257b2d7d5dda242ce8f0e2f12e1af4b32d9efd2c090f66b0f29986dbb645dae9880089704a94e5066d594162ae6ee8892e6ec70701db0a6c445c04778eb3de1293aa1a23c3825b85c6620a2bc3f82f9b0c309bc0ab3aeb1873282bebd3da03c33e76c21e9beb172fd44c9e43be32e2c99827033cf8d0f0c606f4579326c930eb4e854395ad941256542c793902185153c474bed109d6ff5141ebf9cd256cf58893a37f83729f97e7cb435ec679d2e33901d27bb35aa0d7e20561da08885ef0abbf8e2fb48d6a5487047a9ecb1ad41fa7ed84f6e3e8ecd5d98b3982d2a901b4454991766da295ab78822add5612a2df83bcee814cf50973e80d7ef38111b1bd87da2ae92438a2c8cbcc70b31ee319939a3b9c761dbc13b5c086d6b64bf7ae7dacc14622375d92a8ff9af7eb962162bbddebf90acb32adb5e4e4029f1c96019949ecfbfeffd7ac1e3fbcc6b6168c34be3d5a2e5999fcbb39bba7adbca78eab09b9bc39f7fa4b93411f4cc175e70c0a083e96bfaefb04a9580b4753c1738a6a760ae1afd851a1a4bdad231cf56e9284d832483df215a46c1c21bdf0c6cfe951c18f1ee4078c79c13d63edb6e14feaeffabc90ad317e4875fe648101b0864097e998f0ca3025ef9638cd2b0caecd3770ab54a1d9c6ca959b0f5dcbc90caeefc4135baca6fd475224269bbe1b0203010001 |

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
5. If the length is greater than 42, then hash it using the SHA256
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
  ([inspect](http://cid.ipfs.tech/#bafzbeie5745rpv2m6tjyuugywy4d5ewrqgqqhfnf445he3omzpjbx5xqxe)).
- `QmYyQSo1c1Ym7orWxLYvCrM2EmxFTANf8wXmmE7DWjhx5N` -- Peer ID (sha256) encoded as a raw base58btc multihash.
- `12D3KooWD3eckifWpRn9wQpMG9R9hX3sD158z7EqHWmweQAJU5SA` -- Peer ID (ed25519, using the "identity" multihash) encoded as a raw base58btc multihash.

[multihash]: https://github.com/multiformats/multihash
[multicodec]: https://github.com/multiformats/multicodec
[multibase]: https://github.com/multiformats/multibase
[base58btc]: https://en.bitcoinwiki.org/wiki/Base58#Alphabet_Base58
[cid]: https://github.com/multiformats/cid
[cid-decoding]: https://github.com/multiformats/cid#decoding-algorithm
[protobuf-encoding]: https://developers.google.com/protocol-buffers/docs/encoding
