# Design considerations for the libp2p TLS Handshake

## Requirements 

There are two main requirements that prevent us from using the straightforward way to run a TLS handshake (which would be to simply use the host key to create a self-signed certificate).

1. We want to use different key types: RSA, ECDSA, and Ed25519, Secp256k1 (and maybe more in the future?).
2. We want to be able to send the key type along with the key (see https://github.com/libp2p/specs/issues/111).

The first point is problematic in practice, because Go currently only supports RSA and ECDSA certificates. Support for Ed25519 was planned for Go 1.12, but was deferred recently, and the Go team is now evaluating interest in this in order to prioritze their work, so this might or might not happen in Go 1.13. I'm not aware of any plans for Secp256k1 at the moment.
The second requirement implies that we might want add some additional (free-form) information to the handshake, and we need to find a field to stuff that into.

The handshake protocol described here:
* supports arbitrary keys, independent from what the signature algorithms implemented by the TLS library used
* defines a way how future versions of this protocol might be negotiated without requiring any out-of-band information and additional roundtrips


## Design Choices

### TLS 1.3 - What about older versions?

The handshake protocol requires TLS 1.3 support. This means that the handshake between to peers that have never communicated before will typically complete in just a single roundtrip. With older TLS versions, a handshake typically takes two roundtrips. By not specifying support for older TLS versions, we increase perfomance and simplify the protocol.


### Why we're not using the host key for the certificate

The current proposal uses a self-signed certificate to carry the host's public key in the libp2p Public Key Extension. The key used to generate the self-signed certificate has no relationship with the host key. This key can be generated for every single connection, or can be generated at boot time.

One optimisation that was considered when designing the protocol was to use the libp2p host key to generate the certificate in the case of RSA and ECDSA keys (which we can assume to be supported signature schemes by all peers). That would have allowed us to strip the host key and the signature from the key extension, in order to

1. reduce the size of the certificate and
2. reduce the number of signature verifications the peer has to perform from 2 to 1.

The protocol does not include this optimisation, because

1. assuming that the peer uses an ECDSA key for generating the self-signed certificate, this only saves about ~150 bytes if the host key is an ECDSA key as well, and it even slightly increases the size of the certificate in case of a RSA host key. Furthermore, for ECDSA keys, the size of all handshake messages combined is less than 900 bytes, so having a slightly larger certificate won't require us to send more (TCP / QUIC) packets.
2. For a client, the number of signature verifications shouldn't pose a problem, since it controls the rate of its dials. Only for servers this might be a problem, since a malicious client could force a server to waste resources on signature verification. However, this is not a particularly interesting DoS vector, since the client's certificate is sent in its second flight (after receiving the ServerHello and the server's certificate), so it requires the attacker to actually perform most of the TLS handshake, including encrypting the certificate chain with a key that's tied to that handshake.


### Versioning - How we could roll out a new version of this protocol in the future

An earlier version of this document included a version negotiation mechanism. While it is a desireable property to be able to change things in the future, it also adds a lot of complexity.

To keep things simple, the current proposal does not include a version negotiation mechanism. A future version of this protocol might:

1. Change the format in which the keys are transmitted. A x509 extension has an ID (the Objected Identifier, OID), so we can use a new OID if we want to change the way we encode information. x509 certificates allow use to include multiple extensions, so we can even send the old and the new version during a transition period. In the handshake protocol defined here, peers are required to skip over extensions that they don't understand.
2. For more involved changes, a new version might (ab)use the SNI field field in the ClientHello to announce support for new versions. To allow for this to work, the current version requires clients to send anything in the SNI field and server to completely ignore this field, no matter what its contents are.
