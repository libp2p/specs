# Circuit Relay v0.1.0

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 3A              | Recommendation | Active | r1, 2018-06-03  |

Authors: [@daviddias]

Interest Group: [@lgierth], [@hsanjuan], [@jamesray1], [@vyzo], [@yusefnapora]

[@daviddias]: https://github.com/daviddias
[@lgierth]: https://github.com/lgierth
[@hsanjuan]: https://github.com/hsanjuan
[@jamesray1]: https://github.com/jamesray1
[@vyzo]: https://github.com/vyzo
[@yusefnapora]: https://github.com/yusefnapora

See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Implementations

- [js-libp2p-circuit](https://github.com/libp2p/js-libp2p-circuit)
- [go-libp2p-circuit](https://github.com/libp2p/go-libp2p-circuit)
- [rust-libp2p-relay](https://github.com/libp2p/rust-libp2p/tree/master/protocols/relay)

## Table of Contents

- [Overview](#overview)
- [Dramatization](#dramatization)
- [Addressing](#addressing)
- [Wire protocol](#wire-protocol)
- [Interfaces](#interfaces)
- [Implementation Details](#implementation-details)
- [Removing existing relay protocol](#removing-existing-relay-protocol)

## Overview

The circuit relay is a means to establish connectivity between libp2p nodes (e.g. IPFS nodes) that wouldn't otherwise be able to establish a direct connection to each other.

Relay is needed in situations where nodes are behind NAT, reverse proxies, firewalls and/or simply don't support the same transports (e.g. go-ipfs vs. browser-ipfs). Even though libp2p has modules for NAT port mapping ([go-libp2p-nat](https://github.com/libp2p/go-libp2p-nat)), this isn't always an option, nor does it always work (e.g. non-residential routers, hotspots, etc.). The circuit relay protocol exists to overcome those scenarios.

Unlike a transparent **tunnel**, where a libp2p peer would just proxy a communication stream to a destination (the destination being unaware of the original source), a circuit relay makes the destination aware of the original source and the circuit followed to establish communication between the two. This provides the destination side with full knowledge of the circuit which, if needed, could be rebuilt in the opposite direction. As a word of caution, dialing a peer back on its source addr:port usually won't work. However, most libp2p implementations (e.g. go-libp2p) enable `SO_REUSEPORT` and `SO_REUSEADDR`, and use the listening address as the local address when dialing, to facilitate this connection reversability.

Apart from that, this relayed connection behaves just like a regular connection would, but over an existing fully formed libp2p stream with another peer (instead of e.g. a raw TCP connection). Think of this as a "virtualized connection". This enables further resource efficiency and maximizes the utility of the underlying connection, as once a NAT'ted peer A has established a connection to a relay R, many peers (B1...Bn) can establish relayed connections to A over that single physical connection. The relay node acts like a circuit switcher over streams between the two nodes, enabling them to reach each other.

Relayed connections are end-to-end encrypted just like regular connections.

The circuit relay consists of both a (tunneled) libp2p transport and a libp2p protocol, mounted on the host. The libp2p transport is the means of ***establishing*** and ***accepting*** connections, and the libp2p protocol is the means to ***relaying*** connections.

```
+-----+    /ip4/.../tcp/.../ws/p2p/QmRelay    +-------+    /ip4/.../tcp/.../p2p/QmTwo       +-----+
|QmOne| <------------------------------------>|QmRelay|<----------------------------------->|QmTwo|
+-----+   (/libp2p/relay/circuit multistream) +-------+ (/libp2p/relay/circuit multistream) +-----+
     ^                                         +-----+                                         ^
     |           /p2p-circuit/QmTwo            |     |                                         |
     +-----------------------------------------+     +-----------------------------------------+
```

**Notes for the reader:**

- In this document, we use `/p2p/Qm...` multiaddrs. libp2p previously used `/ipfs/Qm...` for multiaddrs, and you'll likely see uses of this notation in the wild. `/ipfs` and `/p2p` multiaddrs are equivalent but `/ipfs` is deprecated `/p2p` should be preferred.
- You may also see `/ipfs/Qm...` used for _content-addressed pathing_ in IPFS. These are _not_ multiaddrs and this confusion is one of the many motivations for switching to `/p2p/Qm...` multiaddrs.

## Dramatization

Cast:
- QmOne, the dialing node (browser).
- QmTwo, the listening node (go-ipfs).
- QmRelay, a node which speaks the circuit relay protocol (go-ipfs or js-ipfs).

Scene 1:
- QmOne wants to connect to QmTwo, and through peer routing has acquired a set of addresses of QmTwo.
- QmTwo doesn't support any of the transports used by QmOne.
- Awkward silence.

Scene 2:
- All three nodes have learned to speak the `/ipfs/relay/circuit` protocol.
- QmRelay is configured to allow relaying connections between other nodes.
- QmOne is configured to use QmRelay for relaying.
- QmOne automatically added `/p2p-circuit/p2p/QmTwo` to its set of QmTwo addresses.
- QmOne tries to connect via relaying, because it shares this transport with QmTwo.
- A lively and prolonged dialogue ensues.

## Addressing

`/p2p-circuit` multiaddrs don't carry any meaning of their own. They need to encapsulate a `/p2p` address, or be encapsulated in a `/p2p` address, or both.

As with all other multiaddrs, encapsulation of different protocols determines which metaphorical tubes to connect to each other.

A `/p2p-circuit` circuit address, is formatted as following:

`[<relay peer multiaddr>]/p2p-circuit/<destination peer multiaddr>`

Examples:

- `/p2p-circuit/p2p/QmVT6GYwjeeAF5TR485Yc58S3xRF5EFsZ5YAF4VcP3URHt` - Arbitrary relay node that can relay to `QmVT6GYwjeeAF5TR485Yc58S3xRF5EFsZ5YAF4VcP3URHt` (target)
- `/ip4/192.0.2.0/tcp/5002/p2p/QmdPU7PfRyKehdrP5A3WqmjyD6bhVpU1mLGKppa2FjGDjZ/p2p-circuit/p2p/QmVT6GYwjeeAF5TR485Yc58S3xRF5EFsZ5YAF4VcP3URHt` - Specific relay node to relay to `QmVT6GYwjeeAF5TR485Yc58S3xRF5EFsZ5YAF4VcP3URHt` (target)

This opens the room for multiple hop relay, where the second relay is encapsulated in the first relay multiaddr, such that one relay relays to the next relay, in a daisy-chain fashion. Example:

`<1st relay>/p2p-circuit/<2nd relay>/p2p-circuit/<dst multiaddr>`

A few examples:

Using any relay available:

- `/p2p-circuit/p2p/QmTwo`
  - Dial QmTwo, through any available relay node (or find one node that can relay).
  - The relay node will use peer routing to find an address for QmTwo if it doesn't have a direct connection.
- `/p2p-circuit/ip4/../tcp/../p2p/QmTwo`
  - Dial QmTwo, through any available relay node, but force the relay node to use the encapsulated `/ip4` multiaddr for connecting to QmTwo.

Specify a relay:

- `/p2p/QmRelay/p2p-circuit/p2p/QmTwo`
  - Dial QmTwo, through QmRelay.
  - Use peer routing to find an address for QmRelay.
  - The relay node will also use peer routing, to find an address for QmTwo.
- `/ip4/../tcp/../p2p/QmRelay/p2p-circuit/p2p/QmTwo`
  - Dial QmTwo, through QmRelay.
  - Includes info for connecting to QmRelay.
  - The relay node will use peer routing to find an address for QmTwo, if not already connected.

Double relay:

- `/p2p-circuit/p2p/QmTwo/p2p-circuit/p2p/QmThree`
  - Dial QmThree, through a relayed connection to QmTwo.
  - The relay nodes will use peer routing to find an address for QmTwo and QmThree.
  - go-libp2p (reference implementation) **does not support nested relayed connections for now**, see [Future Work](#future-work) section.

## Wire format

We start the description of the Wire format by illustrating a possible flow scenario and then describing them in detail by phases.

### Relay Message

Every message in the relay protocol uses the following protobuf:

```
message CircuitRelay {

  enum Status {
    SUCCESS                    = 100;
    HOP_SRC_ADDR_TOO_LONG      = 220;
    HOP_DST_ADDR_TOO_LONG      = 221;
    HOP_SRC_MULTIADDR_INVALID  = 250;
    HOP_DST_MULTIADDR_INVALID  = 251;
    HOP_NO_CONN_TO_DST         = 260;
    HOP_CANT_DIAL_DST          = 261;
    HOP_CANT_OPEN_DST_STREAM   = 262;
    HOP_CANT_SPEAK_RELAY       = 270;
    HOP_CANT_RELAY_TO_SELF     = 280;
    HOP_BACKOFF                = 290;
    STOP_SRC_ADDR_TOO_LONG     = 320;
    STOP_DST_ADDR_TOO_LONG     = 321;
    STOP_SRC_MULTIADDR_INVALID = 350;
    STOP_DST_MULTIADDR_INVALID = 351;
    STOP_RELAY_REFUSED         = 390;
    MALFORMED_MESSAGE          = 400;
  }

  enum Type { // RPC identifier, either HOP, STOP or STATUS
    HOP = 1;
    STOP = 2;
    STATUS = 3;
    CAN_HOP = 4; // is peer a relay?
  }

  message Peer {
    required bytes id = 1;    // peer id
    repeated bytes addrs = 2; // peer's known addresses
  }

  optional Type type = 1;     // Type of the message

  optional Peer srcPeer = 2;  // srcPeer and dstPeer are used when Type is HOP or STOP
  optional Peer dstPeer = 3;

  optional Status code = 4;   // Status code, used when Type is STATUS
}
```

### High level overview of establishing a relayed connection

**Setup:**
- Peers involved, A, B, R
- A wants to connect to B, but needs to relay through R

**Assumptions:**
- A has connection to R, R has connection to B

**Events:**
- phase I: Open a request for a relayed stream (A to R).
  - A dials a new stream `sAR` to R using protocol `/libp2p/circuit/relay/0.1.0`.
  - A sends a CircuitRelay message with `{ type: 'HOP', srcPeer: '/p2p/QmA', dstPeer: '/p2p/QmB' }` to R through `sAR`.
  - R receives stream `sAR` and reads the message from it.
- phase II: Open a stream to be relayed (R to B).
  - R opens a new stream `sRB` to B using protocol `/libp2p/circuit/relay/0.1.0`.
  - R sends a CircuitRelay message with `{ type: 'STOP', srcPeer: '/p2p/QmA', dstPeer: '/p2p/QmB' }` on `sRB`.
  - R sends a CircuitRelay message with `{ type: 'STATUS', code: 'SUCCESS' }` on `sAR`.
- phase III: Streams are piped together, establishing a circuit
  - B receives stream `sRB` and reads the message from it
  - B sends a CircuitRelay message with `{ type: 'STATUS', code: 'SUCCESS' }` on `sRB`.
  - B passes stream to `NewConnHandler` to be handled like any other new incoming connection.

### Under the microscope

- We've defined a max length for the multiaddrs of arbitrarily 1024 bytes
- Multiaddrs are transfered on its binary packed format
- Peer Ids are transfered on its non base encoded format (aka byte array containing the multihash of the Public Key).


### Status codes table

This is a table of status codes and sample messages that may occur during a relay setup. Codes in the 200 range are returned by the relay node. Codes in the 300 range are returned by the destination node.


| Code  | Message                                           | Meaning    |
| ----- |:--------------------------------------------------|:----------:|
| 100   | "success"                                         | Relay was setup correctly |
| 220   | "src address too long"                            | |
| 221   | "dst address too long"                            | |
| 250   | "failed to parse src addr: no such protocol ipfs" | The `<src>` multiaddr in the header was invalid |
| 251   | "failed to parse dst addr: no such protocol ipfs" | The `<dst>` multiaddr in the header was invalid |
| 260   | "passive relay has no connection to dst"          | |
| 261   | "active relay couldn't dial to dst: conn refused" | relay could not form new connection to target peer |
| 262   | "couldn't' dial to dst"                           | relay has conn to dst, but failed to open a stream |
| 270   | "dst does not support relay"                      | |
| 280   | "can't relay to itself"                           | The relay got its own address as destination |
| 290   | "temporary backoff"                               | The relay wants us to backoff and try again later |
| 320   | "src address too long"                            | |
| 321   | "dst address too long"                            | |
| 350   | "failed to parse src addr"                        | src multiaddr in the header was invalid |
| 351   | "failed to parse dst addr"                        | dst multiaddr in the header was invalid |
| 390   | "connection refused by stop endpoint"             | The stop endpoint couldn't accept the connection |
| 400   | "malformed message"                               | A malformed or too long message was received |

## Implementation details

### Interfaces

> These are go-ipfs specific

As explained above, the relay is both a transport (`tpt.Transport`) and a mounted stream protocol (`p2pnet.StreamHandler`). In addition it provides a means of specifying relay nodes to listen/dial through.

Note: the usage of `p2pnet.StreamHandler` is a little bit off herein, but it gets the point across.

```go
import (
  tpt "github.com/libp2p/go-libp2p-transport"
  p2phost "github.com/libp2p/go-libp2p-host"
  p2pnet "github.com/libp2p/go-libp2p-net"
  p2proto "github.com/libp2p/go-libp2p-protocol"
)

const ID p2proto.ID = "/libp2p/circuit/relay/0.1.0"

type CircuitRelay interface {
  tpt.Transport
  p2pnet.StreamHandler

  EnableRelaying(enabled bool)
}

fund NewCircuitRelay(h p2phost.Host)
```

### Removing existing relay protocol in Go

Note that there is an existing swarm protocol colloquially called relay. It lives in the go-libp2p package and is named `/ipfs/relay/line/0.1.0`.

- Introduced in ipfs/go-ipfs#478 (28-Dec-2014).
- No changes except for ipfs/go-ipfs@de50b2156299829c000b8d2df493b4c46e3f24e9.
  - Changed to use multistream muxer.
- Shortcomings
  - No end-to-end encryption.
  - No rate limiting (DoS by resource exhaustion).
  - Doesn't verify src id in ReadHeader(), easy to fix.
- Capable of *accepting* connections, and *relaying* connections.
- Not capable of *connecting* via relaying.

Since the existing protocol is incomplete, insecure, and certainly not used, we can safely remove it.

## Future work

We have considered more features but won't be adding them on the first iteration of Circuit Relay, the features are:

- Multihop relay - With this specification, we are only enabling single hop relays to exist. Multihop relay will come at a later stage as Packet Switching.
- Relay discovery mechanism - At the moment we're not including a mechanism for discovering relay nodes. For the time being, they should be configured statically.
