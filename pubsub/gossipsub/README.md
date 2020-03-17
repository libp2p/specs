# gossipsub: An extensible baseline pubsub protocol

Gossipsub is an extensible baseline pubsub protocol,
based on randomized topic meshes and gossip. It is a general purpose
pubsub protocol with moderate amplification factors and good scaling
properties. The protocol is designed to be extensible by more
specialized routers, which may add protocol messages and gossip in
order to provide behaviour optimized for specific application
profiles.

## Specification

- [gossipsub-v1.0](gossipsub-v1.0.md): v1.0 of the gossipsub protocol. This is a revised specification, to use a more normative language. 
  - The original v1.0 specification is [here](gossippsub-v1.0-old.md).
- [gossipsub-v1.1](gossipsub-v1.1.md): v1.1 of the gossipsub protocol.
- [(not in use) episub](episub.md): a research note on a protocol building on top of gossipsub to implement [epidemic broadcast trees](https://www.gsd.inesc-id.pt/~ler/reports/srds07.pdf).

## Implementation status

- Go: [libp2p/go-libp2p-pubsub/gossipsub.go](https://github.com/libp2p/go-libp2p-pubsub/blob/master/gossipsub.go) (experimental)
- JS: [ChainSafeSystems/gossipsub-js](https://github.com/ChainSafeSystems/gossipsub-js) (compliant with `gossipsub-v1.0`).
- Rust: [libp2p/rust-libp2p#898](https://github.com/libp2p/rust-libp2p/pull/898) implements the spec but is missing some features. [libp2p/rust-libp2p#767](https://github.com/libp2p/rust-libp2p/pull/767) is an alternative, partial implementation that differs slightly from the spec (see [#142](https://github.com/libp2p/specs/issues/142) for details).
- Gerbil: [vyzo/gerbil-simsub](https://github.com/vyzo/gerbil-simsub) (simulator)
