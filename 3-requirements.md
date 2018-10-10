3 Requirements and considerations
=================================

## 3.1 Transport agnostic

`libp2p` is transport agnostic, so it can run over any transport protocol. It does not even depend on IP; it may run on top of NDN, XIA, and other new Internet architectures.

In order to reason about possible transports, `libp2p` uses [multiaddr](https://github.com/multiformats/multiaddr), a self-describing addressing format that describes the stack of protocols used to send packets to another peer. This makes it possible for `libp2p` to treat addresses opaquely everywhere in the system, and have support for various transport protocols in the network layer. The actual format of addresses in `libp2p` is `p2p-addr`, a multiaddr that ends with a peer id. For example, these are all valid `p2p-addrs`:

```
# P2P over TCP over IPv6 (typical TCP)
/ip6/fe80::8823:6dff:fee7:f172/tcp/4001/p2p/QmYJyUMAcXEw1b5bFfbBbzYu5wyyjLMRHXGUkCXpag74Fu

# P2P over uTP over UDP over IPv4 (UDP-shimmed transport)
/ip4/162.246.145.218/udp/4001/utp/p2p/QmYJyUMAcXEw1b5bFfbBbzYu5wyyjLMRHXGUkCXpag74Fu

# P2P over TCP over IPv6 with QUIC
/ip6/fe80::8823:6dff:fee7:f172/tcp/4001/quic/p2p/QmYJyUMAcXEw1b5bFfbBbzYu5wyyjLMRHXGUkCXpag74Fu

# P2P over IPv6 (unreliable)
/ip6/fe80::8823:6dff:fee7:f172/p2p/QmYJyUMAcXEw1b5bFfbBbzYu5wyyjLMRHXGUkCXpag74Fu

# P2P over TCP over IPv4 over TCP over IPv4 (proxy)
/ip4/162.246.145.218/tcp/7650/ip4/192.168.0.1/tcp/4001/p2p/QmYJyUMAcXEw1b5bFfbBbzYu5wyyjLMRHXGUkCXpag74Fu

# P2P over Ethernet (no IP)
/ether/ac:fd:ec:0b:7c:fe/p2p/QmYJyUMAcXEw1b5bFfbBbzYu5wyyjLMRHXGUkCXpag74Fu
```

**Note:** At this time, no unreliable transport implementations exist. The protocol's interface for defining and using unreliable transport has not been defined. For more information on unreliable vs reliable transport, see [here](http://www.inetdaemon.com/tutorials/basic_concepts/communication/reliable_vs_unreliable.shtml). In the context of WebRTC, CTRL+F "reliable" [here](https://www.html5rocks.com/en/tutorials/webrtc/basics/#signaling).

## 3.2 Multi-multiplexing

The `libp2p` protocol is a collection of multiple protocols. In order to conserve resources, and to make connectivity easier, `libp2p` can perform all its operations through a single port, such as a TCP or UDP port, depending on the transports used. `libp2p` can multiplex its many protocols through point-to-point connections. This multiplexing is for both reliable streams and unreliable datagrams.

`libp2p` is pragmatic. It seeks to be usable in as many settings as possible, to be modular and flexible to fit various use cases, and to force as few choices as possible. Thus the `libp2p` network layer provides what we're loosely referring to as "multi-multiplexing":

- can multiplex multiple listen network interfaces
- can multiplex multiple transport protocols
- can multiplex multiple connections per peer
- can multiplex multiple client protocols
- can multiplex multiple streams per protocol, per connection (SPDY, HTTP2, QUIC, SSH)
- has flow control (backpressure, fairness)
- encrypts each connection with a different ephemeral key

To give an example, imagine a single libp2p node that:

- listens on a particular TCP/IP address
- listens on a different TCP/IP address
- listens on a SCTP/UDP/IP address
- listens on a UDT/UDP/IP address
- has multiple connections to another node X
- has multiple connections to another node Y
- has multiple streams open per connection
- multiplexes streams over HTTP2 to node X
- multiplexes streams over SSH to node Y
- one protocol mounted on top of `libp2p` uses one stream per peer
- one protocol mounted on top of `libp2p` uses multiple streams per peer

Not providing this level of flexbility makes it impossible to use `libp2p` in various platforms, use cases, or network setups. It is not important that all implementations support all choices; what is critical is that the spec is flexible enough to allow implementations to use precisely what they need. This ensures that complex user or application constraints do not rule out `libp2p` as an option.

## 3.3 Encryption

Communications on `libp2p` may be:

- **encrypted**
- **clear** (not encrypted, not signed)

We take both security and performance seriously. We recognize that encryption is not viable for some in-datacenter high performance use cases.

We recommend that:

- implementations encrypt all communications by default
- implementations are audited
- unless absolutely necessary, users normally operate with encrypted communications only.

`libp2p` uses TLS or TLS-like encryption protocols.

**Note:** We do not use TLS directly, because we do not want the CA system baggage. Most TLS implementations are very big. Since the `libp2p` model begins with keys, `libp2p` only needs to apply ciphers. This is a minimal portion of the whole TLS standard.

## 3.4 NAT traversal

Network Address Translation is ubiquitous in the Internet. Not only are most consumer devices behind many layers of NAT, but most data center nodes are often behind NAT for security or virtualization reasons. As we move into containerized deployments, this is getting worse. Libp2p implementations SHOULD provide a way to traverse NATs, otherwise it is likely that operation will be affected. Even nodes meant to run with real IP addresses must implement NAT traversal techniques, as they may need to establish connections to peers behind NAT.

`libp2p` accomplishes full NAT traversal using an ICE-like protocol. It is not exactly ICE, as libp2p networks provide the possibility of relaying communications over the libp2p protocol itself, for coordinating hole-punching or even relaying communication.

It is recommended that implementations use one of the many NAT traversal libraries available, such as `libnice`, `libwebrtc`, or `natty`. However, NAT traversal must be interoperable.

## 3.5 Relay

Unfortunately, due to symmetric NATs, container and VM NATs, and other impossible-to-bypass NATs, `libp2p` MUST fallback to relaying communication to establish a full connectivity graph. To be complete, implementations MUST support relay, though it SHOULD be optional and able to be turned off by end users.

Connection relaying SHOULD be implemented as a transport, in order to be transparent to upper layers.

For an instantiation of relaying, see the [p2p-circuit transport](relay).

## 3.6 Enable several network topologies

Different systems have different requirements and with that comes different topologies. In the P2P literature we can find these topologies being enumerated as: unstructured, structured, hybrid and centralized.

Centralized topologies are the most common to find in Web Applications infrastructures, it requires for a given service or services to be present at all times in a known static location, so that other services can access them. Unstructured networks represent a type of P2P networks where the network topology is completely random, or at least non deterministic, while structured networks have a implicit way of organizing themselves. Hybrid networks are a mix of the last two.

With this in consideration, `libp2p` must be ready to perform different routing mechanisms and peer discovery, in order to build the routing tables that will enable services to propagate messages or to find each other.

## 3.7 Resource discovery

`libp2p` also solves the problem with discoverability of resources inside of a network through *records*.  A record is a unit of data that can be digitally signed, timestamped and/or used with other methods to give it an ephemeral validity. These records hold pieces of information such as location or availability of resources present in the network. These resources can be data, storage, CPU cycles and other types of services.

`libp2p` must not put a constraint on the location of resources, but instead offer ways to find them easily in the network or use a side channel.

## 3.8 Messaging

Efficient messaging protocols offer ways to deliver content with minimum latency and/or support large and complex topologies for distribution. `libp2p` seeks to incorporate the developments made in Multicast and PubSub to fulfil these needs.

## 3.9 Naming

Networks change and applications need to have a way to use the network in such a way that it is agnostic to its topology, naming appears to solve this issues.
