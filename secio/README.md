# SECIO 1.0.0

> A stream security transport for libp2p. Streams wrapped by SECIO use secure
> sessions to encrypt all traffic.

## Authors

- [Juan Benet](https://github.com/jbenet) (October, 2015)

## Editors

- [Cole Brown](https://github.com/bigs)
- [Lars Gierth](https://github.com/lgierth)

## Implementations

- [js-libp2p-secio](https://github.com/libp2p/js-libp2p-secio)
- [go-secio](https://github.com/libp2p/go-libp2p-secio)

## Table of Contents

- [Algorithm Support](#algorithm-support)

## Algorithm Support

SECIO allows participating peers to support a subset of the following
algorithms.

### Exhchanges

- P-256
- P-384
- P-521

### Ciphers

- AES-256
- AES-128
- Blowfish

### Hashes

- SHA-256
- SHA-512

## Data Structures

The SECIO wire protocol features two message types defined in the
[protobuf description language](https://github.com/libp2p/go-libp2p-secio/blob/master/pb/spipe.proto).
These two messages, `Propose` and `Exchange` are the only serialized types
required to implement SECIO.

## Protocol

### Proposal Generation
