# gossipsub: An extensible baseline pubsub protocol

Revision:

Authors: vyzo

This is the specification for an extensible baseline pubsub protocol,
based on randomized topic meshes and gossip. It is a general purpose
pubsub protocol with moderate amplification factors and good scaling
properties.  The protocol is designed to be extensible by more
specialized routers, which may add protocol messages and gossip in
order to provide behaviour optimized for specific application
profiles.

<!-- toc -->

- [Implementation status](#implementation-status)
- [General purpose pubsub for libp2p](#general-purpose-pubsub-for-libp2p)
- [In the beginning was floodsub](#in-the-beginning-was-floodsub)
- [From floodsub to gossipsub](#from-floodsub-to-gossipsub)
  * [Controlling the flood: meshsub](#controlling-the-flood-meshsub)
  * [Gossip propagation: augmenting the mesh](#gossip-propagation-augmenting-the-mesh)
- [The gossipsub protocol](#the-gossipsub-protocol)
- [Protobuf](#protobuf)

<!-- tocstop -->

## Implementation status

- Go: [libp2p/go-floodsub#67](https://github.com/libp2p/go-floodsub/pull/67) (experimental)
- JS: not yet started
- Rust: not yet started
- Gerbil: [vyzo/gerbil-simsub](https://github.com/vyzo/gerbil-simsub) (simulator)

## General purpose pubsub for libp2p


## In the beginning was floodsub


## From floodsub to gossipsub

### Controlling the flood: meshsub

### Gossip propagation: augmenting the mesh


## The gossipsub protocol


## Protobuf
