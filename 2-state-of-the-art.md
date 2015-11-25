2 An analysis the State of the Art in Network Stacks
====================================================

This section presents to the reader an analysis of the available protocols and architectures for a Network Stack. The goal is to provide the foundations from which to infer the conclusions and understand what are libp2p requirements and its designed architecture.

## 2.1 The client-server model

The client-server model indicates that both parties that ends of the channel have different roles, that support different services and/or have different capabilities, or in another words, speak different protocols.

Building client-server applications has been natural tendency for a number of reasons:

- The bandwidth inside a DataCenter is considerably high compared to the one available for clients to connect between each other
- DataCenter resources are considerably cheaper, due to efficient usage and bulk stocking
- Enables easier methods for the developer and system admin to have a fine grained control over the application
- Reduces the number of heteregeneus systems to be handled (although it is still considerably high)
- Systems like NAT make it really hard for client machines to find and talk with each other, forcing a developer to perform very clever hacks to traverse these obstacles.
- Protocols started to be designed with the assumption that a developer will create a client-server application from the start.

We even learned how to hide all of the complexity of a distributed system behind gateways on the Internet, using protocols that were designed to perform a point-to-point operation, such as HTTP, making it opaque for the application to see and understand how the cascade of service calls made for each request.

`libp2p` offers a move towards dialer-listener interactions, from the client-server listener, where it is not implicit which of the entities, dialer or listener, has which capabilities or is enabled to perform which actions. Setting up a connection between two applications today is a multilayered problem to solve, and these connections should not have a purpose bias, instead support to several other protocols to work on top of the established connection. In a client-server model, a server sending data without a prior request from the client is known as a push model, which typically adds more complexity, in a dialer-listener model, both entities can perform requests independently.

## 2.2 Categorizing the network stack protocols by solutions

Before diving into the libp2p protocols, it is important to understand the large diversity of protocols already in wide use and deployment that help maintain today's simple abstractions. For example, when one thinks about an HTTP connection, one might naively just think HTTP/TCP/IP as the main protocols involved, but in reality many more participate, all depending on the usage, the networks involved, and so on. Protocols like DNS, DHCP, ARP, OSPF, Ethernet, 802.11 (WiFI), ... and many others get involved. Looking inside ISPs' own networks would reveal dozens more.

Additionally, it's worth noting that the traditional 7-layer OSI model characterization does not fit libp2p. Instead, we categorize protocols based on their role, the problem they solve. The upper layers of the OSI model are geared towards point-to-point links between applications, whereas the libp2p protocols speak more towards various sizes of networks, with various properties, under various different security models. Different libp2p protocols can have the same role (in the OSI model, this would be "address the same layer"), meaning that multiple protocols can run simultaneously, all addressing one role (instead of one-protocol-per-layer in traditional OSI stacking) For example, bootstrap lists, mDNS, DHT Discovery, and PEX are all forms of the role "Peer Discovery"; they can coexist and even synergize.

### 2.2.1 Establishing the physical Link

- ethernet
- wifi
- bluetooth
- usb

### 2.2.2 Addressing a machine or process

- IPv4
- IPv6
- Hidden Addressing, like SDP

### 2.2.3 Discovering other peers or services

- ARP
- DHCP
- DNS
- Onion

### 2.2.4 Routing messages through the Network

- RIP(1, 2)
- OSP
- PPP
- Tor
- I2P
- cjdns

### 2.2.5 Transport

- TCP
- UDP
- UDT
- QUIC
- WebRTC DataChannel

### 2.2.6 Agreed semantics for applications to talk to each other

- RMI
- Remoting
- RPC
- HTTP


## 2.3 Current Shortcommings

Although we currently have a panoply of protocols available for our services the communicate, the abundance and the variety of solutions is also its shortfall. It is currently difficult for an application to be able to support and be available through several transports (for e.g. the lack of TCP/UDP stack in browser applications).

There is also no 'presence linking', meaning that isn't a notion for a peer to announce itself in several transports, so that other peer can guarantee that it is always the same peer.
