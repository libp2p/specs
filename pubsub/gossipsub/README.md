# gossipsub: An extensible baseline pubsub protocol

<p align="center">
  <img src="https://ipfs.io/ipfs/QmVSk8VvxWExnYCjqg7TNW2aBnN8Wr7SzkawLUyocWq96p/Gossipsub_fullcolor.png" alt="Gossipsub logo" width="400" />
</p>

![]()

Gossipsub is an extensible baseline pubsub protocol, based on randomized topic meshes and gossip. It is a general purpose pubsub protocol with moderate amplification factors and good scaling properties. The protocol is designed to be extensible by more specialized routers, which may add protocol messages and gossip in order to provide behaviour optimized for specific application profiles.

If you are new to Gossipsub and/or PubSub in general, we recommend you to first:
- Read the [Publish/Subscribe guide at docs.libp2p.io](https://docs.libp2p.io/concepts/publish-subscribe/)
- Watch the [Scalable PubSub with GossipSub talk by Dimitris Vyzovitis](https://www.youtube.com/watch?v=mlrf1058ENY&index=3&list=PLuhRWgmPaHtRPl3Itt_YdHYA0g0Eup8hQ)

## Specification

- [gossipsub-v1.0](gossipsub-v1.0.md): v1.0 of the gossipsub protocol. This is a revised specification, to use a more normative language. The original v1.0 specification is [here](gossipsub-v1.0-old.md), still a good read.
- [gossipsub-v1.1](gossipsub-v1.1.md): v1.1 of the gossipsub protocol.
- [gossipsub-v1.2](gossipsub-v1.2.md): v1.2 of the gossipsub protocol. This includes the aggregation of the IDONTWANT control messages to the specs.
- [gossipsub-v1.3](gossipsub-v1.3.md): v1.3 of the gossipsub protocol. Introduces the Extensions Control Message framework.
- [gossipsub-v1.4](gossipsub-v1.4.md): v1.4 of the gossipsub protocol. Large message propagation via fragmentation, staggering, PREAMBLE, and IMRECEIVING.
  - [Design Document](design-document.md): Architectural rationale, prototype analysis (nim-libp2p, py-libp2p), and design decisions for the v1.4 specification.
- [(not in use) episub](episub.md): a research note on a protocol building on top of gossipsub to implement [epidemic broadcast trees](https://www.gsd.inesc-id.pt/~ler/reports/srds07.pdf).

## Implementation status

Legend: ✅ = complete, 🏗 = in progress, ❕ = not started yet

| Name                                                                                             | v1.0  | v1.1  | v1.2 | v1.3 | v1.4 |
|--------------------------------------------------------------------------------------------------|:-----:|:-----:|:----:|:----:|:----:|
| [go-libp2p-pubsub (Golang)](https://github.com/libp2p/go-libp2p-pubsub/blob/master/gossipsub.go) |   ✅  |   ✅  |   ✅  |  🏗  |  ❕  |
| [js-libp2p-gossipsub (JavaScript)](https://github.com/ChainSafe/js-libp2p-gossipsub)             |   ✅  |   ✅  |   ✅  |  ❕  |  ❕  |
| [rust-libp2p (Rust)](https://github.com/libp2p/rust-libp2p/tree/master/protocols/gossipsub)      |   ✅  |   ✅  |  ❔   |  ❕  |  ❕  |
| [py-libp2p (Python)](https://github.com/libp2p/py-libp2p/tree/master/libp2p/pubsub)              |   ✅  |   🏗  |   ❔  |  ❕  |  🏗  |
| [jvm-libp2p (Java/Kotlin)](https://github.com/libp2p/jvm-libp2p/tree/develop/src/main/kotlin/io/libp2p/pubsub) |   ✅  |   🏗  |   ✅  |  ❕  |  ❕  |
| [nim-libp2p (Nim)](https://github.com/status-im/nim-libp2p/blob/master/libp2p/protocols/pubsub/gossipsub.nim) |   ✅  |   🏗  |   ✅  |  ❕  |  🏗  |

Additional tooling:

- Simulator developed in Gerbil: [vyzo/gerbil-simsub](https://github.com/vyzo/gerbil-simsub)
- Formal specification developed in ACL2s: [gossipsubfm/gossipsubfm](https://github.com/gossipsubfm/gossipsubfm)
