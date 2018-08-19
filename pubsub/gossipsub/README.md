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
- [In the beginning was floodsub](#in-the-beginning-was-floodsub)
  * [Ambient Peer Discovery](#ambient-peer-discovery)
  * [Flood routing](#flood-routing)
  * [Retrospective](#retrospective)
- [Controlling the flood](#controlling-the-flood)
  * [randomsub: A random message router](#randomsub-a-random-message-router)
  * [meshsub: An overlay mesh router](#meshsub-an-overlay-mesh-router)
- [The gossipsub protocol](#the-gossipsub-protocol)
- [Protobuf](#protobuf)

<!-- tocstop -->

## Implementation status

- Go: [libp2p/go-floodsub#67](https://github.com/libp2p/go-floodsub/pull/67) (experimental)
- JS: not yet started
- Rust: not yet started
- Gerbil: [vyzo/gerbil-simsub](https://github.com/vyzo/gerbil-simsub) (simulator)


## In the beginning was floodsub

The initial pubsub experiment in libp2p was `floodsub`.
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
the router maintains a timed cache of previous messages, so that seen
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

In order to scale pubsub without excessive bandwidth waste or peer
overload, we need a router that bounds the degree of each peer and
globally controls the amplification factor.

### randomsub: A random message router

Let's first consider the simplest bounded floodsub variant, which we
call `randomsub`. In this construction, the router is still stateless
apart from a list of known peers in the topic. But instead of
forwarding messages to all peers, it forwards to a random subset up to
`D` peers, where `D` is the desired degree of the network.

The problem with this construction is that the message propagation
patterns are non-deterministic. This results to extreme message route
instability which is an undesirable property for many applications.

### meshsub: An overlay mesh router

Nonetheless, the idea of limiting the flow of messages to a random
subset of peers is solid. But instead of randomly selecting peers on a
per message basis, we can form an overlay mesh where each peer
forwards to a subset of its peers on a stable basis. We construct a
router in this fashion, dubbed `meshsub`.

Each peer maintains its own view of the mesh for each topic, which is
a list of bidirectional links to other peers.  That is, in steady
state, whenever a peer A is in the mesh of peer B, then peer B is also
in the mesh of peer A.

The overlay is initially constructed in a random fashion. Whenever a
peer joins a topic, then it selects `D` peers (in the topic) at random
and adds them to the mesh, notifying them with a control message. When
it leaves the topic, it notifies its peers and forgets the mesh for
the topic.

The mesh is maintained with the following periodic stabilization
algorithm:

```
at each peer:
  loop:
    if |peers| < D_low:
       select D - |peers| non-mesh peers at random and add them to the mesh
    if |peers| > D_high:
       select |peers| - D mesh peers at random and remove them from the mesh
    sleep t
```
The parameters of the algorithm are `D` which is the target degree,
and two relaxed degree parameters `D_low` and `D_high` which represent
admissible mesh degree bounds.


## The gossipsub protocol


## Protobuf
