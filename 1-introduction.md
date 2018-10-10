1 Introduction
==============

While developing [IPFS, the InterPlanetary FileSystem](https://ipfs.io/), we came to learn about several challenges imposed by having to run a distributed file system on top of heterogeneous devices, with different network setups and capabilities. During this process, we had to revisit the whole network stack and elaborate solutions to overcome the obstacles imposed by design decisions of the several layers and protocols, without breaking compatibility or recreating technologies.

In order to build this library, we focused on tackling problems independently, creating less complex solutions with powerful abstractions that, when composed, can offer an environment for a peer-to-peer application to work successfully.

## 1.1 Motivation

`libp2p` is the result of our collective experience of building a distributed system, in that it puts responsibility on developers to decide how they want an app to interoperate with others in the network, and favors configuration and extensibility instead of making assumptions about the network setup.

In essence, a peer using `libp2p` should be able to communicate with another peer using a variety of different transports, including connection relay, and talk over different protocols, negotiated on demand.

## 1.2 Goals

Our goals for the `libp2p` specification and its implementations are:

  - Enable the use of various:
    - transports ; for example TCP, UDP, SCTP, UDT, uTP, QUIC, SSH, etc.
    - authenticated transports ; for example TLS, DTLS, CurveCP, SSH
  - Make efficient use of sockets (connection reuse)
  - Enable communications between peers to be multiplexed over one socket (avoiding handshake overhead)
  - Enable multiprotocols and respective versions to be used between peers, using a negotiation process
  - Stay backwards compatible when releasing updates
  - Work in current systems
  - Use the full capabilities of current network technologies
  - Have NAT traversal
  - Enable connections to be relayed
  - Enable encrypted channels
  - Make efficient use of underlying transports (e.g. native stream muxing, native auth, etc.)
