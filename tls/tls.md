# libp2p TLS Handshake  <!-- omit in toc -->

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 3A              | Recommendation | Active | r0, 2019-03-23  |

Authors: [@marten-seemann]

Interest Group: [@Stebalien], [@jacobheun], [@raulk], [@Kubuxu], [@yusefnapora]

[@marten-seemann]: https://github.com/marten-seemann
[@Stebalien]: https://github.com/Stebalien
[@jacobheun]: https://github.com/jacobheun
[@raulk]: https://github.com/raulk
[@Kubuxu]: https://github.com/Kubuxu
[@yusefnapora]: https://github.com/yusefnapora


See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Table of Contents  <!-- omit in toc -->

- [Introduction](#introduction)
- [Handshake Protocol](#handshake-protocol)
- [Peer Authentication](#peer-authentication)
  - [libp2p Public Key Extension](#libp2p-public-key-extension)
- [ALPN](#alpn)
- [Inlined Muxer Negotiation](#inlined-muxer-negotiation)
- [Test vectors](#test-vectors)
  - [1. Valid certificate authenticating an ED25519 Peer ID](#1-valid-certificate-authenticating-an-ed25519-peer-id)
  - [2. Valid certificate authenticating an ECDSA Peer ID](#2-valid-certificate-authenticating-an-ecdsa-peer-id)
  - [3. Valid certificate authenticating a secp256k1 Peer ID](#3-valid-certificate-authenticating-a-secp256k1-peer-id)
  - [4. Invalid certificate](#4-invalid-certificate)
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
```

How the public key is encoded into the `Data` bytes depends on the Key Type.
- `Ed25519`: Only the 32 bytes of the public key
- `Secp256k1`: Only the compressed form of the public key. 33 bytes.
- The rest of the keys are encoded as a [SubjectPublicKeyInfo structure](https://www.rfc-editor.org/rfc/rfc5280.html#section-4.1) in PKIX, ASN.1 DER form.

## ALPN

"libp2p" is used as the application protocol for [ALPN](https://en.wikipedia.org/wiki/Application-Layer_Protocol_Negotiation).

The server MUST abort the handshake if it doesn't support any of the application protocols offered by the client.

## Inlined Muxer Negotiation

See [Multiplexer Negotiation over TLS](../connections/inlined-muxer-negotiation.md#multiplexer-negotiation-over-tls).

## Test vectors

The following items present test vectors that a compatible implementation should pass.
Due to the randomness required when signing certificates, it is hard to provide testcases for generating certificates.
These test cases verify that implementations can correctly parse certificates with all key types.
Implementations are encouraged to also perform roundtrip tests on their own certificate generation.

All certificates in these testcases are HEX encoded.

### 1. Valid certificate authenticating an ED25519 Peer ID

Certificate:
```
308201ae30820156a0030201020204499602d2300a06082a8648ce3d040302302031123010060355040a13096c69627032702e696f310a300806035504051301313020170d3735303130313133303030305a180f34303936303130313133303030305a302031123010060355040a13096c69627032702e696f310a300806035504051301313059301306072a8648ce3d020106082a8648ce3d030107034200040c901d423c831ca85e27c73c263ba132721bb9d7a84c4f0380b2a6756fd601331c8870234dec878504c174144fa4b14b66a651691606d8173e55bd37e381569ea37c307a3078060a2b0601040183a25a0101046a3068042408011220a77f1d92fedb59dddaea5a1c4abd1ac2fbde7d7b879ed364501809923d7c11b90440d90d2769db992d5e6195dbb08e706b6651e024fda6cfb8846694a435519941cac215a8207792e42849cccc6cd8136c6e4bde92a58c5e08cfd4206eb5fe0bf909300a06082a8648ce3d0403020346003043021f50f6b6c52711a881778718238f650c9fb48943ae6ee6d28427dc6071ae55e702203625f116a7a454db9c56986c82a25682f7248ea1cb764d322ea983ed36a31b77
```

PeerId: `12D3KooWM6CgA9iBFZmcYAHA6A2qvbAxqfkmrYiRQuz3XEsk4Ksv`

### 2. Valid certificate authenticating an ECDSA Peer ID

Certificate:
```
308201f63082019da0030201020204499602d2300a06082a8648ce3d040302302031123010060355040a13096c69627032702e696f310a300806035504051301313020170d3735303130313133303030305a180f34303936303130313133303030305a302031123010060355040a13096c69627032702e696f310a300806035504051301313059301306072a8648ce3d020106082a8648ce3d030107034200040c901d423c831ca85e27c73c263ba132721bb9d7a84c4f0380b2a6756fd601331c8870234dec878504c174144fa4b14b66a651691606d8173e55bd37e381569ea381c23081bf3081bc060a2b0601040183a25a01010481ad3081aa045f0803125b3059301306072a8648ce3d020106082a8648ce3d03010703420004bf30511f909414ebdd3242178fd290f093a551cf75c973155de0bb5a96fedf6cb5d52da7563e794b512f66e60c7f55ba8a3acf3dd72a801980d205e8a1ad29f2044730450220064ea8124774caf8f50e57f436aa62350ce652418c019df5d98a3ac666c9386a022100aa59d704a931b5f72fb9222cb6cc51f954d04a4e2e5450f8805fe8918f71eaae300a06082a8648ce3d04030203470030440220799395b0b6c1e940a7e4484705f610ab51ed376f19ff9d7c16757cfbf61b8d4302206205c03fbb0f95205c779be86581d3e31c01871ad5d1f3435bcf375cb0e5088a
```

PeerId: `QmfXbAwNjJLXfesgztEHe8HwgVDCMMpZ9Eax1HYq6hn9uE`

### 3. Valid certificate authenticating a secp256k1 Peer ID

Certificate:
```
308201ba3082015fa0030201020204499602d2300a06082a8648ce3d040302302031123010060355040a13096c69627032702e696f310a300806035504051301313020170d3735303130313133303030305a180f34303936303130313133303030305a302031123010060355040a13096c69627032702e696f310a300806035504051301313059301306072a8648ce3d020106082a8648ce3d030107034200040c901d423c831ca85e27c73c263ba132721bb9d7a84c4f0380b2a6756fd601331c8870234dec878504c174144fa4b14b66a651691606d8173e55bd37e381569ea38184308181307f060a2b0601040183a25a01010471306f0425080212210206dc6968726765b820f050263ececf7f71e4955892776c0970542efd689d2382044630440220145e15a991961f0d08cd15425bb95ec93f6ffa03c5a385eedc34ecf464c7a8ab022026b3109b8a3f40ef833169777eb2aa337cfb6282f188de0666d1bcec2a4690dd300a06082a8648ce3d0403020349003046022100e1a217eeef9ec9204b3f774a08b70849646b6a1e6b8b27f93dc00ed58545d9fe022100b00dafa549d0f03547878338c7b15e7502888f6d45db387e5ae6b5d46899cef0
```

PeerId: `16Uiu2HAkutTMoTzDw1tCvSRtu6YoixJwS46S1ZFxW8hSx9fWHiPs`

### 4. Invalid certificate

This certificate has a mismatch between the Peer ID that it claims to authenticate vs the key that was used to sign it.

Certificate:
```
308201f73082019da0030201020204499602d2300a06082a8648ce3d040302302031123010060355040a13096c69627032702e696f310a300806035504051301313020170d3735303130313133303030305a180f34303936303130313133303030305a302031123010060355040a13096c69627032702e696f310a300806035504051301313059301306072a8648ce3d020106082a8648ce3d030107034200040c901d423c831ca85e27c73c263ba132721bb9d7a84c4f0380b2a6756fd601331c8870234dec878504c174144fa4b14b66a651691606d8173e55bd37e381569ea381c23081bf3081bc060a2b0601040183a25a01010481ad3081aa045f0803125b3059301306072a8648ce3d020106082a8648ce3d03010703420004bf30511f909414ebdd3242178fd290f093a551cf75c973155de0bb5a96fedf6cb5d52da7563e794b512f66e60c7f55ba8a3acf3dd72a801980d205e8a1ad29f204473045022100bb6e03577b7cc7a3cd1558df0da2b117dfdcc0399bc2504ebe7de6f65cade72802206de96e2a5be9b6202adba24ee0362e490641ac45c240db71fe955f2c5cf8df6e300a06082a8648ce3d0403020348003045022100e847f267f43717358f850355bdcabbefb2cfbf8a3c043b203a14788a092fe8db022027c1d04a2d41fd6b57a7e8b3989e470325de4406e52e084e34a3fd56eef0d0df
```

## Future Extensibility

Future versions of this handshake protocol MAY use the Server Name Indication (SNI) in the `ClientHello` as defined in [RFC 6066, section 3](https://tools.ietf.org/html/rfc6066) to announce their support for other versions.

In order to keep this flexibility for future versions, clients that only support the version of the handshake defined in this document MUST NOT send any value in the Server Name Indication. Servers that support only this version MUST ignore this field if present.
