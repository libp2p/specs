# Spec:  Peer Ids and Keys

## Keys


Our key pairs are stored on disk using a simple protobuf defined in [libp2p/go-libp2p-crypto/pb/crypto.proto#L5](https://github.com/libp2p/go-libp2p-crypto/blob/master/pb/crypto.proto#L5):

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

message PrivateKey {
	required KeyType Type = 1;
	required bytes Data = 2;
}
```

As should be apparent from the above code block, this proto simply encodes for transmission a public/private key pair along with an enum specifying the type of keypair.

#### Where it's used?

Keys are used in two places in libp2p.  The first is for signing messages.  Here are some examples of messages we sign:
 - IPNS records
 - PubSub messages (coming soon)
 - SECIO handshake

The second is for generating peer ids; this is discussed in the section below.

## Peer Ids

Here is the process by which we generate peer id's based on the public/private keypairs described above:

  1. Encode the public key into the protobuf.
  2. Serialize the protobuf containing the public key into bytes using the [canonical protobuf encoding](https://developers.google.com/protocol-buffers/docs/encoding).
  3.  If the length of the serialized bytes <= 42, then we compute the "identity" multihash of the serialized bytes.  In other words, no hashing is performed, but the [multihash format is still followed](https://github.com/multiformats/multihash) (byte plus varint plus serialized bytes).  The idea here is that if the serialized byte array is short enough, we can fit it in a multihash proto without having to condense it using a hash function.
  4. If the length is >42, then we hash it using it using the SHA256 multihash.

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

We encode the private key as a PKCS1 key using ASN.1 DER.

To sign a message, we first hash it with SHA-256 and then sign it using the RSASSA-PKCS1-V1.5-SIGN from RSA PKCS#1 v1.5.

See [libp2p/go-libp2p-crypto/rsa.go](https://github.com/libp2p/go-libp2p-crypto/blob/master/rsa.go) for details

### Ed25519

Ed25519 specifies the exact format for keys and signatures, so we do not do much additional encoding, except as noted below.

We do not do any special additional encoding for Ed25519 public keys.

The encoding for Ed25519 private keys is a little unusual. There are two formats that we encourage implementors to support:

 - Preferred method is a simple concatenation:  `[private key bytes][public key bytes]` (64 bytes)
 - Older versions of the libp2p code used the following format:  `[private key][public key][public key]` (96 bytes).  If you encounter this type of encoding, the proper way to process it is to compare the two public key strings (32 bytes each) and verify they are identical.  If they are, then proceed as you would with the preferred method.  If they do not match, reject or error out because the byte array is invalid.

Ed25519 signatures follow the normal Ed25519 standard.

See [libp2p/go-libp2p-crypto/ed25519.go](https://github.com/libp2p/go-libp2p-crypto/blob/master/ed25519.go) for details

### Secp256k1

We use the standard Bitcoin EC encoding for Secp256k1 public and private keys.

To sign a message, we hash the message with SHA 256, then sign it using the standard Bitcoin EC signature algorithm (BIP0062), and then use standard Bitcoin encoding.

See [libp2p/go-libp2p-crypto/secp256k1.go](https://github.com/libp2p/go-libp2p-crypto/blob/master/secp256k1.go) for details.

### ECDSA

We encode the public key using ASN.1 DER.

We encode the private key using DER-encoded PKIX.

To sign a message, we hash the message with SHA 256, and then sign it with the ECDSA standard algorithm, then we encode it using DER-encoded ASN.1.

See [libp2p/go-libp2p-crypto/ecdsa.go](https://github.com/libp2p/go-libp2p-crypto/blob/master/ecdsa.go) for details.

