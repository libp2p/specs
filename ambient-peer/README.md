# Ambient peer discovery

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r0, 2023-10-08  |

Authors: [@thomaseizinger]

Interest Group: 

[@thomaseizinger]: https://github.com/thomaseizinger

See the [lifecycle document][lifecycle-spec] for context about the maturity level and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Table of Contents

<!-- TODO -->

## Overview

The ambient peer discovery protocol allows peers to share some of their ambient peers with each other.
Ambient in this case means "peers I used to be connected to".

## Usecase

Ambient peer discovery is most useful when a node either starts with or is left with a few or perhaps only a single connection.

For example, a user may start a libp2p web app and enter another browser's relayed `/webrtc` address.
The connection will succeed but because both nodes are browsers, further discovery of nodes via e.g. kademlia is not possible.
Ambient peer discovery allows the web app to inquire for further nodes from the new connection.

## Protocol

1. Node _A_ opens a new stream to node _B_ with the protocol name `/libp2p/ambient-peers`.
1. Node _B_ chooses a subset of at most 5 known peer records received from other peers.
   1. The chosen peer records SHOULD at least have one address that share the same transport technology as the the connection between node _A_ and node _B_.
      For example, if node _A_ and node _B_ are connected via WebRTC, node _B_ SHOULD select 5 peer records where each one of them has at least one WebRTC address.
   1. Node _B_ SHOULD NOT be currently connected to any of these nodes.
1. Node _B_ writes these peer records onto the stream in their [protobuf encoding](https://github.com/libp2p/specs/blob/master/RFC/0003-routing-records.md#address-record-format), each record being length-prefixed using an unsigned varint and closes the stream after the last one.
1. Node _A_ reads peer records from the stream until EOF or 5 have been received, whichever comes earlier.

## Security considerations

Revealing even just some of your peers has serious privacy and security implications for a network.
By default, implementations MUST NOT share records of peers they are currently connected to.
Implementations MAY add a configuration flag that allows users to override this.

<!-- @vyzo to add more text here -->

## Implementation considerations

### Bound local peer storage

This protocol requires nodes to store records of peers they used to be connected to.
This is useful independently of this protocol to e.g. reconnect to a peer you've once been connected to.
Implementations should take care that the resulting memory or disk usage is bounded and only store a number of peers appropriate for their deployment target (mobile, server, etc). 

### Group transport technologies

Implementations MAY group transports as follows:

1. **Anything on top of TCP:** We support several encryption protocols on top of TCP like noise or TLS.
   Some nodes may choose to embed this in their multiaddress using `/tls` or `/noise`.
   Nodes MAY consider these to be the equivalent and return a peer record containing a `/tcp/noise` address on a connection that is using `/tcp/tls`.
2. **All versions of QUIC:** QUIC is in itself a versioned protocol and we have for the moment two multiaddress protocols: `/quic` and `/quicv1`.
   For the purpose of ambient peer discovery, nodes MAY assume all current and future versions of QUIC are equal.
3. **Anything Web:** If a peer connects over `/webrtc`, `/webrtc-direct`, `/webtransport` or `/ws`, chances are they are a browser node.
   As such, nodes MAY assume that any peer record with one of these is useful.
4. **IPv4 & IPv6**: Nodes MAY assume that the requesting peer is capable of dialing either version of IP, regardless of which one was used to make the connection.

### Separating networks

Libp2p is used across a range of networks and many of them may not actually have a useful overlap in compatible protocols.
To avoid sharing addresses of peers that don't support useful protocols, implementations SHOULD allow configuration of the protocol identifier.
For example, instead of `/libp2p/ambient-peers` a node may use `/my-cool-p2p-network/ambient-peers`.
It is RECOMMENDED that implementations retain the `/ambient-peers` suffix to communicate the semantics of this protocol.

## Prior art

Exchanging peers one knows is a common thing in the peer-to-peer space:

1. [PEX](https://en.wikipedia.org/wiki/Peer_exchange) augments the BitTorrent protocol.
2. Bitcoin nodes can send [`addr`](https://en.bitcoin.it/wiki/Protocol_documentation#addr) messages to exchange peers with one another.
3. WAKU has an [ambient-peer discovery](https://github.com/vacp2p/rfc/blob/master/content/docs/rfcs/34/README.md) protocol built on top of libp2p.

There have been several discussions in the libp2p space about adding such a protocol:

- https://github.com/libp2p/specs/issues/222
- https://github.com/libp2p/notes/issues/3
- https://github.com/libp2p/notes/issues/7

## FAQ

### Why not use the rendezvous?

The rendezvous protocol could be repurposed as a kind of peer exchange protocol.
We would have to agree on an identifier that all peers use to register themselves within a certain topic.
Other peers can then go and query a node for all peers registered under this topic.

We consider this impractical for the given problem because:

- It requires three parties to support the protocol instead of just two and thus would take a lot longer to be rolled out.
- It creates a lot of traffic.
  Nodes have to actively register themselves without knowing whether their peer record will ever be distributed / requested.
  To be effective, every node would have to register themselves with every other node.
