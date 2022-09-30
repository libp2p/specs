# libp2p TLS Handshake

| Lifecycle Stage | Maturity                 | Status | Latest Revision |
|-----------------|--------------------------|--------|-----------------|
| 2A              | Candidate Recommendation | Active | r0, 2019-03-23  |

Authors: [@marten-seemann]

Interest Group: [@Stebalien], [@jacobheun], [@raulk], [@Kubuxu], [@yusefnapora]

[@marten-seemann]: https://github.com/marten-seemann
[@Stebalien]: https://github.com/Stebalien
[@jacobheun]: https://github.com/jacobheun
[@raulk]: https://github.com/raulk
[@Kubuxu]: https://github.com/Kubuxu
[@yusefnapora]: https://github.com/yusefnapora


See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Table of Contents

- [libp2p TLS Handshake](#libp2p-tls-handshake)
    - [Table of Contents](#table-of-contents)
    - [Introduction](#introduction)
    - [Handshake Protocol](#handshake-protocol)
    - [Peer Authentication](#peer-authentication)
        - [libp2p Public Key Extension](#libp2p-public-key-extension)
    - [Test vectors](#test-vectors)
    - [Future Extensibility](#future-extensibility)

## Introduction

This document describes how [TLS 1.3](https://tools.ietf.org/html/rfc8446) is used to secure libp2p connections. Endpoints authenticate to their peers by encoding their public key into a X.509 certificate extension. The protocol described here allows peers to use arbitrary key types, not constrained to those for which signing of a X.509 certificates is specified.


## Handshake Protocol

The libp2p handshake uses TLS 1.3 (and higher). Endpoints MUST NOT negotiate lower TLS versions.

During the handshake, peers authenticate each other’s identity as described in [Peer Authentication](#peer-authentication). Endpoints MUST verify the peer's identity. Specifically, this means that servers MUST require client authentication during the TLS handshake, and MUST abort a connection attempt if the client fails to provide the requested authentication information.

When negotiating the usage of this handshake dynamically, via a protocol agreement mechanism like [multistream-select 1.0](https://github.com/libp2p/specs/blob/master/connections/README.md#multistream-select), it MUST be identified with the following protocol ID:

```
/tls/1.0.0
```

## Peer Authentication

In order to be able to use arbitrary key types, peers don’t use their host key to sign the X.509 certificate they send during the handshake. Instead, the host key is encoded into the [libp2p Public Key Extension](#libp2p-public-key-extension), which is carried in a self-signed certificate.

The key used to generate and sign this certificate SHOULD NOT be related to the host's key. Endpoints MAY generate a new key and certificate for every connection attempt, or they MAY reuse the same key and certificate for multiple connections.

Endpoints MUST choose a key that will allow the peer to verify the certificate (i.e. choose a signature algorithm that the peer supports), and SHOULD use a key type that (a) allows for efficient signature computation, and (b) reduces the combined size of the certificate and the signature. In particular, RSA SHOULD NOT be used unless no elliptic curve algorithms are supported.

Endpoints MUST NOT send a certificate chain that contains more than one certificate. The certificate MUST have `NotBefore` and `NotAfter` fields set such that the certificate is valid at the time it is received by the peer. When receiving the certificate chain, an endpoint MUST check these conditions and abort the connection attempt if (a) the presented certificate is not yet valid, OR (b) if it is expired. Endpoints MUST abort the connection attempt if more than one certificate is received, or if the certificate’s self-signature is not valid.

The certificate MUST contain the [libp2p Public Key Extension](#libp2p-public-key-extension). If this extension is missing, endpoints MUST abort the connection attempt. This extension MAY be marked critical. The certificate MAY contain other extensions. Implementations MUST ignore non-critical extensions with unknown OIDs. Endpoints MUST abort the connection attempt if the certificate contains critical extensions that the endpoint does not understand.

Certificates MUST omit the deprecated `subjectUniqueId` and `issuerUniqueId` fields. Endpoints MAY abort the connection attempt if either is present.

Certificates MUST use the `NamedCurve` encoding for elliptic curve parameters. Endpoints MUST abort the connection attempt if is not used. Failure to enforce this restriction allows [“Whose Curve Is It Anyway”](https://whosecurve.com) attacks, which completely compromise the security of the connection. Similarly, hash functions with an output length less than 256 bits MUST NOT be used, due to the possibility of collision attacks. In particular, MD5 and SHA1 MUST NOT be used.

Note for clients: Since clients complete the TLS handshake immediately after sending the certificate (and the TLS `ClientFinished` message), the handshake will appear as having succeeded before the server had the chance to verify the certificate. In this state, the client can already send application data. If certificate verification fails on the server side, the server will close the connection without processing any data that the client sent.

### libp2p Public Key Extension

In order to prove ownership of its host key, an endpoint sends two values:
- the public host key
- a signature performed using the private host key

The public host key allows the peer to calculate the peer ID of the peer it is connecting to. Clients MUST verify that the peer ID derived from the certificate matches the peer ID they intended to connect to, and MUST abort the connection if there is a mismatch.

The peer signs the concatenation of the string `libp2p-tls-handshake:` and the encoded public key that is used to generate the certificate carrying the libp2p Public Key Extension, using its private host key. The public key is encoded as a `SubjectPublicKeyInfo` structure as described in RFC 5280, Section 4.1:

```asn1
SubjectPublicKeyInfo ::= SEQUENCE {
  algorithm             AlgorithmIdentifier,
  subject_public_key    BIT STRING
}
AlgorithmIdentifier  ::= SEQUENCE {
  algorithm             OBJECT IDENTIFIER,
  parameters            ANY DEFINED BY algorithm OPTIONAL
}
```

This signature provides cryptographic proof that the peer was in possession of the private host key at the time the certificate was signed. Peers MUST verify the signature, and abort the connection attempt if signature verification fails.

The public host key and the signature are ANS.1-encoded into the SignedKey data structure, which is carried in the libp2p Public Key Extension. The libp2p Public Key Extension is a X.509 extension with the Object Identier `1.3.6.1.4.1.53594.1.1`, [allocated by IANA to the libp2p project at Protocol Labs](https://www.iana.org/assignments/enterprise-numbers/enterprise-numbers).

```asn1
SignedKey ::= SEQUENCE {
  publicKey OCTET STRING,
  signature OCTET STRING 
}
```

The publicKey field of `SignedKey` contains the public host key of the endpoint, encoded using the following protobuf:

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

How the public key is encoded into the `Data` bytes depends on the Key Type.
- `Ed25519`: Only the 32 bytes of the public key
- `Secp256k1`: Only the compressed form of the public key. 33 bytes.
- The rest of the keys are encoded as a [SubjectPublicKeyInfo structure](https://www.rfc-editor.org/rfc/rfc5280.html#section-4.1) in PKIX, ASN.1 DER form.

## Test vectors

The following items presents test vectors that a compatible implementation should pass.
All certificates are HEX encoded.

### 1. Valid certificate authenticating an ED25519 Peer ID

Certificate:
```
308201773082011ea003020102020900f5bd0debaa597f52300a06082a8648ce3d04030230003020170d3735303130313030303030305a180f34303936303130313030303030305a30003059301306072a8648ce3d020106082a8648ce3d030107034200046bf9871220d71dcb3483ecdfcbfcc7c103f8509d0974b3c18ab1f1be1302d643103a08f7a7722c1b247ba3876fe2c59e26526f479d7718a85202ddbe47562358a37f307d307b060a2b0601040183a25a01010101ff046a30680424080112207fda21856709c5ae12fd6e8450623f15f11955d384212b89f56e7e136d2e17280440aaa6bffabe91b6f30c35e3aa4f94b1188fed96b0ffdd393f4c58c1c047854120e674ce64c788406d1c2c4b116581fd7411b309881c3c7f20b46e54c7e6fe7f0f300a06082a8648ce3d040302034700304402207d1a1dbd2bda235ff2ec87daf006f9b04ba076a5a5530180cd9c2e8f6399e09d0220458527178c7e77024601dbb1b256593e9b96d961b96349d1f560114f61a87595
```

PeerId: `12D3KooWJRSrypvnpHgc6ZAgyCni4KcSmbV7uGRaMw5LgMKT18fq`

### 2. Valid certificate authenticating an ECDSA Peer ID

Certificate:
```
308201c030820166a003020102020900eaf419a6e3edb4a6300a06082a8648ce3d04030230003020170d3735303130313030303030305a180f34303936303130313030303030305a30003059301306072a8648ce3d020106082a8648ce3d030107034200048dbf1116c7c608d6d5292bd826c3feb53483a89fce434bf64538a359c8e07538ff71f6766239be6a146dcc1a5f3bb934bcd4ae2ae1d4da28ac68b4a20593f06ba381c63081c33081c0060a2b0601040183a25a01010101ff0481ae3081ab045f0803125b3059301306072a8648ce3d020106082a8648ce3d0301070342000484b93fa456a74bd0153919f036db7bc63c802f055bc7023395d0203de718ee0fc7b570b767cdd858aca6c7c4113ff002e78bd2138ac1a3b26dde3519e06979ad04483046022100bc84014cea5a41feabdf4c161096564b9ccf4b62fbef4fe1cd382c84e11101780221009204f086a84cb8ed8a9ddd7868dc90c792ee434adf62c66f99a08a5eba11615b300a06082a8648ce3d0403020348003045022054b437be9a2edf591312d68ff24bf91367ad4143f76cf80b5658f232ade820da022100e23b48de9df9c25d4c83ddddf75d2676f0b9318ee2a6c88a736d85eab94a912f
```

PeerId: `QmZcrvr3r4S3QvwFdae3c2EWTfo792Y14UpzCZurhmiWeX`

### 3. Valid certificate authenticating a secp256k1 Peer ID

Certificate:
```
3082018230820128a003020102020900f3b305f55622cfdf300a06082a8648ce3d04030230003020170d3735303130313030303030305a180f34303936303130313030303030305a30003059301306072a8648ce3d020106082a8648ce3d0301070342000458f7e9581748ff9bdd933b655cc0e5552a1248f840658cc221dec2186b5a2fe4641b86ab7590a3422cdbb1000cf97662f27e5910d7569f22feed8829c8b52e0fa38188308185308182060a2b0601040183a25a01010101ff0471306f042508021221026b053094d1112bce799dc8026040ae6d4eb574157929f1598172061f753d9b1b04463044022040712707e97794c478d93989aaa28ae1f71c03af524a8a4bd2d98424948a782302207b61b7f074b696a25fb9e0059141a811cccc4cc28042d9301b9b2a4015e87470300a06082a8648ce3d04030203480030450220143ae4d86fdc8675d2480bb6912eca5e39165df7f572d836aa2f2d6acfab13f8022100831d1979a98f0c4a6fb5069ca374de92f1a1205c962a6d90ad3d7554cb7d9df4
```

PeerId: `16Uiu2HAm2dSCBFxuge46aEt7U1oejtYuBUZXxASHqmcfVmk4gsbx`

### 4. Invalid certificate

This certificate has a mismatch between the Peer ID that it claims to authenticate vs the key that was used to sign it.

Certificate:
```
308201773082011da003020102020830a73c5d896a1109300a06082a8648ce3d04030230003020170d3735303130313030303030305a180f34303936303130313030303030305a30003059301306072a8648ce3d020106082a8648ce3d03010703420004bbe62df9a7c1c46b7f1f21d556deec5382a36df146fb29c7f1240e60d7d5328570e3b71d99602b77a65c9b3655f62837f8d66b59f1763b8c9beba3be07778043a37f307d307b060a2b0601040183a25a01010101ff046a3068042408011220ec8094573afb9728088860864f7bcea2d4fd412fef09a8e2d24d482377c20db60440ecabae8354afa2f0af4b8d2ad871e865cb5a7c0c8d3dbdbf42de577f92461a0ebb0a28703e33581af7d2a4f2270fc37aec6261fcc95f8af08f3f4806581c730a300a06082a8648ce3d040302034800304502202dfb17a6fa0f94ee0e2e6a3b9fb6e986f311dee27392058016464bd130930a61022100ba4b937a11c8d3172b81e7cd04aedb79b978c4379c2b5b24d565dd5d67d3cb3c
```

## Future Extensibility

Future versions of this handshake protocol MAY use the Server Name Indication (SNI) in the `ClientHello` as defined in [RFC 6066, section 3](https://tools.ietf.org/html/rfc6066) to announce their support for other versions.

In order to keep this flexibility for future versions, clients that only support the version of the handshake defined in this document MUST NOT send any value in the Server Name Indication. Servers that support only this version MUST ignore this field if present.
