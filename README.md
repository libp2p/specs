# libp2p specification


<h1 align="center">
  <img src="https://raw.githubusercontent.com/libp2p/libp2p/a13997787e57d40d6315b422afbe1ceb62f45511/logo/libp2p-logo.png" alt="libp2p logo"/>
</h1>

<a href="http://protocol.ai"><img src="https://img.shields.io/badge/made%20by-Protocol%20Labs-blue.svg?style=flat-square" /></a>
<a href="http://libp2p.io/"><img src="https://img.shields.io/badge/project-libp2p-yellow.svg?style=flat-square" /></a>
<a href="http://webchat.freenode.net/?channels=%23libp2p"><img src="https://img.shields.io/badge/freenode-%23libp2p-yellow.svg?style=flat-square" /></a>

## Overview

This repository contains the specifications for [`libp2p`](https://libp2p.io), a
framework and suite of protocols for building peer-to-peer network applications.
libp2p has several [implementations][libp2p_implementations], with more in development.

The main goal of this repository is to provide accurate reference documentation
for the aspects of libp2p that are independent of language or implementation.
This includes wire protocols, addressing conventions, and other "network level"
concerns. 

## Status

The specifications for libp2p are currently incomplete, and we have recently
[defined a process][spec_lifecycle] for categorizing specs according to their
maturity and status. Many of the existing specs linked below are not yet
categorized according to this framework, however, they will soon be updated for
consistency.

This document replaces an earlier RFC, which still contains much useful
information and is helpful for understanding the libp2p design philosophy. It is
avaliable at [archive/README.md](./archive/README.md).

## Index

- [identify](./identify/README.md) Exchange keys and addresses with other peers
- [mplex](./mplex/README.md) The friendly stream multiplexer
- [pnet](./pnet/README.md) Private networking in libp2p using pre-shared keys
- [pubsub](./pubsub/README.md) PubSub interface for libp2p
  - [gossipsub](./pubsub/gossipsub/README.md) An extensible baseline PubSub
    protocol
    - [episub](./pubsub/gossipsub/episub.md) Proximity Aware Epidemic PubSub for libp2p
- [relay](./relay/README.md) Circuit Switching for libp2p (aka TURN in
  networking literature)
- [rendezvous](./rendezvous/README.md) Rendezvous protocol
- [tls](./tls/tls.md) The libp2p TLS Handshake (TLS 1.3+)


[libp2p_implementations]: https://libp2p.io/implementations
[spec_lifecycle]: 00-framework-01-spec-lifecycle.md
