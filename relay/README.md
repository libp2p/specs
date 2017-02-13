# Circuit Relay

> Circuit Switching in libp2p

Table of Contents
- [Overview](#overview)
- [Dramatization](#dramatization)
- [Addressing](#addressing)
- [Wire protocol](#wire-protocol)
- [Interfaces](#interfaces)
- [Removing existing relay protocol](#removing-existing-relay-protocol)

Note: as of 8-Feb-2017, this protocol isn't implemented yet, neither in go-libp2p nor js-libp2p.
We aim to implement and ship it [during the "ipfs in web browsers" sprint](https://github.com/ipfs/pm/issues/351) starting 12-Feb-2017.

## Overview

The circuit relay is a means of establishing connectivity between
libp2p nodes (such as IPFS) that wouldn't otherwise be able to connect to each other.

This helps in situations where nodes are behind NAT or reverse proxies,
or simply don't support the same transports (e.g. go-ipfs vs. browser-ipfs).
libp2p already has modules for NAT ([go-libp2p-nat](https://github.com/libp2p/go-libp2p-nat)),
but these don't always do the job, just because NAT traversal is complicated.
That's why it's useful to have a simple relay protocol.

One node asks a relay node to connect to another node on its behalf.
The relay node shortcircuits its streams to the two nodes,
and they are then connected through the relay.
This relayed connection behaves just like a regular connection would,
because it is in fact just that,
but over an existing swarm stream with another peer, instead of e.g. TCP.

Relayed connections are end-to-end encrypted just like regular connections.

The circuit relay is both a tunneled transport and a mounted swarm protocol.
The transport is the means of *establishing* and *accepting* connections,
and the swarm protocol is the means to *relaying* connections.

```
+-------+    /ip4/.../tcp/.../ws/ipfs/QmRelay    +---------+    /ip4/.../tcp/.../ipfs/QmTwo        +-------+
| QmOne | <------------------------------------> | QmRelay | <-----------------------------------> | QmTwo |
+-------+    (/ipfs/relay/circuit multistream)   +---------+   (/ipfs/relay/circuit multistream)   +-------+
      ^                                            +-----+                                           ^
      |                                            |     |                                           |
      |            /p2p-circuit/QmTwo              |     |                                           |
      +--------------------------------------------+     +-------------------------------------------+
```

TODO: the stream codec should be called `/libp2p/relay/circuit` instead.

Note: we're using the `/p2p` multiaddr protocol instead of `/ipfs` in this document.
`/ipfs` is currently the canonical way of addressing a libp2p or IPFS node,
but given the growing non-IPFS usage of libp2p, we'll migrate to using `/p2p`.

Note: at the moment we're not including a mechanism for discovering relay nodes.
For the time being, they should be configured statically.


## Dramatization

Cast:
- QmOne, the dialing node (browser).
- QmTwo, the listening node (go-ipfs).
- QmRelay, a node which speaks the circuit relay protocol (go-ipfs or js-ipfs).

Scene 1:
- QmOne wants to connect to QmTwo,
  and through peer routing has acquired a set of addresses of QmTwo.
- QmTwo doesn't support any of the transports used by QmOne.
- Awkward silence.

Scene 2:
- All three nodes have learned to speak the `/ipfs/relay/circuit` protocol.
- QmRelay is configured to allow relaying connections between other nodes.
- QmOne is configured to use QmRelay for relaying.
- QmOne automatically added `/p2p-circuit/ipfs/QmTwo` to its set of QmTwo addresses.
- QmOne tries to connect via relaying, because it shares this transport with QmTwo.
- A lively and prolonged dialogue ensues.


## Addressing

`/p2p-circuit` multiaddrs don't carry any meaning of their own.
They need to encapsulate a `/p2p` address, or
be encapsulated in a `/p2p` address, or both.

As with all other multiaddrs, encapsulation of different protocols
determines which metaphorical tubes to connect to each other.

A few examples:

- `/p2p-circuit/p2p/QmTwo`
  - Dial QmTwo, through any available relay node.
  - The relay node will use peer routing to find an address for QmTwo.
- `/p2p/QmRelay/p2p-circuit/p2p/QmTwo`
  - Dial QmTwo, through QmRelay.
  - Use peer routing to find an address for QmRelay.
  - The relay node will also use peer routing, to find an address for QmTwo.
- `/p2p-circuit/ip4/../tcp/../p2p/QmTwo`
  - Dial QmTwo, through any available relay node,
    but force the relay node to use the encapsulated `/ip4` multiaddr for connecting to QmTwo.
  - We'll probably not support forced addresses for now, just because it's complicated.
- `/ip4/../tcp/../p2p/QmRelay/p2p-circuit`
  - Listen for connections relayed through QmRelay.
  - Includes info for connecting to QmRelay.
  - Also makes QmRelay available for relayed dialing, based on how listeners currently relate to dialers.
- `/p2p/QmRelay/p2p-circuit`
  - Same as previous example, but use peer routing to find an address for QmRelay.
- `/p2p-circuit/p2p/QmTwo/p2p-circuit/p2p/QmThree`
  - Dial QmThree, through a relayed connection to QmTwo.
  - The relay nodes will use peer routing to find an address for QmTwo and QmThree.
  - We'll probably not support nested relayed connections for now, there are edge cases to think of.
- `/ip4/../tcp/../p2p/QmRelay/p2p-circuit/p2p/QmTwo`
  - Dial QmTwo, through QmRelay.
  - Includes info for connecting to QmRelay.
  - The relay node will use peer routing to find an address for QmTwo.
- `/p2p-circuit`
  - Use relay discovery to find a suitable relay node. (Neither specified nor implemented.)
  - Listen for relayed connections.
  - Dial through the discovered relay node for any `/p2p-circuit` multiaddr.

TODO: figure out forced addresses.
TODO: figure out nested relayed connections.

## Wire format

The wire format (or codec) is named `/ipfs/relay/circuit` and is simple.
A variable-length header consisting of two length-prefixed multiaddrs
is followed by a bidirectional stream of arbitrary data,
and the eventual closing of the stream.

```
<src><dst><data>

 ^    ^    ^
 |    |    |
 |    |    +-- bidirectional data stream
 |    |         (usually /multistream-select in the case of /p2p multiaddrs)
 |    |
 |    +------- multiaddr of the listening node
 |
 +------------ multiaddr of the dialing node
```

After getting a stream to the relay node from its libp2p swarm,
the dialing transport writes the header to the stream.
The relaying node reads the header, gets a stream to the destination node,
then writes the header to the destination stream and shortcircuits the two streams.

Each relayed connection corresponds to two multistreams,
one between QmOne and QmRelay, the other between QmRelay and QmTwo.

Implementation details:
- The relay node has the `Swarm.EnableRelaying` config option enabled
- The relay node allows only one relayed connection between any two nodes.
- The relay node validates the `src` header field.
- The listening node validates the `dst` header field.


## Interfaces

As explained above, the relay is both a transport (`tpt.Transport`)
and a mounted stream protocol (`p2pnet.StreamHandler`).
In addition it provides a means of specifying relay nodes to listen/dial through.

TODO: the usage of p2pnet.StreamHandler is a little bit off, but it gets the point across.

```go
import (
  tpt "github.com/libp2p/go-libp2p-transport"
  p2phost "github.com/libp2p/go-libp2p-host"
  p2pnet "github.com/libp2p/go-libp2p-net"
  p2proto "github.com/libp2p/go-libp2p-protocol"
)

const ID p2proto.ID = "/ipfs/relay/circuit/0.1.0"

type CircuitRelay interface {
  tpt.Transport
  p2pnet.StreamHandler

  EnableRelaying(enabled bool)
}

fund NewCircuitRelay(h p2phost.Host)
```


### Removing existing relay protocol

Note that there is an existing swarm protocol colloqiually called relay.
It lives in the go-libp2p package and is named `/ipfs/relay/line/0.1.0`.

- Introduced in ipfs/go-ipfs#478 (28-Dec-2014).
- No changes except for ipfs/go-ipfs@de50b2156299829c000b8d2df493b4c46e3f24e9.
  - Changed to use multistream muxer.
- Shortcomings
  - No end-to-end encryption.
  - No rate limiting (DoS by resource exhaustion).
  - Doesn't verify src id in ReadHeader(), easy to fix.
- Capable of *accepting* connections, and *relaying* connections.
- Not capable of *connecting* via relaying.

Since the existing protocol is incomplete, insecure, and certainly not used,
we can safely remove it.
