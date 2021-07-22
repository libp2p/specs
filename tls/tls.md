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

In order to be able use arbitrary key types, peers don’t use their host key to sign the X.509 certificate they send during the handshake. Instead, the host key is encoded into the [libp2p Public Key Extension](#libp2p-public-key-extension), which is carried in a self-signed certificate.

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

The peer signs the concatenation of the string `libp2p-tls-handshake:` and the `SubjectPublicKeyInfo` of the certificate carrying the libp2p Public Key Extension, using its private host key. This signature provides cryptographic proof that the peer was in possession of the private host key at the time the certificate was signed. Peers MUST verify the signature, and abort the connection attempt if signature verification fails.

The public host key and the signature are ANS.1-encoded into the SignedKey data structure, which is carried in the libp2p Public Key Extension. The libp2p Public Key Extension is a X.509 extension with the Object Identier `1.3.6.1.4.1.53594.1.1`, [allocated by IANA to the libp2p project at Protocol Labs](https://www.iana.org/assignments/enterprise-numbers/enterprise-numbers).

```asn1
SignedKey ::= SEQUENCE {
  publicKey BIT STRING,
  signature BIT STRING 
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

**TODO: PublicKey.Data looks underspecified. Define precisely how to marshal the key.**

## Future Extensibility

Future versions of this handshake protocol MAY use the Server Name Indication (SNI) in the `ClientHello` as defined in [RFC 6066, section 3](https://tools.ietf.org/html/rfc6066) to announce their support for other versions.

In order to keep this flexibility for future versions, clients that only support the version of the handshake defined in this document MUST NOT send any value in the Server Name Indication. Servers that support only this version MUST ignore this field if present.
