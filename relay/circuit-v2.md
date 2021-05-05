# Circuit Relay v2

This is the version 2 of the libp2p Circuit Relay protocol.

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 1A              | DRAFT          | Active | r1, 2021-05-05  |

Authors: [@vyzo]

Interest Group: [@mxinden], [@stebalien], [@raulk]

[@vyzo]: https://github.com/vyzo
[@mxinden]: https://github.com/mxinden
[@stebalien]: https://github.com/stebalien
[@raulk]: https://github.com/raulk

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Table of Contents

- [Introduction](#introduction)
  - [Rationale](#rationale)
- [The Protocol](#the-protocol)
  - [Interaction](#interaction)
  - [Hop Protocol](#hop-protocol)
  - [Stop Protocol](#stop-protocol)
  - [Reservation Vouchers](#reservation-vouchers)
- [Protobuf](#protobuf)

## Introduction

This is the specification of v2 of the p2p-circuit relay protocol.

Compared to the first version of the protocol, there are some significant departures:
- The protocol has been split into two subprotocols, `hop` and `stop`
  - The `hop` protocol governs the behaviour of relays; it is used for
    reserving resources in the relay and opening a switched connection
    to a peer through the relay.
  - The `stop` protocol governs the termination of circuit switched
    connections.
- The concept of resource reservation has been introduced, whereby
  peers wishing to use a relay explicitly reserve resources and obtain
  _reservation vouchers_ which can be distributed to their peers for
  routing purposes.
- The concept of limited relaying has been introduced, whereby relays
  provide switched connectivity with a limited duration and data cap.

### Rationale

The evolution of the protocol towards v2 has been influenced by our
experience in operating open relays in the wild.  The original
protocol, while very flexible, has some limitations when it comes to
the practicalities of relaying connections.

The main problem is that is no mechanism to reserve resources in the
relay, which leads to continuoues oversubscription of relays and the
necessity of (often inefective) heuristics for balancing resources.
In practice, running a relay proved to be an expensive proposition
requiring dedicated hosts with significant hardware and bandwidth
costs.  In addition, there is ongoing work in Hole Punching
coordination for direction connection upgrade through relays, which
doesn't require an unlimited relay connection.

In order to address the situation and seamlessly support pervasive
hole punching, we have introduced limited relays and slot
reservations.  This allows relays to effectively manage their
resources and provide service at a small scale, thus enabling the
deployment of an army of relays for extreme horizontal scaling without
excessive bandwidth costs and dedicated hosts.

Furthermore, the original decision to conflate circuit initiation and
termination in the same protocol has made it very hard to on provide
relay service on demand, decoupled with whether _client_ functionality
is supported by the host.

In order to address this problem, we have splt the protocol into the
`hop` and `stop` subprotocols. This allows us to always enable the
client-side functionality in a host, while providing the option to
later mount the relay service in public hosts, _after_ the
reachability of the host has been determined through AutoNAT.

## The Protocol

### Interaction

The following diagram illustrates the interaction between three peers,
_A_, _B_, and _R_, in the course of establishing a relayed connection.
Peer _A_ is a private peer, which is not publicly reachable; it
utilizes the services of peer _R_ as the relay.  Peer _B_ is another
peer who wishes to connect to peer _A_ through _R_.

![Circuit v2 Protocol Interaction](circuit-v2.png)

The first part of the interaction is _A_'s reservation of a relay slot
in _R_.  This is accomplished by opening a connection to _R_ and
sending a `RESERVE` message in the `hop` protocol; if the reservation
is successful, the relay responds with a `STATUS:OK` message and
provides _A_ with a reservation voucher.

The second part of the interaction is the establishment of a circuit
switch connection from _B_ to _A_ through _R_.  It is assumed that _B_
has obtained a circuit multiaddr for _A_ of the form
`/p2p/QmR/p2p-circuit/p2p/QmA` out of band using some peer discovery
service (eg. the DHT or a rendezvous point).

In order to connect to _A_, _B_ then conncts to _R_, opens a `hop`
protocol stream and sends a `CONNECT` message to the relay.  The relay
verifies that it has a reservation and connection for _A_ and opens a
`stop` protocol stream to _A_, sending a `CONNECT` message.

Peer _A_ then responds to the relaywith a `STATUS:OK` message, which
responds to _B_ with a `STATUS:OK` message in the open `hop` stream
and then proceeds to bridge the two streams into a relayed connection.
The relayed connection flows in the `hop` stream between the
connection initiator and the relay and in the `stop` stream between
the relay and the connection termination point.

### Hop Protocol

TBD

### Stop Protocol

TBD

### Reservation Vouchers

TBD

## Protobuf

```
message HopMessage {
  enum Type {
    RESERVE = 0;
    CONNECT = 1;
    STATUS = 2;
  }

  required Type type = 1;

  optional Peer peer = 2;
  optional Reservation reservation = 3;
  optional Limit limit = 4;

  optional Status status = 5;
}

message StopMessage {
  enum Type {
    CONNECT = 0;
    STATUS = 1;
  }

  required Type type = 1;

  optional Peer peer = 2;
  optional Limit limit = 3;

  optional Status status = 4;
}

message Peer {
  required bytes id = 1;
  repeated bytes addrs = 2;
}

message Reservation {
  optional int64 expire = 1;  // Unix expiration time (UTC)
  repeated bytes addrs = 2;   // relay addrs for reserving peer
  optional bytes voucher = 3; // reservation voucher
}

message Limit {
  optional int32 duration = 1; // seconds
  optional int64 data = 2;     // bytes
}

enum Status {
  OK                      = 100;
  RESERVATION_REFUSED     = 200;
  RESOURCE_LIMIT_EXCEEDED = 201;
  PERMISSION_DENIED       = 202;
  CONNECTION_FAILED       = 203;
  NO_RESERVATION          = 204;
  MALFORMED_MESSAGE       = 400;
  UNEXPECTED_MESSAGE      = 401;
}
```
