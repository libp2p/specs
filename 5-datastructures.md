5 Datastructures
================

The network protocol deals with these datastructures:

- a `PrivateKey`, the private key of a node.
- a `PublicKey`, the public key of a node.
- a `PeerID`, a hash of a node's public key.
- a `Node`[1], has a PeerID, and open connections to other `Nodes`.
- a `Connection`, a point-to-point link between two Nodes (muxes 1 or more streams)
- a `Stream`, a duplex message channel.

[1] currently called `PeerHost` in go-ipfs.
