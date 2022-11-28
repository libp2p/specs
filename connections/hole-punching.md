# Hole punching


| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 3A              | Recommendation | Active | r1, 2022-06-13  |

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

### Trusted TLS certificate

When using TLS as a transport security protocol, one needs to differentiate
whether the source trusts the destination's TLS certificate. For example in the
browser to server use-case one needs to differentiate whether the server's TLS
certificate is in the browser's certificate chain of trust.

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
namely QUIC and [WebTransport]. In addition there is [WebRTC] which can run both
atop TCP and UDP.

#### Relay

A relay protocol allows two clients to communicate, routing data via a relay
server, instead of using a direct connection. Example of a relay protocol is the
[circuit relay v2][circuit-relay-v2] protocol.

#### STUN-like

STUN-like protocols allow a host to detect whether they are running behind a
firewall and/or NAT and if so they enable a host to discover their perceived
public IP addresses as well as their port mapping. Examples of STUN-like
protocols are [STUN] (hence the name) and [AutoNAT] in combination with
[Identify].

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

| ↓ establishing connection to → | public non-browser                                                                       | private non-browser                                                                                                                                                                                                         | private browser                                                                                                                                                                                                            |
|--------------------------------|------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **public non-browser**         | TCP or QUIC                                                                              | Destination has reservation with [circuit-relay-v2]. Source connects to destination via relay. Source triggers connection (TCP or QUIC) reversal with destination via [DCUTR].                                              | Destination has reservation with [circuit-relay-v2]. Source connects to destination via relay. Source triggers connection (WebSocket (trusted TLS cert),[WebRTC] or [WebTransport]) reversal with destination via [DCUTR]. |
| **private non-browser**        | TCP or QUIC                                                                              | Source and destination use [identify] and [AutoNAT]. Destination has reservation with [circuit-relay-v2]. Source connects to destination via relay. Source and destination coordinate hole punch (TCP or QUIC) via [DCUTR]. | Source uses [identify] and [AutoNAT]. Destination has reservation with [circuit-relay-v2]. Source connects to destination via relay. Source and destination coordinate hole punch ([WebRTC]) via [DCUTR].                  |
| **private browser**            | If source trusts destination's TLS certificate WebSocket else [WebRTC] or [WebTransport] | [WebRTC]                                                                                                                                                                                                                    | [WebRTC]                                                                                                                                                                                                                   |

## FAQ

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
[Identify]: ../identify/README.md
[SDP]: https://en.wikipedia.org/wiki/Session_Description_Protocol
[circuit-relay-v2]: https://github.com/libp2p/specs/blob/master/relay/circuit-v2.md
[DCUTR]: https://github.com/libp2p/specs/pull/173
[ipfs-kademlia]: https://docs.ipfs.io/concepts/dht/
[Kademlia]: https://github.com/libp2p/specs/blob/master/kad-dht/README.md
[Gossipsub]: ../pubsub/gossipsub/README.md
[WebRTC]: ../webrtc/README.md
[WebTransport]: https://github.com/libp2p/specs/pull/404
