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

## Test vectors

The following items present test vectors that a compatible implementation should pass.
Due to the randomness required when signing certificates, it is hard to provide testcases for generating certificates.
These test cases verify that implementations can correctly parse certificates with all key types.
Implementations are encouraged to also perform roundtrip tests on their own certificate generation.

All certificates in these testcases are HEX encoded.

### 1. Valid certificate authenticating an ED25519 Peer ID

Certificate:
```
308201b030820156a00302010202081ef0074922d196fd300a06082a8648ce3d040302301e311c301a06035504051313343337323333323535383639393632313939323020170d3235303332303130333033305a180f32313235303232343131333033305a301e311c301a06035504051313343337323333323535383639393632313939323059301306072a8648ce3d020106082a8648ce3d03010703420004799542bfc7bfb7506ecd6d78857796b30e4127c44716fc2caa40922cc578ec9367e5b748c748a3ae576786b9fddeca36f40f2cc883b101e937511bff41ab5232a37c307a3078060a2b0601040183a25a0101046a3068042408011220970ec193ab5f6c556009767d5cdc0477d257807b41468a6f2007b40f03034fc70440db02949ac1e19fa61632baafa30d565eca7c12e84f0fc4341ade332b5ccbac60640fdc59213399d913e6c3c0f1111f92f66f04ee20cfe8f16cecfb7b5ee59205300a06082a8648ce3d040302034800304502203d33964353d80f393415c993a6462d47c7dacc38147ee445953019786ea7b66d022100a693ade35c4edb786bdb0bd09f1cb0c9a5b0bc6b61a97b639b4e3334371e10aa
```

PeerId: `12D3KooWKz2nHY8tmcX7ziGsF3gBoUZVvCXcmkvn86DaBsGktZfc`

### 2. Valid certificate authenticating an ECDSA Peer ID

Certificate:
```
308201f63082019ca00302010202081052b953fab8f4be300a06082a8648ce3d040302301e311c301a06035504051313313931333134363939343730373431363038313020170d3235303332303130333033305a180f32313235303232343131333033305a301e311c301a06035504051313313931333134363939343730373431363038313059301306072a8648ce3d020106082a8648ce3d03010703420004c2fc1d082c85b90d8a82413b9b34f9c9c5f93f79e6d1eb954b5fdfe41b26fc9a4c44f32844eb40be9b4728a59ec966816a5394d3a0c1f06334b6debecb36f0aea381c13081be3081bb060a2b0601040183a25a01010481ac3081a9045f0803125b3059301306072a8648ce3d020106082a8648ce3d03010703420004d287ad3dc5c97884b7ab987b660efc2aa8cde7f9814e0fb3a8a005bfd8cd4a6cd2fd961d3e2013256b5b59e1ca6c9e7e48febfb1ed90cd092ef24aa0ae2d0dc404463044022021e1ccaf2f3c77fde5ada1242b830e7a5c1ab25956ac5edbca4904ec47a09479022051884dbdda561b545abf3fe391341898a4b4ceccccb83507b445ed36a6b2eedc300a06082a8648ce3d040302034800304502200f0fd126fb521ef8543655ccd3c32b1df34be8eb61ba4d30a04eebdb2870f2b0022100e97a637a3e702f360b45eb7567647c6a46f9d2a53291332a89898f3d84afc24e
```

PeerId: `Qmf5QwyriEdqphhFWkFJsmfY4Sgsj5Cq47VTa5RAboELhM`

### 3. Valid certificate authenticating a secp256k1 Peer ID

Certificate:
```
308201b83082015fa003020102020831c14b384686f89a300a06082a8648ce3d040302301e311c301a06035504051313313435373936393932373437313131393132373020170d3235303332303130333033305a180f32313235303232343131333033305a301e311c301a06035504051313313435373936393932373437313131393132373059301306072a8648ce3d020106082a8648ce3d03010703420004e5da66e6dc811fef90f2b7a77ec92f8f7a96942899dc31ce649058cff9f9504cbe2c70212b616daef3fb52afa7d75b1c7880f48fdf0565cb7809ffb656b3b540a38184308181307f060a2b0601040183a25a01010471306f04250802122102d5dd09fddbcc150de9cb92e1777d7712ba0e20f526c7a842cc5f134a966cda780446304402202ece49e25a4b743f6965c70fd7c6efcf9101909a12fe81f2df98a5fcc203e49b02206e16a72fa8d1375d6117db99a960c324fe02f54d0853ecc19dda23a4f40949f0300a06082a8648ce3d0403020347003044022022587f895d257d5cf66da1d1c3627910b858443cb887f405e1948dc3e55d80b902200e2f07b93a2e4a487bb4bc721e9431ae723f921d91f84a875758d787c4302fa8
```

PeerId: `16Uiu2HAm9pWJoENCPfqs3NxD58ujsoi8PNAVpDDJxfbuVHSWj1VZ`

### 4. Invalid certificate

This certificate has a mismatch between the Peer ID that it claims to authenticate vs the key that was used to sign it.

Certificate:
```
308201f83082019da00302010202081d051a136acdc4ea300a06082a8648ce3d040302301e311c301a06035504051313333037373732313536373332393634323238363020170d3235303332303130333830395a180f32313235303232343131333830395a301e311c301a06035504051313333037373732313536373332393634323238363059301306072a8648ce3d020106082a8648ce3d030107034200043168c3c9c49ec956c48446b64cc9c2c3d19eb7292ec8410ab9db14bef4946e5d14372ff5ae437b66b2fc724180bafeb8424a7bd4e119a02fcbbbabe039d9e6d7a381c23081bf3081bc060a2b0601040183a25a01010481ad3081aa045f0803125b3059301306072a8648ce3d020106082a8648ce3d03010703420004570acac25ebaaf7cc97c83858bff4c1bec26c9fdeb001b443c08cf26aee887099b36b73fa1aab6b3f729d8e9d8a7b789b5addcb79064769722a0da54cb4ceee804473045022100c253946d4c212698afb92095fdf281611f3fe7088f6cc1ccc71950509558459202206213b2c8fd07d53dc4554c54403116cb9d780d2fdd5b05c4447f1f187dbd26b6300a06082a8648ce3d0403020349003046022100c942bba92a2f3a1f639ae20c1c20e3bbea0f69d45c0ca67411a67c5ec71745f4022100896af401d8d137db9d075cb949b26c5808543540f3cf823352f53e920b5c7d55
```

## Future Extensibility

Future versions of this handshake protocol MAY use the Server Name Indication (SNI) in the `ClientHello` as defined in [RFC 6066, section 3](https://tools.ietf.org/html/rfc6066) to announce their support for other versions.

In order to keep this flexibility for future versions, clients that only support the version of the handshake defined in this document MUST NOT send any value in the Server Name Indication. Servers that support only this version MUST ignore this field if present.
