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
308201d83082017ea003020102021100a488d437a726243f2f3933fb76ac1260300a06082a8648ce3d040302301431123010060355040a13096c69627032702e696f301e170d3235303331393131353433315a170d3335303331373131353433315a301431123010060355040a13096c69627032702e696f3059301306072a8648ce3d020106082a8648ce3d0301070342000408cb1e75b43c328b0c68b732cce1264aeaba43691a02b49af3cdb255b2832b10882aeb0cc2579ebc8750a15ae93c96be04c8a3ed11811ba90edc4cd2186a7b5ba381b03081ad300e0603551d0f0101ff0404030205a030130603551d25040c300a06082b06010505070301300c0603551d130101ff040230003078060a2b0601040183a25a0101046a3068042408011220964412b781912b2cac807b9731d30201c0c17fccaf15363bf03458b4ed37b9120440fa19f2c89aed436e07ef860dc37a16e538b2714d4fbc95f2470d680bf04319de942108a7c61a23b8112715dd6a5db7846e0d8e2dfc0a11069f6691f0d4fa2c0c300a06082a8648ce3d040302034800304502210097c3c6887c2f4f4747f51a969e104ee3b66d4518bb42adeba13657954bc482b10220613a0a8726ef3c5453e1fe19a2e6fbb8cf6674c9d9480d210655b5416b57a939
```

PeerId: `12D3KooWKvwXZNS7Rabb9xZgscwidxjkCh6GgJCxvaYc2UekmKGu`

### 2. Valid certificate authenticating an ECDSA Peer ID

Certificate:
```
3082021d308201c3a0030201020210030a3d9ec63fa9699d9786225333e2e6300a06082a8648ce3d040302301431123010060355040a13096c69627032702e696f301e170d3235303331393131353433315a170d3335303331373131353433315a301431123010060355040a13096c69627032702e696f3059301306072a8648ce3d020106082a8648ce3d0301070342000443cb7e0ad4550054ce8aef3871ff1183280a801f359a62449e742616d4859acbf90e4c3549e91d30343d934d6c7ed5177fda747b05450109ac0c2bed4b774961a381f63081f3300e0603551d0f0101ff0404030205a030130603551d25040c300a06082b06010505070301300c0603551d130101ff040230003081bd060a2b0601040183a25a01010481ae3081ab045f0803125b3059301306072a8648ce3d020106082a8648ce3d03010703420004e4314d7937c72ffe3e32c86bf01ce5dbbba97f51b3ba1b92988dc055134e67192cc7c4a72957efc81ca1d6842568424661f51d645cf188b49dcb378ab2f3ad8804483046022100b7a863233201ee58c55303e3a295debb4494215fadf9fdae8d673ec77fdc9248022100c622e11fc3f22d7ab6b3fbdb2b4fcdc20ded5cf63903c4a203b28418ea8eee41300a06082a8648ce3d0403020348003045022100ca7a345bdb1c9729e741d34871ef68150f8cd4727d3328a9c45401e201bbc0350220712fc0a3ec3fca0e50d001049a0a4114d957ae111f4c911c3e54360d80aa7119
```

PeerId: `QmPt7GAt6b4cJE8qYWYUvBkSPxmhsVoqkSnbtkoKw8rsKr`

### 3. Valid certificate authenticating a secp256k1 Peer ID

Certificate:
```
308201dd30820184a00302010202102c9f34881912e91d916c813673fc268a300a06082a8648ce3d040302301431123010060355040a13096c69627032702e696f301e170d3235303331393131353433315a170d3335303331373131353433315a301431123010060355040a13096c69627032702e696f3059301306072a8648ce3d020106082a8648ce3d03010703420004accc9a0f5852fd73b02ec880c4cb2076cd37440ae24aee1eb4b3116311215f9ba0a3d86a4b12dbf04f0a08e8f4dd2cc0f515bcb86e4653e991e2f0efc0365886a381b73081b4300e0603551d0f0101ff0404030205a030130603551d25040c300a06082b06010505070301300c0603551d130101ff04023000307f060a2b0601040183a25a01010471306f0425080212210378067cceac4ac01ce5b03758ce4de591cec37080e434c3dd5e1cc62cd6da2831044630440220544b670a9d92b262714317f7f20f6afbd910d1573584fb672b0714bc2b8b195e02203d832f7f308e03a5a4d33fc4866af2044e9c69c459478ffb32b55ba7e7fad2a9300a06082a8648ce3d0403020347003044022048f1495b10b0ffcd8590600663bd63f7585b40c5f25ea65256e83410f3b12c6002202a37ba56922f953444e1128839a6c64681edcab6107b6fdc8e8a36172a95f842
```

PeerId: `16Uiu2HAmLjX1eVhPDcu5UX7iMprQGHdn3iVqebE9Qe4R5LScDCPz`

### 4. Invalid certificate

This certificate has a mismatch between the Peer ID that it claims to authenticate vs the key that was used to sign it.

Certificate:
```
3082021d308201c3a00302010202107f3d6f4349b6e7eb3b1bb66fff5046b8300a06082a8648ce3d040302301431123010060355040a13096c69627032702e696f301e170d3235303331393134333631355a170d3335303331373134333631355a301431123010060355040a13096c69627032702e696f3059301306072a8648ce3d020106082a8648ce3d03010703420004df3a5d51c593489f59301eb4363618ba87c47f8bbbaec04af98d5fb94f3e15fff2abc41cc14a85b765df1b83d56feae524abfd9ad85e1e2805f06fc2f9794e72a381f63081f3300e0603551d0f0101ff0404030205a030130603551d25040c300a06082b06010505070301300c0603551d130101ff040230003081bd060a2b0601040183a25a01010481ae3081ab045f0803125b3059301306072a8648ce3d020106082a8648ce3d03010703420004534e5755014446ff4077c66addc4ac71be602d146d5d709a8c476a94a680b7e3355a17b95eda49c19740b90dcfb929e1e537ec8146acfcaa731b1b84c1ffdd83044830460221009f599024ebec5e4002c63878e6ba84f98fc968f2d635539524b7161b4ad31752022100bf5dd3b475e84c2192bee0a94ba41751f846b2715fa2f2ec51443dd89bed37f1300a06082a8648ce3d040302034800304502202362f3821760ed19d8ecb6c2c98e272e36728e2f9b74c80dfb44f4b6a4bca7ac022100dfbf9c66a75fdb91aa4215c5dbb6a560b81dcc3ebf7e4ef414cfbe04a8f3e5ee
```

## Future Extensibility

Future versions of this handshake protocol MAY use the Server Name Indication (SNI) in the `ClientHello` as defined in [RFC 6066, section 3](https://tools.ietf.org/html/rfc6066) to announce their support for other versions.

In order to keep this flexibility for future versions, clients that only support the version of the handshake defined in this document MUST NOT send any value in the Server Name Indication. Servers that support only this version MUST ignore this field if present.
