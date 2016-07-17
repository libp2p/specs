2 An analysis the state of the art in network stacks
====================================================

This section presents to the reader an analysis of the available protocols and architectures for network stacks. The goal is to provide the foundations from which to infer the conclusions and understand why `libp2p` has the requirements and architecture that it has.

## 2.1 The client-server model

The client-server model indicates that both parties at the ends of the channel have different roles, that they support different services and/or have different capabilities, or in other words, that they speak different protocols.

Building client-server applications has been the natural tendency for a number of reasons:

- The bandwidth inside a data center is considerably higher than that available for clients to connect to each other.
- Data center resources are considerably cheaper, due to efficient usage and bulk stocking.
- It makes it easier for the developer and system admin to have fine grained control over the application.
- It reduces the number of heteregeneus systems to be handled (although the number is still considerable).
- Systems like NAT make it really hard for client machines to find and talk with each other, forcing a developer to perform very clever hacks to traverse these obstacles.
- Protocols started to be designed with the assumption that a developer will create a client-server application from the start.

We even learned how to hide all the complexity of a distributed system behind gateways on the Internet, using protocols that were designed to perform a point-to-point operation, such as HTTP, making it opaque for the application to see and understand the cascade of service calls made for each request.

`libp2p` offers a move towards dialer-listener interactions, from the client-server listener, where it is not implicit which of the entities, dialer or listener, has which capabilities or is enabled to perform which actions. Setting up a connection between two applications today is a multilayered problem to solve, and these connections should not have a purpose bias, and should instead support several other protocols to work on top of the established connection. In a client-server model, a server sending data without a prior request from the client is known as a push model, which typically adds more complexity; in a dialer-listener model in comparison, both entities can perform requests independently.

## 2.2 Categorizing the network stack protocols by solutions

Before diving into the `libp2p` protocols, it is important to understand the large diversity of protocols already in wide use and deployment that help maintain today's simple abstractions. For example, when one thinks about an HTTP connection, one might naively just think that HTTP/TCP/IP are the main protocols involved, but in reality many more protocols participate, depending on the usage, the networks involved, and so on. Protocols like DNS, DHCP, ARP, OSPF, Ethernet, 802.11 (Wi-Fi) and many others get involved. Looking inside ISPs' own networks would reveal dozens more.

Additionally, it's worth noting that the traditional 7-layer OSI model characterization does not fit `libp2p`. Instead, we categorize protocols based on their role, i.e. the problem they solve. The upper layers of the OSI model are geared towards point-to-point links between applications, whereas the `libp2p` protocols speak more towards various sizes of networks, with various properties, under various different security models. Different `libp2p` protocols can have the same role (in the OSI model, this would be "address the same layer"), meaning that multiple protocols can run simultaneously, all addressing one role (instead of one-protocol-per-layer in traditional OSI stacking). For example, bootstrap lists, mDNS, DHT discovery, and PEX are all forms of the role "Peer Discovery"; they can coexist and even synergize.

### 2.2.1 Establishing the physical link

- Ethernet
- Wi-Fi
- Bluetooth
- USB

### 2.2.2 Addressing a machine or process

- IPv4
- IPv6
- Hidden addressing, like SDP

### 2.2.3 Discovering other peers or services

- ARP
- DHCP
- DNS
- Onion

### 2.2.4 Routing messages through the network

- RIP(1, 2)
- OSPF
- PPP
- Tor
- I2P
- cjdns

### 2.2.5 Transport

- TCP
- UDP
- UDT
- QUIC
- WebRTC data channel

### 2.2.6 Agreed semantics for applications to talk to each other

- RMI
- Remoting
- RPC
- HTTP

## 2.3 Current shortcommings

Although we currently have a panoply of protocols available for our services to communicate, the abundance and variety of solutions creates its own problems. It is currently difficult for an application to be able to support and be available through several transports (e.g. the lack of TCP/UDP stack in browser applications).

There is also no 'presence linking', meaning that there isn't a notion for a peer to announce itself in several transports, so that other peers can guarantee that it is always the same peer.
