5 Datastructures
================

The network protocol deals with these datastructures:

- a `PrivateKey`, the private key of a node.
- a `PublicKey`, the public key of a node.
- a `PeerId`, a hash of a node's public key.
- a `PeerInfo`[1], an object with peerId and known multiaddrs from another Node.
- a `Transport`, a transport used to establish connections to other peers. https://github.com/diasdavid/abstract-transport
- a `Connection`, a point-to-point link between two Nodes. Must implement https://github.com/diasdavid/abstract-connection
- a `Muxed-Stream`, a duplex message channel. 
- a `Stream-Muxer`, a stream multiplexer. Must implement https://github.com/diasdavid/abstract-stream-muxer
- a `Record`, IPLD described object that implements IPRS
- a `multiaddr`, a self describable network address - https://github.com/jbenet/js-multiaddr
- a `multicodec`, a self describable encoding type - https://github.com/jbenet/multicodec
- a `multihash`, a self describable hash - https://github.com/jbenet/multihash

[1] currently called `PeerHost` in go-ipfs.
