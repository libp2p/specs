# libp2p specification


<h1 align="center">
  <img src="https://raw.githubusercontent.com/libp2p/libp2p/a13997787e57d40d6315b422afbe1ceb62f45511/logo/libp2p-logo.png" alt="libp2p logo"/>
</h1>

<a href="http://protocol.ai"><img src="https://img.shields.io/badge/made%20by-Protocol%20Labs-blue.svg?style=flat-square" /></a>
<a href="http://libp2p.io/"><img src="https://img.shields.io/badge/project-libp2p-yellow.svg?style=flat-square" /></a>
<a href="https://matrix.to/#/#welcome-j4p2p:matrix.org"><img src="https://img.shields.io/badge/matrix-🚪_Прихожая-yellow.svg?style=flat-square" /></a>
<a href="https://discuss.libp2p.io"><img src="https://img.shields.io/discourse/https/discuss.libp2p.io/posts.svg" /></a>

## Overview

Данный репозиторий являеться переводом спецификации для [`libp2p`](https://libp2p.io). Оригинальный репозиторий: [libp2p/specs](https://github.com/libp2p/specs).

Libp2p - это фреймворк для построения peer-to-peer приложений, с использование различных протоколов.
libp2p имеет несколько [реализаций][libp2p_implementations], и еще
многие в разработке.

Главной целью репозитория - это предоставить перевод технической документации для различных аспектов libp2p не зависимо от реализации или языка программирования.
Включая протоклы передачи данных, соглашение об адресации и других вопросов сетевого уровня.

Если вы ищите пользовательскую документацию, то она здесь: https://docs.libp2p.io

In addition to describing the current state of libp2p, the specs repository
serves as a coordination point and a venue to drive future developments in
libp2p. For the short and long term roadmap see [ROADMAP.md](./ROADMAP.md). To
participate in the evolution of libp2p via the specs process, please see the
[Contributions section](#contributions).

## Status

The specifications for libp2p are currently incomplete, and we are working to
address this by revising existing specs to ensure correctness and writing new
specifications to detail currently unspecified parts of libp2p.

This document replaces an earlier RFC, which still contains much useful
information and is helpful for understanding the libp2p design philosophy. It is
avaliable at [_archive/README.md](./_archive/README.md).

## Specification Index

This index contains links to all the spec documents that are currently merged.
If documents are moved to new locations within the repository, this index will
be updated to reflect the new locations.

### Specs Framework

These specs define processes for the specification framework itself, such as the
expected lifecycle and document formatting.

- [Spec Lifecycle][spec_lifecycle] - The process for introducing, revising and
  adopting specs.
- [Document Header][spec_header] - A standard document header for libp2p specs.

### Core Abstractions and Types

These specs define abstractions and data types that form the "core" of libp2p
and are used throughout the system.

- [Addressing][spec_addressing] - Working with addresses in libp2p.
- [Connections and Upgrading][spec_connections] - Establishing secure,
  multiplexed connections between peers, possibly over insecure, single stream transports.
- [Peer Ids and Keys][spec_peerids] - Public key types & encodings, peer id calculation, and
  message signing semantics

### Protocols

These specs define wire protocols that are used by libp2p for connectivity,
security, multiplexing, and other purposes.

The protocols described below all use [protocol buffers](https://developers.google.com/protocol-buffers/docs/proto?hl=en) (aka protobuf) to define message schemas. Version `proto2` is used unless stated otherwise.

- [ping][spec_ping] - Ping protocol
- [autonat][spec_autonat] - NAT detection
- [identify][spec_identify] -  Exchange keys and addresses with other peers
- [kademlia][spec_kademlia] - The Kademlia Distributed Hash Table (DHT) subsystem
- [mdns][spec_mdns] - Local peer discovery with zero configuration using multicast DNS
- [mplex][spec_mplex] - The friendly stream multiplexer
- [noise][spec_noise] - The libp2p Noise handshake
- [plaintext][spec_plaintext] - An insecure transport for non-production usage
- [pnet][spec_pnet] - Private networking in libp2p using pre-shared keys
- [pubsub][spec_pubsub] - PubSub interface for libp2p
  - [gossipsub][spec_gossipsub] - An extensible baseline PubSub protocol
    - [episub][spec_episub] - Proximity Aware Epidemic PubSub for libp2p
- [relay][spec_relay] - Circuit Switching for libp2p (similar to TURN)
  - [dcutr][spec_dcutr] - Direct Connection Upgrade through Relay protocol
- [rendezvous][spec_rendezvous] - Rendezvous Protocol for generalized
  peer discovery
- [secio][spec_secio] - SECIO, a transport security protocol for libp2p
- [tls][spec_tls] - The libp2p TLS Handshake (TLS 1.3+)
- [webrtc][spec_webrtc] - The libp2p WebRTC transport
- [WebTransport][spec_webtransport] - Using WebTransport in libp2p


## Contributions

Thanks for your interest in improving libp2p! We welcome contributions from all
interested parties. Please take a look at the [Spec Lifecycle][spec_lifecycle]
document to get a feel for how the process works, and [open an
issue](https://github.com/libp2p/specs/issues/new) if there's work you'd like to
discuss.

For discussions about libp2p that aren't specific to a particular spec, or if
you feel an issue isn't the appropriate place for your topic, please join our
[discussion forum](https://discuss.libp2p.io) and post a new topic in the
[contributor's section](https://discuss.libp2p.io/c/contributors).


[libp2p_implementations]: https://libp2p.io/implementations
[spec_lifecycle]: 00-framework-01-spec-lifecycle.md
[spec_header]: 00-framework-02-document-header.md
[spec_identify]: ./identify/README.md
[spec_kademlia]: ./kad-dht/README.md
[spec_mplex]: ./mplex/README.md
[spec_pnet]: ./pnet/Private-Networks-PSK-V1.md
[spec_pubsub]: ./pubsub/README.md
[spec_gossipsub]: ./pubsub/gossipsub/README.md
[spec_episub]: ./pubsub/gossipsub/episub.md
[spec_relay]: ./relay/README.md
[spec_rendezvous]: ./rendezvous/README.md
[spec_secio]: ./secio/README.md
[spec_tls]: ./tls/tls.md
[spec_peerids]: ./peer-ids/peer-ids.md
[spec_connections]: ./connections/README.md
[spec_plaintext]: ./plaintext/README.md
[spec_addressing]: ./addressing/README.md
[spec_noise]: ./noise/README.md
[spec_mdns]: ./discovery/mdns.md
[spec_autonat]: ./autonat/README.md
[spec_dcutr]: ./relay/DCUtR.md
[spec_webrtc]: ./webrtc/README.md
[spec_webtransport]: ./webtransport/README.md
[spec_ping]: ./ping/ping.md
