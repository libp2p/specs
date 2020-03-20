# gossipsub: An extensible baseline pubsub protocol

![](https://gateway.ipfs.io/ipfs/Qmbox17N8YF5GxVaM6u2c2quokg4brqxMZGzSMfibQ2nw1)

Gossipsub is an extensible baseline pubsub protocol, based on randomized topic meshes and gossip. It is a general purpose pubsub protocol with moderate amplification factors and good scaling properties. The protocol is designed to be extensible by more specialized routers, which may add protocol messages and gossip in order to provide behaviour optimized for specific application profiles.

If you are new to Gossipsub and/or PubSub in general, we recommend you to first:
- Read the [Publish/Subscribe guide at docs.libp2p.io](https://docs.libp2p.io/concepts/publish-subscribe/)
- Watch the [Scalable PubSub with GossipSub talk by Dimitris Vyzovitis](https://www.youtube.com/watch?v=mlrf1058ENY&index=3&list=PLuhRWgmPaHtRPl3Itt_YdHYA0g0Eup8hQ)

## Specification

- [gossipsub-v1.0](gossipsub-v1.0.md): v1.0 of the gossipsub protocol. This is a revised specification, to use a more normative language. The original v1.0 specification is [here](gossippsub-v1.0-old.md), still a good read.
- [gossipsub-v1.1](gossipsub-v1.1.md): v1.1 of the gossipsub protocol.
- [(not in use) episub](episub.md): a research note on a protocol building on top of gossipsub to implement [epidemic broadcast trees](https://www.gsd.inesc-id.pt/~ler/reports/srds07.pdf).

## Implementation status

Legend: ✅ = complete, 🏗 = in progress, ❕ = not started yet

| Name                                                                                             | v1.0  | v1.1  |
|--------------------------------------------------------------------------------------------------|:-----:|:-- --:|
| [go-libp2p-pubsub (Golang)](https://github.com/libp2p/go-libp2p-pubsub/blob/master/gossipsub.go) |   ✅  |   ✅  |
| [gossipsub-js (JavaScript)](https://github.com/ChainSafeSystems/gossipsub-js)                    |   ✅  |   ❕  |
| [rust-libp2p (Rust)](https://github.com/libp2p/rust-libp2p/tree/master/protocols/gossipsub)      |   🏗  |   ❕  |
| [py-libp2p (Python)](https://github.com/libp2p/py-libp2p/tree/master/libp2p/pubsub)              |   ✅  |   ❕  |
| [jvm-libp2p (Java/Kotlin)](https://github.com/libp2p/jvm-libp2p/tree/develop/src/main/kotlin/io/libp2p/pubsub) |   ✅  |   ❕  |

Additional tooling:

- Simulator developed in Gerbil: [vyzo/gerbil-simsub](https://github.com/vyzo/gerbil-simsub)
