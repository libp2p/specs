# QUIC-NOISE 1.0.0

> A combined muxer and security transport for libp2p.

| Lifecycle Stage | Maturity Level           | Status     | Latest Revision |
|-----------------|--------------------------|------------|-----------------|
| 2A              | Candidate Recommendation | Active     | r1, 2021-07-19  |

Authors: [@dvc94ch]

Interest Group: [@dvc94ch]

[@dvc94ch]: https://github.com/dvc94ch

See the [lifecycle document](../00-framework-01-spec-lifecycle.md) for context
about maturity level and spec status.

## Table of Contents

- [QUIC-NOISE 1.0.0](#secio-100)
    - [Table of Contents](#table-of-contents)
    - [Implementations](#implementations)
    - [Handshake pattern](#handshake-pattern)
    - [Identity and key exchange](#identity-and-key-exchange)
    - [Handshake session](#handshake-session)
    - [QUIC version](#quic-version)

## Implementations

- [rust-libp2p](https://github.com/libp2p/rust-libp2p/tree/master/protocols/quic)

## Handshake pattern

The IK handshake pattern is used with an optional psk. The psk allows for private
p2p networks using a pre shared key. In a p2p context the static keys are known and
the IK handshake allows for 0-rtt encryption. Identity hiding isn't a concern in
many p2p networks.

```
IKpsk1:
    <- s
    ...
    -> e, es, s, ss, psk  || client transport parameters || 0rtt-data
    <- e, ee, se          || server transport parameters || 1rtt-data
```

## Identity and key exchange

Signing keys are used as identities in p2p networks. Because the IK handshake requires prior
knowledge of the handshake key, the signing key is reused for the key exchange. An ed25519 key
is converted to an x25519 key using the algorithm as implemented by libsodium.

NOTE: while it is likely ok to reuse the key for singing and diffie hellman it is strongly advised
not to reuse the key for other protocols like VRF or threshold signatures.

## Handshake session

Using xoodyak (a finalist in the on-going NIST light weight crypto competition), the following
sequence of operations are performed for deriving the 0rtt-key, 1rtt-key and next-1rtt-key. For
fast authenticated encryption a chacha8poly1305 cipher is used.

```
Initial:
  | Cyclist({}, {}, {})
p | Absorb("Noise_IKpsk1_Edx25519_ChaCha8Poly")
p | Absorb(e)
  | Absorb(s)
  | Absorb(es)
  | key = Squeeze(32)
  | Cyclist(key, {}, {})
c | Encrypt(s)
  | Absorb(ss)
  | Absorb(psk)
c | Encrypt(client_transport_parameters)
t | Squeeze(16)
  | initiator-0rtt-key = SqueezeKey(32)
  | responder-0rtt-key = SqueezeKey(32)
...
Handshake:
c | Encrypt(e)
  | Absorb(ee)
  | Absorb(se)
c | Encrypt(server_transport_parameters)
t | Squeeze(16)
  | initiator-1rtt-key = SqueezeKey(32)
  | responder-1rtt-key = SqueezeKey(32)
...
Data:
  | Ratchet()
  | initiator-next-1rtt-key = SqueezeKey(32)
  | responder-next-1rtt-key = SqueezeKey(32)
```

## QUIC version

Reserved versions for `quinn-noise` are `0xf0f0f2f[0-f]` [0]. Currently only `0xf0f0f2f0` is a
valid `quinn-noise` version.

- [0] https://github.com/quicwg/base-drafts/wiki/QUIC-Versions
