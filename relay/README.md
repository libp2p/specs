# Circuit Relay

> Circuit Switching for libp2p, also known as TURN or Relay in Networking literature.

## Implementations

- [js-libp2p-circuit](https://github.com/libp2p/js-libp2p-circuit)
- [go-libp2p-circuit](https://github.com/libp2p/go-libp2p-circuit)

## Table of Contents

- [Overview](#overview)
- [Dramatization](#dramatization)
- [Addressing](#addressing)
- [Wire protocol](#wire-protocol)
- [Interfaces](#interfaces)
- [Implementation Details](#implementation-details)

## Overview

The circuit relay is a means of establishing connectivity between libp2p nodes (such as IPFS) that wouldn't otherwise be able to establish a direct connection to each other.

This helps in situations where nodes are behind NAT or reverse proxies, or simply don't support the same transports (e.g. go-ipfs vs. browser-ipfs). libp2p already has modules for NAT ([go-libp2p-nat](https://github.com/libp2p/go-libp2p-nat)), however piercing through NATs is not always an option due to their implementation differences. The circuit relay protocol exists to overcome those scenarios.

Unlike a transparent **tunnel**, where a libp2p peer would just proxy a communication stream to a destination (the destination being unaware of the original source), a circuit-relay makes the destination aware of the original source and the circuit followed to establish communication between the two. This provides the destination side with full knowledge of the circuit which, if needed, could be rebuilt in the opposite direction.

Apart from that, this relayed connection behaves just like a regular connection would, but over an existing swarm stream with another peer (instead of e.g. TCP.): One node asks a relay node to connect to another node on its behalf. The relay node shortcircuits its streams to the two nodes, and they are then connected through the relay.

Relayed connections are end-to-end encrypted just like regular connections.

The circuit relay is both a tunneled transport and a mounted swarm protocol.
The transport is the means of ***establishing*** and ***accepting*** connections, and the swarm protocol is the means to ***relaying*** connections.

```
+-----+    /ip4/.../tcp/.../ws/p2p/QmRelay    +-------+    /ip4/.../tcp/.../p2p/QmTwo       +-----+
|QmOne| <------------------------------------>|QmRelay|<----------------------------------->|QmTwo|
+-----+   (/libp2p/relay/circuit multistream) +-------+ (/libp2p/relay/circuit multistream) +-----+
     ^                                         +-----+                                         ^
     |           /p2p-circuit/QmTwo            |     |                                         |
     +-----------------------------------------+     +-----------------------------------------+
```

## Notes for the reader

1. We're using the `/p2p` multiaddr protocol instead of `/ipfs` in this document. `/ipfs` is currently the canonical way of addressing a libp2p or IPFS node, but given the growing non-IPFS usage of libp2p, we'll migrate to using `/p2p`.

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

`/p2p-circuit` multiaddrs don't carry any meaning of their own. They need to encapsulate a `/p2p` address, or be encapsulated in a `/p2p` address, or both.

As with all other multiaddrs, encapsulation of different protocols determines which metaphorical tubes to connect to each other.

A `/p2p-circuit` circuit address, is formated following:

`[<relay peer multiaddr>]/p2p-circuit/<destination peer multiaddr>`

Examples:

- `/p2p-circuit/p2p/QmVT6GYwjeeAF5TR485Yc58S3xRF5EFsZ5YAF4VcP3URHt` - Arbitrary relay node
- `/ip4/127.0.0.1/tcp/5002/ipfs/QmdPU7PfRyKehdrP5A3WqmjyD6bhVpU1mLGKppa2FjGDjZ/p2p-circuit/p2p/QmVT6GYwjeeAF5TR485Yc58S3xRF5EFsZ5YAF4VcP3URHt` - Specific relay node

This opens the room for multiple hop relay, where the second relay is encapsulated in the first relay multiaddr, such as:

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
  - The relay node will use peer routing to find an address for QmTwo.

Double relay:

- `/p2p-circuit/p2p/QmTwo/p2p-circuit/p2p/QmThree`
  - Dial QmThree, through a relayed connection to QmTwo.
  - The relay nodes will use peer routing to find an address for QmTwo and QmThree.
  - We'll probably not support nested relayed connections for now, there are edge cases to think of.

## Wire format

We start the description of the Wire format by illustrating a possible flow scenario and then describing them in detail by phases.

### High level overview of establishing a relayed connection

Setup:
- Peers involved, A, B, R
- A wants to connect to B, but needs to relay through R

Assumptions:
- A has connection to R, R has connection to B

Events:
- phase I: Open a request for a relayed stream (A to R)
  - A dials a new stream `sAR` to R using protocol `/libp2p/relay/hop` 
  - A writes Bs multiaddr `/p2p/QmB` on `sAR`
  - R receives stream `sAR` and reads `/p2p/QmB` from it.
- phase II: Open a stream to be relayed (R to B)
  - R opens a new stream `sRB` to B using protocol `/libp2p/relay/stop`
  - R writes `/p2p/QmA` on `sRB`
  - R writes OK to `sAR`
- phase III: Streams are piped together, establishing a circuit
  - B receives stream `sRB` and reads `/p2p/QmA` from it.
  - B writes OK to `sRB`
  - B passes stream to `NewConnHandler` to be handled like any other new incoming connection

### Under the microscope

Notes for the reader:
- `maddrA` is peer A's multiaddr
- `maddrR` is peer R's multiaddr
- `maddrB` is peer B's multiaddr
- `maxAddrLen` is arbitrarily 1024
- `readLpMaddr` is a function that does the following:

Read a Uvarint `V` from the stream. If the value is higher than `maxAddrLen`, writes an error code back, closes the stream and halts the relay attempt. If not, then reads `V` bytes from the stream and checks if its a valid multiaddr. Check for multiaddr validity and error back if not a valid formated multiaddr.

#### Phase I

Peer A opens a new stream to R on the '/libp2p/relay/hop' protocol and writes:

```
<uvarint len(maddrA)><madddrA><uvarint len(maddrB)><madddrB>
```

It then waits for a response in the form of:
```
<uvarint error code><uvarint msglength><message>
```

Once it receives that, it checks if the status code is `OK`. If it is, it passes the new connection to its `NewConnHandler`. Otherwise, it returns the error message to the caller.

Peer R receives a new stream on the '/libp2p/relay/hop' protocol.

It then calls `readLpMaddr` twice. The first value is `<src>` and the second is `<dst>`.

Peer R checks to make sure that `<src>` matches the remote peer of the stream its reading from. If it does not match, it writes an Error message, closes the stream and halts the relay attempt.

Peer R checks if `<dst>` refers to itself, if it does, it (writes an error back?) closes the stream and halts the relay attempt.

Peer R then checks if it has an open connection to the peer specified by `<dst>`.
If it does not, and the relay is not an "active" relay it (writes an error back) closes the stream, and halts the relay attempt.

If R does not have a connection to `<dst>`, and it *is* an "active" relay, it attempts to connect to `<dst>`.

If this connection succeeds it continues, otherwise it (writes back an error) closes the stream, and halts the relay attempt.


#### Phase II

R now opens a new stream to B with the '/libp2p/relay/stop' relay protocol multicodec and writes:

```
<uvarint len(maddrA)><madddrA><uvarint len(maddrB)><madddrB>
```

After this, R pipes the stream from A and the stream it opened to B together. R also writes OK back to A. R's job is complete.

#### Phase III

Peer B receives a new stream on the '/libp2p/relay/stop' protocol. It then calls `readLpMaddr` twice on this stream.

The first value is `<src>` and the second value is `<dst>`. Any error from those calls should be written back accordingly.

B now verifies that `<dst>` matches its peer ID. It then also checks that `<src>` is valid. It uses src as the
'remote addr' of the new 'incoming relay connection' it will create.

Peer B now writes back a message of the form:
```
<uvarint 'OK'><uvarint len(msg)><string "OK">
```

And passes the relayed connection into its `NewConnHandler`.

### Status codes table

This is a table of status codes and sample messages that may occur during a relay setup. Codes in the 200 range are returned by the relay node. Codes in the 300 range are returned by the destination node.


| Code  | Message                                           | Meaning    |
| ----- |:--------------------------------------------------|:----------:|
| 100   | OK                                                | Relay was setup correctly    |
| 220   | "src address too long"                            | |
| 221   | "dst address too long"                            | |
| 250   | "failed to parse src addr: no such protocol ipfs" | The `<src>` multiaddr in the header was invalid |
| 251   | "failed to parse dst addr: no such protocol ipfs" | The `<dst>` multiaddr in the header was invalid |
| 260   | "passive relay has no connection to dst"          | |
| 261   | "active relay could not connect to dst: connection refused" | relay could not form new connection to target peer |
| 262   | "could not open new stream to dst: BAD ERROR"     | relay has connection to dst, but failed to open a new stream |
| 270   | "<dst> does not support relay"                    | |
| 280   | "can't relay to itself"                           | The relay got its own address as destination |
| 320   | "src address too long"                            | |
| 321   | "dst address too long"                            | |
| 350   | "failed to parse src addr: no such protocol ifps" | The `<src>` multiaddr in the header was invalid |
| 351   | "failed to parse dst addr: no such protocol ifps" | The `<dst>` multiaddr in the header was invalid |

## Interfaces

As explained above, the relay is both a transport (`tpt.Transport`) and a mounted stream protocol (`p2pnet.StreamHandler`). In addition it provides a means of specifying relay nodes to listen/dial through.

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

## Implementation details

### Removing existing relay protocol in Go

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

Since the existing protocol is incomplete, insecure, and certainly not used, we can safely remove it.

## Future work

- Multihop relay - With this specification, we are only enabling single hop relays to exist. Multihop relay will come at a later stage as Packet Switching.
- Relay discovery mechanism - At the moment we're not including a mechanism for discovering relay nodes. For the time being, they should be configured statically.
