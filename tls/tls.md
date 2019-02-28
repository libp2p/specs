# libp2p TLS Handshake

## Introduction

This document describes how [TLS 1.3](https://tools.ietf.org/html/rfc8446) is used to secure libp2p connections. Endpoints authenticates to their peers by encoding their public key into a x509 certificate extension. The protocol described here allows peers to use arbitrary key types, not constrained to those for which signing of a x509 certificates is specified.


## Handshake Protocol

The libp2p handshake uses TLS 1.3 (and higher). Endpoints MUST NOT negotiate lower TLS versions.

During the handshake, peers authenticate each other’s identity as described in [Peer Authentication](#peer-authentication). Endpoints MUST verify the peer's identy. Specifically, this means that servers MUST require clients authentication during the TLS handshake, and MUST abort a connection attempt if the client fails to provide the requested authentication information.


## Peer Authentication

In order to be able use arbitrary key types, peers don’t use their host key to sign the x509 certificate they send during the handshake. Instead, the host key is encoded into the [libp2p Public Key Extension](#libp2p-public-key-extension), which is carried in a self-signed certificate. The key used to generate and sign this certificate SHOULD NOT be related to the host's key. Endpoints MAY generate a new key and certificate for every connection attempt, or they MAY reuse the same key and certificate for multiple connections. Endpoints MUST choose a key that will allow the peer to verify the certificate (i.e. choose a signature algorithm that the peer supports), and SHOULD use a key type which allows for efficient signature computation and which reduces the combined size of the certificate and the signature.

Endpoints MUST NOT send a certificate chain that contains more than one certificate. The certificate MUST have NotBefore and NotAfter fields set such that the certificate is valid at the time it is received by the peer. When receiving the certificate chain, an endpoint MUST check these conditions and abort the connection attempt if the presented certificate is not yet valid or if it is expired.

The certificate MUST contain the [libp2p Public Key Extension](#libp2p-public-key-extension). If this extension is missing, endpoints MUST abort the connection attempt. The certificate MAY contain other extensions, implementations MUST ignore extensions with unknown OIDs.

Note for clients: Since clients complete the TLS handshake immediately after sending the certificate (and the TLS ClientFinished message), the handshake will appear as having succeeded before the server had the chance to verify the certificate. In this state, the client can already send application data. If certificate verification fails on the server side, the server will close the connection without processing any data that the client sent.



### libp2p Public Key Extension

In order to prove ownership of its host key, an endpoint sends two values:
- the public key corresponding to its host key
- a signature performed using the host key

The public key allows the peer to calculate the peer ID of the peer it is connecting to. Clients MUST verify that the peer ID derived from the certificate matches the peer ID they intended to connect to, and MUST abort the connection if it there is a mismatch.

The peer signs its public key using the its host key. This signature provides cryptographic proof that the peer was in possession of the private key at the time the certificate was signed. Peers MUST verify the signature, and abort the connection attempt if signature verification fails.

The public key and the signature are ANS.1-encoded into the SignedKey data structure, which is carried in the libp2p Public Key Extension. The libp2p Public Key Extension is a x509 extension with the Object Identier 1.3.6.1.4.1.XXX.YYY.

TODO: Nothing will break if we just use an arbitrary value for XXX. However, if we want to do things correctly, [OID](https://en.wikipedia.org/wiki/Object_identifier) PENs should be registered with [IANA](https://pen.iana.org/pen/PenApplication.page). 

```asn1
SignedKey ::= SEQUENCE {
  publicKey BIT STRING,
  signature BIT STRING 
}
```

The publicKey field of SignedKey contains the public key of the endpoint, encoded using the following protobuf.

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

TODO: PublicKey.Data looks underspecified. Define precisely how to marshal the key.


## Future Extensibility

Future versions of this handshake protocol MAY use the Server Name Indication in the ClientHello as defined in [RFC 6066, section 3](https://tools.ietf.org/html/rfc6066) to announce their support for other versions. In order to keep this flexibility for future versions, clients that only support the version of the handshake defined in this document MUST NOT send any value in the Server Name Indication. Servers that only this version MUST ignore this field, specifically, they MUST NOT check if it was empty.
