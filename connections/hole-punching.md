# Hole punching


| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r0, 2021-04-27  |

Authors: [@mxinden]

Interest Group: [@vyzo], [@vasco], [@stebalien], [@aarsh], [@raulk]

[@aarsh]: https://github.com/aarsh
[@mxinden]: https://github.com/mxinden
[@raulk]: https://github.com/raulk
[@stebalien]: https://github.com/stebalien
[@vasco]: https://github.com/vasco
[@vyzo]: https://github.com/vyzo

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Overview

This document describes the process of **establishing direct connections between
two libp2p peers in which one or both are behind firewalls and/or NATs**. The
document derives many concepts from the _Interactive Connectivity Establishment_
(ICE) standard. The most notable deviation from ICE is the goal of hole punching
in a decentralized fashion.

Additional goals:
- Interoperability across platforms and implementations.
- Shared abstractions reusable across transport protocols.

This document does not reflect the status quo, but much rather the high level
long term vision. To gain an overview of the status quo, see [issue #312].

[issue #312]: https://github.com/libp2p/specs/issues/312

## Definitions

### Reachability

This document distinguishes between two types of hosts: publicly reachable and
non-publicly reachable hosts. Addresses of the former type of hosts can be
directly dialed on the public Internet. Addresses of the latter type of hosts
can only be dialed through a relay protocol, or through some means of hole
punching. The document refers to publicly reachable hosts as _public_ and
non-publicly reachable hosts as _private_.

Note: (For now) this document ignores the case where two hosts are not publicly
reachable, but operate within the same local layer 2 or layer 3 network.
Oftentimes in such cases direct connections between the two hosts can be
established without prior hole punching.

### Platforms

We differentiate two types of platforms: _browser_ and _non-browser_.

On _non-browser_ platforms a libp2p implementation has extensive control over
the (TCP or UDP) network socket, e.g. controlling port-reuse. The libp2p
implementation controls the full transport security stack. Furthermore, unless
run behind a Firewall or NAT, _non-browser_ platform hosts can be directly
dialed through their publicly reachable addresses.

On the contrary, on _browser_ platforms a libp2p implementation does not manage the
network socket nor does it control the transport security stack. In addition to
these restrictions, hosts running on _browser_ platforms can not be directly
dialed.

### Implementations

There are multiple libp2p implementations, e.g. go-libp2p, js-libp2p and
rust-libp2p. It is important to keep in mind that in some cases platforms and
implementations are not matched one-to-one, e.g. the two implementations
js-libp2p and rust-libp2p can run on both the _browser_ and _non-browser_
platform types.

### Protocol types

#### Transport

A transport protocol allows basic host-to-host communication. Examples are TCP,
Websockets building on top of TCP, as well as the protocols layered over UDP
namely QUIC and WebRTC.

#### Relay

A relay protocol allows two clients to communicate, routing data via a relay
server, instead of using a direct connection. Examples of relay protocols are
[TURN], [circuit relay v1][circuit-relay-v1] and [circuit relay
v2][circuit-relay-v2].

#### STUN-like

STUN-like protocols allow a host to detect whether they are running behind a
firewall and/or NAT and if so they enable a host to discover their perceived
public IP addresses as well as their port mapping. Examples of STUN-like
protocols are [STUN] (hence the name) and [AutoNAT].

#### Coordination

Coordination protocols run on top of some relay protocol enabling two hosts to
coordinate the hole punching process. Examples of coordination protocols are the
[Session Description Protocol (SDP)][SDP] and [Direct Connection Upgrade through
Relay][DCUTR].

### Discovery mechanism

A discovery mechanism allows a node to discover peers in the network. A node can
use such mechanism e.g. to find peers at random, to learn external addresses of
peers, or more targeted to discover peers that provide a specific service. Among
others one can build a discovery mechanism on top of the libp2p [Kademlia] and
[Gossipsub] protocol. [IPFS's usage of a Kademlia DHT][ipfs-kademlia] is a
good example of a discovery mechanism.

Further details on discovery mechanisms are out of scope for this document. The
descriptions below will assume a generic _external discovery mechanism_ to be
available.

## Vision

When it comes to establishing direct connections one needs to differentiate by
platform type (browser / non-browser) as as well as routability (public /
private). The below describes on a high level how to establish direct
connections across the various permutations of the two dimensions.

### Public Non-Browser (A) to Public Non-Browser (B)

This is the ideal case, where both hosts can be directly dialed, thus there
being no need for hole punching. The two hosts should use either TCP or QUIC to
communicate directly.

### Private Non-Browser (A) to Public Non-Browser (B)

Given that B is publicly reachable, A can establish a direct TCP or QUIC
connection to B.

### Private Browser (A) to Public Non-Browser (B)

Given that B is publicly reachable A can establish a direct connection, though
multiple restrictions are imposed by the browser platform type of A:

- The only transport protocol allowing direct connections on browser platforms
  is WebSockets. Thus B has to support the WebSocket transport protocol.

- Browser platforms do not allow insecure WebSocket connections, thus B has to
  have a valid TLS certificate to offer secure Websocket communication.

In cases where B does not fulfill both of these requirements, additional steps
as detailed in [Private Browser (A) to Private Non-Browser
(B)](#private-browser-a-to-private-non-browser-b) are necessary.

### Public or Private Non-Browser (A) to Private Non-Browser (B)

In order to establish a direct connection from A to B, one needs to utilize some
means of firewall / NAT hole punching. Given the permissiveness of non-browser
platforms there are many ways to achieve this goal, with the below being one of
them.

- B uses the [AutoNat] protocol to determine whether it is running behind
  firewalls and/or NATs and in the latter case what type of NATs.
  
  Note: Hole punching fails if either A or B runs behind a [symmetric
  NAT][symmetric-nat].

- B establishes a TCP or QUIC connections to one or more relay servers and
  listens for incoming connection requests via the [circuit relay v2
  protocol][circuit-relay-v2]. Once B established a reservation at one or more
  relay servers, B can advertise its relayed addresses (e.g.
  `/ip4/.../tcp/.../p2p/QmRelay`) via some external mechanism.

  Note on decentralization: Given the low resource requirements of the [circuit
  relay v2 protocol][circuit-relay-v2] any public host can serve as a relay
  server.

- A discovers the relayed address of B through some external mechanism. Given
  the relayed address, A can establish a relayed connection to B via the [circuit
  relay v2 protocol][circuit-relay-v2] protocol over TCP or QUIC. A and B can
  then run the [Direct Connection Upgrade through Relay][DCUTR] protocol over
  the relayed connection to coordinate TCP or QUIC hole punching in the best
  case establishing a direction connection.

For more details see the [Project Flare][project-flare] project proposal.

### Private Browser (A) to Private Non-Browser (B)

As mentioned above browser platforms (1) do not allow libp2p implementations to
manage the network sockets nor (2) do they allow managing the transport security
stack, thus not allowing _insecure_ connections.

- Both A and B discover [STUN] servers through some external mechanism. Given
  that two hosts do not need to share the same [STUN] server to establish a
  WebRTC connection, this does not require any coordination beyond the [STUN]
  server discovery process.

- B establishes a TCP or QUIC connections to one or more relay servers and
  listens for incoming connection requests via the [circuit relay v2
  protocol][circuit-relay-v2]. Once B establishes a reservation at one or more
  relay servers, B can advertise its relayed addresses (e.g.
  `/ip4/.../tcp/.../p2p/QmRelay`) via some external mechanism.

  Note: Given that browser platforms do not allow insecure connections
  to non-localhost addresses, the relay server needs to listen on
  TLS secured Websockets (`/ip4/.../tcp/.../wss/p2p/QmRelay`).  

- A discovers the relayed address of B through some external mechanism. Given
  B's relayed address A can establish a Websocket connection to the relay server
  of B. With the help of the [circuit relay v2 protocol][circuit-relay-v2]
  protocol A and B can exchange [SDP] messages eventually allowing A B and to
  establish a WebRTC connection.

### Public or Private Non-Browser (A) to Private Browser (B)

- Both A and B discover [STUN] servers through some external mechanism. Given
  that two hosts do not need to share the same [STUN] server to establish a
  WebRTC connection, this does not require any coordination beyond the [STUN]
  server discovery process.

- B establishes a Websocket connections to one or more relay server and listens
  for incoming connection requests via the [circuit relay v2
  protocol][circuit-relay-v2]. Once B established a reservation at one or more
  relay servers, B can advertise its relayed addresses (e.g.
  `/ip4/.../tcp/.../p2p/QmRelay`) via some external mechanism.

- A discovers the relayed address of B through some external mechanism. Given
  B's relayed address A can establish a TCP or QUIC connection to the relay
  server of B. With the help of the [circuit relay v2
  protocol][circuit-relay-v2] protocol A and B can exchange [SDP] messages
  eventually allowing A B and to establish a WebRTC connection.

### Private Browser (A) to Private Browser (B)

- Both A and B discover [STUN] servers through some external mechanism. Given
  that two hosts do not need to share the same [STUN] server to establish a
  WebRTC connection, this does not require any coordination beyond the [STUN]
  server discovery.

- B establishes a Websocket connections to one or more relay servers and listens
  for incoming connection requests via the [circuit relay v2
  protocol][circuit-relay-v2]. Once B established a reservation at one or more
  relay servers, B can advertise its relayed addresses (e.g.
  `/ip4/.../tcp/.../wss/p2p/QmRelay`) via some external mechanism.

- A discovers the relayed `/wss/` address of B through some external mechanism. Given
  B's relayed address A can establish a Websocket connection to the relay server
  of B. With the help of the [circuit relay v2 protocol][circuit-relay-v2]
  protocol A and B can exchange [SDP] messages eventually allowing A B and to
  establish a WebRTC connection.

## FAQ

- **Why not connect to a relay server via WebRTC instead of Websockets?**

  WebRTC needs some mechanism to exchange [SDP] messages. Unless there is some
  other means to exchange these [SDP] messages to a relay server, one has to use
  Websockets.

- **What to do when hole punching fails?**

  Peers will be able to communicate via the established [circuit relay v2
  protocol][circuit-relay-v2] connection. Though this connection is limited in
  both transfered bytes and time. For now, upper layer protocols need to cope
  with the fact that full connectivity can not be guaranteed.

- **Why use both [AutoNAT] and [STUN], why not settle on one for both TCP / QUIC
  and WebRTC based hole punching?**
  
  On browser platforms libp2p implementations do not control the local WebRTC
  stack. This same stack can only operate with [STUN] and not [AutoNAT]. One
  could use [STUN] instead of [AutoNAT] for TCP and QUIC hole punching though.

[TURN]: https://en.wikipedia.org/wiki/Traversal_Using_Relays_around_NAT
[STUN]: https://en.wikipedia.org/wiki/STUN
[AutoNAT]: https://github.com/libp2p/specs/issues/180
[SDP]: https://en.wikipedia.org/wiki/Session_Description_Protocol
[circuit-relay-v1]: https://github.com/libp2p/specs/tree/master/relay
[circuit-relay-v2]: https://github.com/libp2p/specs/issues/314
[DCUTR]: https://github.com/libp2p/specs/pull/173
[project-flare]: https://github.com/protocol/web3-dev-team/pull/21
[symmetric-nat]: https://dh2i.com/kbs/kbs-2961448-understanding-different-nat-types-and-hole-punching/
[ipfs-kademlia]: https://docs.ipfs.io/concepts/dht/
[Kademlia]: https://github.com/libp2p/specs/pull/108/
[Gossipsub]: ../pubsub/gossipsub/README.md
