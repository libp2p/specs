# Spec:  Peer Ids and Keys

## Keys

Keys are serialized for transmission using a
[simple protobuf](https://github.com/libp2p/go-libp2p-crypto/blob/master/pb/crypto.proto#L5):

```protobuf
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
```

This proto simply encodes for transmission a public key along with an enum specifying the type of key. The specific format of the `Data` field depends on the key type, and is [described below](#how-keys-are-encoded-and-messages-signed).

#### Where it's used?

Keys are used in two places in libp2p.  The first is for signing messages.  Here are some examples of messages we sign:
 - IPNS records
 - PubSub messages (coming soon)
 - SECIO handshake

The second is for generating peer ids; this is discussed in the section below.

## Peer Ids

Here is the process by which we generate peer ids based on the public keys described above:

  1. Encode the public key into the protobuf.
  2. Serialize the protobuf containing the public key into bytes using the [canonical protobuf encoding](https://developers.google.com/protocol-buffers/docs/encoding).
  3.  If the length of the serialized bytes <= 42, then we compute the "identity" multihash of the serialized bytes.  In other words, no hashing is performed, but the [multihash format is still followed](https://github.com/multiformats/multihash) (byte plus varint plus serialized bytes).  The idea here is that if the serialized byte array is short enough, we can fit it in a multihash proto without having to condense it using a hash function.
  4. If the length is >42, then we hash it using it using the SHA256 multihash.

Peer Ids are multihashes, and they are often encoded into strings, most commonly using a base58 encoding with the alphabet used by bitcoin (`base58btc`).
An example of a `base58btc` encoded SHA256 peer id: `QmYyQSo1c1Ym7orWxLYvCrM2EmxFTANf8wXmmE7DWjhx5N`.

## How Keys are Encoded and Messages Signed

Four key types are supported:
 - RSA
 - Ed25519
 - Secp256k1
 - ECDSA

Implementations SHOULD support RSA and Ed25519. Implementations MAY support Secp256k1 and ECDSA, but nodes using those keys may not be able to connect to all other nodes.

Keys are passed around in code as byte arrays.  Keys are encoded within these arrays differently depending on the type of key.  

The following sections describe each key type's encoding rules.

### RSA

We encode the public key using the DER-encoded PKIX format.

To sign a message, we first hash it with SHA-256 and then sign it using the [RSASSA-PKCS1-V1.5-SIGN](https://tools.ietf.org/html/rfc3447#section-8.2) method, as originally defined in [RSA PKCS#1 v1.5](https://tools.ietf.org/html/rfc2313).

### Ed25519

Ed25519 specifies the exact format for keys and signatures, so we do not do any additional encoding for the public key.
Ed25519 signatures follow the normal [Ed25519 standard](https://tools.ietf.org/html/rfc8032#section-5.1).

### Secp256k1

We use the standard Bitcoin EC encoding for Secp256k1 public keys.

To sign a message, we hash the message with SHA 256, then sign it using the standard [Bitcoin EC signature algorithm (BIP0062)](https://github.com/bitcoin/bips/blob/master/bip-0062.mediawiki), and then use [standard Bitcoin encoding](https://github.com/bitcoin/bips/blob/master/bip-0062.mediawiki#der-encoding).

### ECDSA

We encode the public key using ASN.1 DER.

To sign a message, we hash the message with SHA 256, and then sign it with the [ECDSA standard algorithm](https://tools.ietf.org/html/rfc6979), then we encode it using [DER-encoded ASN.1.](https://wiki.openssl.org/index.php/DER)
