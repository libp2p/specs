RFC - libp2p
============

![](https://raw.githubusercontent.com/diasdavid/specs/libp2p-spec/protocol/network/figs/logo.png)

Authors: 
- [Juan Benet](https://github.com/jbenet)
- [David Dias](https://github.com/diasdavid)

Reviewers:


> tl;dr; This document presents libp2p, a modularized and extensible network stack to overcome the networking challenges faced when doing Peer-to-Peer applications. libp2p is used by IPFS as its networking library.

* * *

# Abstract

This describes the IPFS network protocol. The network layer provides point-to-point transports (reliable and unreliable) between any two IPFS nodes in the network.

This document defines the spec implemented in libp2p.

# Status of this spec

> **This spec is a Work In Progress (WIP).**

# Organization of this document

This RFC is organized by chapters described on the `Table of Contents` section. Each of the chapters can be found in its own file.

# Table of Contents

- [1 Introduction](1-introduction.md)
  - [1.1 Motivation](1-introduction.md#11-motivation)
  - [1.2 Goals](1-introduction.md#12-goals)
- [2 Overview of current Network Stack](2-state-of-the-art.md)
  - [2.1 Client Server model](2-state-of-the-art.md#21-the-client-server-model)
  - [2.2 Categorizing the Network Stack protocols by solutions](2-state-of-the-art.md#22-categorizing-the-network-stack-protocols-by-solutions)
  - [2.3 Current Shortcommings](2-state-of-the-art.md#23-current-shortcommings)
- [3 Requirements](3-requirements.md)
  - [3.1 NAT traversal](3-requirements.md#31-nat-traversal)
  - [3.2 Relay](3-requirements.md#32-relay)
  - [3.3 Encryption](3-requirements.md#33-encryption)
  - [3.4 Transport Agnostic](3-requirements.md#34-transport-agnostic)
  - [3.5 Multi-Multiplexing](3-requirements.md#35-multi-multiplexing)
- [4 Architecture](4-architecture.md)
  - [4.1 Peer Routing](4-architecture.md#41-peer-routing)
  - [4.2 Swarm](4-architecture.md#42-swarm)
  - [4.3 Distributed Record Store](4-architecture.md#43-distributed-record-store)
- [5 Datastructures](5-datastructures.md)
- [6 Interfaces](6-interfaces.md)
  - [6.1 libp2p](6-interfaces.md#61-libp2p)
  - [6.2 Peer Routing](6-interfaces.md#62-peer-routing)
  - [6.3 Swarm](6-interfaces.md#63-swarm)
  - [6.4 Distributed Record Store](6-interfaces.md#64-distributed-record-store)
- [7 Properties](7-properties.md)
  - [7.1 Communication Model - Streams](7-properties.md#71-communication-model---streams)
  - [7.2 Ports - Constrained Entrypoints](7-properties.md#72-ports---constrained-entrypoints)
  - [7.3 Transport Protocol](7-properties.md#73-transport-protocols)
  - [7.4 Non-IP Networks](7-properties.md#74-non-ip-networks)
  - [7.5 On the wire](7-properties.md#75-on-the-wire)
    - [7.5.1 Protocol-Multiplexing](7-properties.md#751-protocol-multiplexing)
    - [7.5.2 multistream - self-describing protocol stream](7-properties.md#752-multistream---self-describing-protocol-stream)
    - [7.5.3 multistream-selector - self-describing protocol stream selector](7-properties.md#753-multistream-selector---self-describing-protocol-stream-selector)
    - [7.5.4 Stream Multiplexing](7-properties.md#754-stream-multiplexing)
    - [7.5.5 Portable Encodings](7-properties.md#755-portable-encodings)
- [8 Implementations](8-implementations.md)
- [9 References](9-references.md)
