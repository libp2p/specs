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
Ambient in this case simply means "known peers".
There is no definition of distance like in kademlia and neither do peers have to be connected to consider another peer as ambient.

## Usecase

Ambient peer discovery is most useful when a node either starts with or is left with a few or perhaps only a single connection.

For example, a user may start a libp2p web app and enter another browser's relayed `/webrtc` address.
The connection will succeed but because both nodes are browsers, further discovery of nodes via e.g. kademlia is not possible.
Ambient peer discovery allows the web app to inquire for further nodes from the new connection.

## Protocol

1. Node _A_ opens a new stream to node _B_ with the protocol name `/libp2p/ambient-peers`.
2. Node _B_ chooses a subset of at most 5 known peer records received from other peers.
   The chosen peer records SHOULD at least have one address that share the same transport technology as the the connection between node _A_ and node _B_.
   For example, if node _A_ and node _B_ are connected via WebRTC, node _B_ SHOULD select 5 peer records where each one of them has at least one WebRTC address.
3. Node _B_ writes these peer records onto the stream in their [protobuf encoding](https://github.com/libp2p/specs/blob/master/RFC/0003-routing-records.md#address-record-format), each record being length-prefixed using an unsigned varint and closes the stream after the last one.
4. Node _A_ reads peer records from the stream until EOF or 5 have been received, whichever comes earlier.

## Security considerations

Revealing even just some of your peers has serious privacy and security implications for a network.
Care has been taken to mitigate some of these at the design level of the ambient peer discovery protocol.
However, users should still be aware that usage of this protocol does reveal _some_ of your either current or past connections.

<!-- @vyzo to add more text here -->

### Pre-sample peer records

Creating new nodes is cheap, meaning we have to assume that repeated requests for e.g. TCP nodes may all come from the same actor trying to map the network.
Implementations therefore MUST pre-sample which peer records they will return for a particular transport protocol and return the same set, regardless of which peer is asking.

Implementations MAY group transports as follows to further reduce how many peers they reveal:

1. **Anything on top of TCP:** We support several encryption protocols on top of TCP like noise or TLS.
   Some nodes may choose to embed this in their multiaddress using `/tls` or `/noise`.
   Nodes MAY consider these to be the equivalent and return a peer record containing a `/tcp/noise` address on a connection that is using `/tcp/tls`.
2. **All versions of QUIC:** QUIC is in itself a versioned protocol and we have for the moment two multiaddress protocols: `/quic` and `/quicv1`.
   For the purpose of ambient peer discovery, nodes MAY assume all current and future versions of QUIC are equal.
3. **Anything Web:** If a peer connects over `/webrtc`, `/webrtc-direct`, `/webtransport` or `/ws`, chances are they are a browser node.
   As such, nodes MAY assume that any peer record with one of these is useful.
4. **IPv4 & IPv6**: Nodes MAY assume that the requesting peer is capable of dialing either version of IP, regardless of which one was used to make the connection.
