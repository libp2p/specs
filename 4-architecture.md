4 Architecture
==============

`libp2p` was designed around the Unix Philosophy of creating small components that are easy to understand and test. These components should also be able to be swapped in order to accommodate different technologies or scenarios and also make it feasible to upgrade them over time.

Although different peers can support different protocols depending on their capabilities, any peer can act as a dialer and/or a listener for connections from other peers, connections that once established can be reused from both ends, removing the distinction between clients and servers.

The `libp2p` interface acts as a thin veneer over a multitude of subsystems that are required in order for peers to be able to communicate. These subsystems are allowed to be built on top of other subsystems as long as they respect the standardized interface. The main areas where these subsystems fit are:

- Peer Routing - Mechanism to decide which peers to use for routing particular messages. This routing can be done recursively, iteratively or even in a broadcast/multicast mode.
- Swarm - Handles everything that touches the 'opening a stream' part of `libp2p`, from protocol muxing, stream muxing, NAT traversal and connection relaying, while being multi-transport.
- Distributed Record Store - A system to store and distribute records. Records are small entries used by other systems for signaling, establishing links, announcing peers or content, and so on. They have a similar role to DNS in the broader Internet.
- Discovery - Finding or identifying other peers in the network.

Each of these subsystems exposes a well known interface (see [chapter 6](6-interfaces.md) for Interfaces) and may use each other in order to fulfill their goal. A global overview of the system is:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                  libp2p                                         │
└─────────────────────────────────────────────────────────────────────────────────┘
┌─────────────────┐┌─────────────────┐┌──────────────────────────┐┌───────────────┐
│   Peer Routing  ││      Swarm      ││ Distributed Record Store ││  Discovery    │
└─────────────────┘└─────────────────┘└──────────────────────────┘└───────────────┘
```

## 4.1 Peer Routing

A Peer Routing subsystem exposes an interface to identify which peers a message should be routed to in the DHT. It receives a key and must return one or more `PeerInfo` objects.

We present two examples of possible Peer Routing subsystems, the first based on a the Kademlia DHT and the second based on mDNS. Nevertheless, other Peer Routing mechanisms can be implemented, as long as they fulfil the same expectation and interface.

```
┌──────────────────────────────────────────────────────────────┐
│       Peer Routing                                           │
│                                                              │
│┌──────────────┐┌────────────────┐┌──────────────────────────┐│
││ kad-routing  ││ mDNS-routing   ││ other-routing-mechanisms ││
││              ││                ││                          ││
││              ││                ││                          ││
│└──────────────┘└────────────────┘└──────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

### 4.1.1 kad-routing

kad-routing implements the Kademlia Routing table, where each peer holds a set of k-buckets, each of them containing several `PeerInfo` objects from other peers in the network.

### 4.1.2 mDNS-routing

mDNS-routing uses mDNS probes to identify if local area network peers have a given key or they are simply present.

## 4.2 Swarm

### 4.2.1 Stream Muxer

The stream muxer must implement the interface offered by [interface-stream-muxer](https://github.com/diasdavid/interface-stream-muxer).

### 4.2.2 Protocol Muxer

Protocol muxing is handled on the application level instead of the conventional way at the port level (where different services/protocols listen at different ports). This enables us to support several protocols to be muxed in the same socket, saving the cost of doing NAT traversal for more than one port.

Protocol multiplexing is done through [`multistream`](https://github.com/jbenet/multistream), a protocol to negotiate different types of streams (protocols) using [`multicodec`](https://github.com/jbenet/multicodec).

### 4.2.3 Transport

### 4.2.4 Crypto

### 4.2.5 Identify

**Identify** is one of the protocols mounted on top of Swarm, our Connection handler. However, it follows and respects the same pattern as any other protocol when it comes to mounting it on top of Swarm. Identify enables us to trade listened addresses and observed addresses between peers, which is crucial for the working of libp2p. Since every socket open implements `REUSEPORT`, an address observed by another peer can enable a third peer to connect to us, since the port will be already open and redirect to us on a NAT.

### 4.2.6 Relay

See [Circuit Relay](/relay).

## 4.3 Distributed Record Store

### 4.3.1 Record

Follows [IPRS spec](/IPRS.md).

### 4.3.2 abstract-record-store

### 4.3.3 kad-record-store

### 4.3.4 mDNS-record-store

### 4.3.5 s3-record-store

## 4.4 Discovery

### 4.4.1 mDNS-discovery

mDNS-discovery is a Discovery Protocol that uses [mDNS](https://en.wikipedia.org/wiki/Multicast_DNS) over local area networks. It emits mDNS beacons to find if there are more peers available. Local area network peers are very useful to peer-to-peer protocols, because of their low latency links.

mDNS-discovery is a standalone protocol and does not depend on any other `libp2p` protocol. mDNS-discovery can yield peers available in the local area network, without relying on other infrastructure. This is particularly useful in intranets, networks disconnected from the Internet backbone, and networks which temporarily lose links.

mDNS-discovery can be configured per-service (i.e. discover only peers participating in a specific protocol, like IPFS), and with private networks (discover peers belonging to a private network).

We are exploring ways to make mDNS-discovery beacons encrypted (so that other nodes in the local network cannot discern what service is being used), though the nature of mDNS will always reveal local IP addresses.

**Privacy note:** mDNS advertises in local area networks, which reveals IP addresses to listeners in the same local network. It is not recommended to use this with privacy-sensitive applications or oblivious routing protocols.

#### 4.4.2 random-walk

Random-Walk is a Discovery Protocol for DHTs (and other protocols with routing tables). It makes random DHT queries in order to learn about a large number of peers quickly. This causes the DHT (or other protocols) to converge much faster, at the expense of a small load at the very beginning.

#### 4.4.3 bootstrap-list

Bootstrap-List is a Discovery Protocol that uses local storage to cache the addresses of highly stable (and somewhat trusted) peers available in the network. This allows protocols to "find the rest of the network". This is essentially the same way that DNS bootstraps itself (though note that changing the DNS bootstrap list -- the "dot domain" addresses -- is not easy to do, by design).

  - The list should be stored in long-term local storage, whatever that means to the local node (e.g. to disk).
  - Protocols can ship a default list hardcoded or along with the standard code distribution (like DNS).
  - In most cases (and certainly in the case of IPFS) the bootstrap list should be user configurable, as users may wish to establish separate networks, or place their reliance and trust in specific nodes.

## 4.5 Messaging

#### 4.5.1 PubSub

See [`pubsub/`](pubsub/) and [`pubsub/gossipsub/`](pubsub/gossipsub/).


## 4.6 Naming

#### 4.6.1 IPRS

[IPRS spec](/IPRS.md)

#### 4.6.2 IPNS
