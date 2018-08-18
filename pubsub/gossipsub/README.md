# gossipsub: An extensible baseline pubsub protocol

Revision:

Author: vyzo

This is the specification for an extensible baseline pubsub protocol,
based on randomized topic meshes and gossip. It is a general purpose
pubsub protocol with moderate amplification factors and good scaling
properties. The protocol is designed to be extensible by more
specialized routers, which may add protocol messages and gossip in
order to provide behaviour optimized for specific application
profiles.

<!-- toc -->

- [Implementation status](#implementation-status)
- [General purpose pubsub for libp2p](#general-purpose-pubsub-for-libp2p)
- [In the beginning was floodsub](#in-the-beginning-was-floodsub)
  * [Ambient Peer Discovery](#ambient-peer-discovery)
  * [Flood routing](#flood-routing)
  * [Retrospective](#retrospective)
- [Controlling the flood](#controlling-the-flood)
  * [A random mesh algorithm](#a-random-mesh-algorithm)
  * [Gossip propagation](#gossip-propagation)
- [The gossipsub protocol](#the-gossipsub-protocol)
- [Protobuf](#protobuf)

<!-- tocstop -->

## Implementation status

- Go: [libp2p/go-floodsub#67](https://github.com/libp2p/go-floodsub/pull/67) (experimental)
- JS: not yet started
- Rust: not yet started
- Gerbil: [vyzo/gerbil-simsub](https://github.com/vyzo/gerbil-simsub) (simulator)

## General purpose pubsub for libp2p


## In the beginning was floodsub

The initial pubsub experiment in libp2p was floodsub.
It implements pubsub in the most basic manner, with two defining aspects:
- ambient peer discovery.
- most basic routing; flooding.

### Ambient Peer Discovery

With ambient peer discovery, the function is pushed outside the scope
of the protocol. Instead, it relies on ambient connection events to
perform peer discovery via protocol identification. Whenever a new
peer is connected, the protocol checks to see if the peer implements
floodsub, and if so it sends a hello packet announcing the topics it
is currently subscribing.

This allows the peer to maintain soft overlays for all topics of
interest. The overlay is maintained by exchanging subscription
control messages whenever there is a change in the topic list. The
subscription messages are not propagated further, so each peer
maintains a topic view of its direct peers only. Whenever a peer
disconnects, it is removed from the overlay.

Ambient peer discovery can be driven by arbitrary external means, which
allows orthogonal development and no external dependencies for the protocol
implementation.

These are a couple of options we are exploring as canonical approaches
for the discovery driver:
- DHT lookups using provider records.
- Rendezvous through known or dynamically discovered rendezvous points.

### Flood routing

With flooding, routing is almost trivial: for each incoming message,
forward to all known peers in the topic. There is a bit of logic, as
the router maintains a timed cache of known messages, so that seen
messages are not further forwarded. It also never forwards a message
back to the source or the peer that forwarded the message.

### Retrospective

Evaluating floodsub as a viable pubsub protocol reveals the following
highly desirable properties:
- it is straightforward to implement.
- it minimizes latency; messages are delivered across minimum latency
  paths, modulo overly connectivity.
- it is highly robust; there is very little maintenance logic or state.

The problem however is that messages don't just follow the minimum
latency paths; they follow all edges, thus creating a flood. The
outbound degree of the network is unbounded, restricted solely from
connectivity. This creates a problem for individual densely connected
nodes, as they may have large number of connected peers and cannot
afford the bandwidth to forward all these pubsub messages.  Similary,
the amplification factor is only bounded by the sum of degrees of all
nodes in the overlay, which creates a scaling problem for densely
connected overlays at large.


## Controlling the flood

### A random mesh algorithm

### Gossip propagation


## The gossipsub protocol


## Protobuf
