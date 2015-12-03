1 Introduction
==============

With the developement of building [IPFS, the InterPlanetary FileSystem](https://ipfs.io/), we came to learn about the several challenges imposed by having to run a distributed file system on top of heterogeneous devices, with diferent network setups and capabilities. During this process, we had to revisit the whole network stack and elaborate solutions to overcome the obstacles imposed by design decisions of the several layers and protocols, without breaking compatibility or recreating technologies.

In order to build this library, we focused on tackling problems independently, creating less complex solutions with powerful abstractions that, when composed, can offer an environment for a peer-to-peer application to work sucessfuly.

## 1.1 Motivation

`libp2p` is the result of the collective experience while building a distributed system, that puts the responsability on the developers on how they want their app to interoperate with others in the network, favoring configuration and extensibility instead of assumptions about the network setup.

In essence, a peer using `libp2p` should be able to communicate with another peer using different transports, including connection relay, and talk over different protocols, negotiated on demand.

## 1.2 Goals

Our goals for `libp2p` specification and its implementations are:

  - Enable the use of various:
    - transports: TCP, UDP, SCTP, UDT, uTP, QUIC, SSH, etc.
    - authenticated transports: TLS, DTLS, CurveCP, SSH
  - Efficient use of sockets (connection reuse)
  - Enable communications between peers to be multiplexed over one socket (avoiding handshake overhead)
  - Enable multiprotocols and respective versions to be used between peers, using a negotiation process
  - Be backwards compatible
  - Work in current systems
  - Use the current network technologies to its best capability
  - Have NAT traversal
  - Enable connections to be relayed
  - Enable encrypted channels
  - Efficient use of underlying transport (e.g. native stream muxing, native auth, etc.)
