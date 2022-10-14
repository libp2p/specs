5 Data structures
=================

The network protocol deals with these data structures:

- a `PrivateKey`, the private key of a node.
- a `PublicKey`, the public key of a node.
- a `PeerId`, a hash of a node's public key.
- a `PeerInfo`, an object containing a node's `PeerId` and its known multiaddrs.
- a `Transport`, a transport used to establish connections to other peers. See <https://github.com/libp2p/interface-transport>.
- a `Connection`, a point-to-point link between two nodes. Must implement <https://github.com/libp2p/interface-connection>.
- a `Muxed-Stream`, a duplex message channel.
- a `Stream-Muxer`, a stream multiplexer. Must implement <https://github.com/libp2p/interface-stream-muxer>.
- a `Record`, IPLD (IPFS Linked Data) described object that implements [IPRS](./IPRS.md).
- a `multiaddr`, a self describable network address. See <https://github.com/multiformats/multiaddr>.
- a `multicodec`, a self describable encoding type. See <https://github.com/multiformats/multicodec>.
- a `multihash`, a self describable hash. See <https://github.com/multiformats/multihash>.
