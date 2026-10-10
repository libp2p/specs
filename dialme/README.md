# Simple protocol to request dial backs

> Allow a peer in a network to be dialed back after an initial connection has been negotiated

In certain scenarios, it might be desirable for a peer to ask another peer to dial it back after an initial connection has been established. This might be useful in scenarios where the dialing peer has learned enough about the network topology and it knows of a better route to be reached over (NATed peers vs non NATed peers). This protocol will allow it to ask its counterpart to dial it back on a hopefully better route.

#### Requirements

The `dialme` protocol is a libp2p protocol.

In order for dial back to happen a prior connection is required. This prior connection could be established over a circuit (the most likely scenario) or any other preexisting connection. The prior connection is only required to request the dial back, and the `dialme` protocol assumes nothing about it at all.

## Typical `dialme` (back) flow

A `dialme` flow might look similar to the one described below:

- Lets assume that `Peer A` wants to dial `Peer B`
  - `Peer A` is publicly reachable on the wider internet
  - `Peer B` is behind an impenetrable NAT
- `Peer A` dials `Peer B` using some relay(s)
- Once a connection has been established over the relay(s), `Peer A` asks `Peer B` to dial it back over the provided address using the `dialme` protocol
- `Peer B` proceeds to dial `Peer A` over the provided addresses, dropping the circuited connection once the new connection succeeds
- `Peer A` accepts the dial back and proceeds to use the new connection dropping the relayed one

### The protocol

This is a rather simple protocol that communicates a multiaddress to perform the dial back:

```protobuf
message DialMe {
  message Peer {
    required bytes id = 1;    // peer id
    repeated string addrs = 2; // a multiaddr to dial the the peer over
  }

  optional Peer peer = 1;
```
