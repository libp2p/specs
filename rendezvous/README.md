# Rendezvous Protocol

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r1, 2019-01-18  |

Authors: [@vyzo]

Interest Group: [@daviddias], [@whyrusleeping], [@Stebalien], [@jacobheun], [@yusefnapora], [@vasco-santos]

[@vyzo]: https://github.com/vyzo
[@daviddias]: https://github.com/daviddias
[@whyrusleeping]: https://github.com/whyrusleeping
[@Stebalien]: https://github.com/Stebalien
[@jacobheun]: https://github.com/jacobheun
[@yusefnapora]: https://github.com/yusefnapora
[@vasco-santos]: https://github.com/vasco-santos

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Table of Contents

- [Overview](#overview)
- [Use Cases](#use-cases)
   - [Replacing ws-star-rendezvous](#replacing-ws-star-rendezvous)
   - [Rendezvous and pubsub](#rendezvous-and-pubsub)
- [The Protocol](#the-protocol)
   - [Registration Lifetime](#registration-lifetime)
   - [Interaction](#interaction)
   - [Proof of Work](#proof-of-work)
   - [Protobuf](#protobuf)
- [Recommendations for Rendezvous Points configurations](#recommendations-for-rendezvous-points-configurations)

## Overview

The protocol described in this specification is intended to provide a
lightweight mechanism for generalized peer discovery. It can be used
for bootstrap purposes, real time peer discovery, application specific
routing, and so on.  Any node implementing the rendezvous protocol can
act as a rendezvous point, allowing the discovery of relevant peers in
a decentralized fashion.

## Use Cases

Depending on the application, the protocol could be used in the
following context:
- During bootstrap, a node can use known rendezvous points to discover
  peers that provide critical services. For instance, rendezvous can
  be used to discover circuit relays for connectivity restricted
  nodes.
- During initialization, a node can use rendezvous to discover
  peers to connect with the rest of the application. For instance,
  rendezvous can be used to discover pubsub peers within a topic.
- In a real time setting, applications can poll rendezvous points in
  order to discover new peers in a timely fashion.
- In an application specific routing setting, rendezvous points can be
  used to progressively discover peers that can answer specific queries
  or host shards of content.

### Replacing ws-star-rendezvous

We intend to replace ws-star-rendezvous with a few rendezvous daemons
and a fleet of p2p-circuit relays.  Real-time applications will
utilize rendezvous both for bootstrap and in a real-time setting.
During bootstrap, rendezvous will be used to discover circuit relays
that provide connectivity for browser nodes.  Subsequently, rendezvous
will be utilized throughout the lifetime of the application for real
time peer discovery by registering and polling rendezvous points.
This allows us to replace a fragile centralized component with a
horizontally scalable ensemble of daemons.

### Rendezvous and pubsub

Rendezvous can be naturally combined with pubsub for effective
real-time discovery.  At a basic level, rendezvous can be used to
bootstrap pubsub: nodes can utilize rendezvous in order to discover
their peers within a topic.  Alternatively, pubsub can also be used as
a mechanism for building rendezvous services. In this scenerio, a
number of rendezvous points can federate using pubsub for internal
real-time distribution, while still providing a simple interface to
clients.

## The Protocol

The rendezvous protocol provides facilities for real-time peer
discovery within application specific namespaces. Peers connect to the
rendezvous point and register their presence in one or more
namespaces. It is not allowed to register arbitrary peers in a
namespace; only the peer initiating the registration can register
itself. The register message contains a serialized [signed peer record](https://github.com/libp2p/specs/blob/377f05a/RFC/0002-signed-envelopes.md)
created by the peer, which can be validated by others.

Peers registered with the rendezvous point can be discovered by other
nodes by querying the rendezvous point. The query specifies the
namespace for limiting application scope and optionally a maximum
number of peers to return. The namespace can be omitted in the query,
which asks for all peers registered to the rendezvous point.

The query can also include a cookie, obtained from the response to a
previous query, such that only registrations that weren't included in
the previous response will be returned. This allows peers to
progressively refresh their network view without overhead, which
greatly simplifies real time discovery. It also allows for pagination
of query responses, so that large numbers of peer registrations can be
managed.

The rendezvous protocol runs over libp2p streams using the protocol id `/rendezvous/1.0.0`.

### Registration Lifetime

Registration lifetime is controlled by an optional TTL parameter in
the `REGISTER` message.  If a TTL is specified, then the registration
persists until the TTL expires.  If no TTL was specified, then a default
of 2hrs is implied. There may be a rendezvous point-specific upper bound
on TTL, with a minimum such value of 72hrs. If the TTL of a registration
is inadmissible, the rendezvous point may reject the registration with
an `E_INVALID_TTL` status.

Peers can refresh their registrations at any time with a new
`REGISTER` message; the TTL of the new message supersedes previous
registrations. Peers can also cancel existing registrations at any
time with an explicit `UNREGISTER` message.

The registration response includes the actual TTL of the registration,
so that peers know when to refresh.

### Interaction

Clients `A` and `B` connect to the rendezvous point `R` and register for namespace
`my-app` with a `REGISTER` message:

```
A -> R: REGISTER{my-app, {QmA, AddrA}}
R -> A: {OK}
B -> R: REGISTER{my-app, {QmB, AddrB}}
R -> B: {OK}
```

Client `C` connects and registers for namespace `another-app`:
```
C -> R: REGISTER{another-app, {QmC, AddrC}}
R -> C: {OK}
```

Another client `D` can discover peers in `my-app` by sending a `DISCOVER` message; the
rendezvous point responds with the list of current peer reigstrations and a cookie.
```
D -> R: DISCOVER{ns: my-app}
R -> D: {[REGISTER{my-app, {QmA, Addr}}
          REGISTER{my-app, {QmB, Addr}}],
         c1}
```

If `D` wants to discover all peers registered with `R`, then it can omit the namespace
in the query:
```
D -> R: DISCOVER{}
R -> D: {[REGISTER{my-app, {QmA, Addr}}
          REGISTER{my-app, {QmB, Addr}}
          REGISTER{another-app, {QmC, AddrC}}],
         c2}
```

If `D` wants to progressively poll for real time discovery, it can use
the cookie obtained from a previous response in order to only ask for
new registrations.

So here we consider a new client `E` registering after the first query,
and a subsequent query that discovers just that peer by including the cookie:
```
E -> R: REGISTER{my-app, {QmE, AddrE}}
R -> E: {OK}
D -> R: DISCOVER{ns: my-app, cookie: c1}
R -> D: {[REGISTER{my-app, {QmE, AddrE}}],
         c3}
```

### Proof of Work

The protocol as described so far is susceptible to spam attacks from
adversarial actors who generate a large number of peer identities and
register under a namespace of interest (eg: the relay namespace). This
can be mitigated by requiring a Proof of Work scheme for client
registrations.

If a rendezvous node decides that Proof of Work is required to complete
a registration, it will send a response with the status code `E_POW_REQUIRED`
together with a `challenge`.

A client is then expected to follow up with a `ProofOfWork` message, computing
a hash by concatenating the following:

- The UTF8 bytes of the string `libp2p-rendezvous-pow`
- The contents of `challenge`
- The `ns` field
- The `signedPeerRecord` field
- The `PeerId` of the rendezvous point we are registering with
- The `nonce` field

The resulting byte buffer is hashed using SHA256.

We define "difficulty" as the number of zero bytes at the front of the
hash assuming a big endian encoding. If a rendezvous point considers
the difficulty too low, it will decline a `ProofOfWork` message with
a `RegisterResponse` and the status code set to `E_POW_DIFFICULTY_TOO_LOW` together
with a new `challenge`.

Once the difficulty requirement is met, a rendezvous point will respond with a
status code of `OK`.

To vary the difficulty, a client can manipulate the `nonce` field.
It is purposely unspecified, what the required difficulty for a
rendezvous point is. This allows rendezvous points to vary the difficulty
based on current load.

Example:

```
A -> R: REGISTER{my-app, {QmA, AddrA}}
R -> A: {E_POW_REQUIRED, challenge: 0xDEADBEEFDEADBEEF}
A -> R: PROOF_OF_WORK{0x00FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF, nonce: 3123452}
R -> A: {E_DIFFICULTY_TOO_LOW, challenge: 0xBEEFDEADBEEFDEAD}
A -> R: PROOF_OF_WORK{0x000000FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF, nonce: 8572945}
R -> A: {OK}
```

### Protobuf

```protobuf
message Message {
  enum MessageType {
    REGISTER = 0;
    REGISTER_RESPONSE = 1;
    UNREGISTER = 2;
    DISCOVER = 3;
    DISCOVER_RESPONSE = 4;
  }

  enum ResponseStatus {
    OK                            = 0;
    E_INVALID_NAMESPACE           = 100;
    E_INVALID_SIGNED_PEER_RECORD  = 101;
    E_INVALID_TTL                 = 102;
    E_INVALID_COOKIE              = 103;
    E_POW_REQUIRED                = 104;
    E_DIFFICULTY_TOO_LOW          = 105;
    E_NOT_AUTHORIZED              = 200;
    E_INTERNAL_ERROR              = 300;
    E_UNAVAILABLE                 = 400;
  }

  message Register {
    optional string ns = 1;
    optional bytes signedPeerRecord = 2;
    optional int64 ttl = 3; // in seconds
  }

  message RegisterResponse {
    optional ResponseStatus status = 1;
    optional string statusText = 2;
    optional int64 ttl = 3; // in seconds
    optional bytes challenge = 4;
  }

  message Unregister {
    optional string ns = 1;
    optional bytes id = 2;
  }

  message Discover {
    optional string ns = 1;
    optional int64 limit = 2;
    optional bytes cookie = 3;
  }

  message DiscoverResponse {
    repeated Register registrations = 1;
    optional bytes cookie = 2;
    optional ResponseStatus status = 3;
    optional string statusText = 4;
  }
  
  message ProofOfWork {
    repeated bytes hash = 1;
    optional int64 nonce = 2;
  }

  optional MessageType type = 1;
  optional Register register = 2;
  optional RegisterResponse registerResponse = 3;
  optional Unregister unregister = 4;
  optional Discover discover = 5;
  optional DiscoverResponse discoverResponse = 6;
}
```

## Recommendations for Rendezvous Points configurations

Rendezvous points should have well defined configurations to enable libp2p
nodes running the rendezvous protocol to have friendly defaults, as well as to
guarantee the security and efficiency of a Rendezvous point. This will be
particularly important in a federation, where rendezvous points should share
the same expectations.

Regarding the validation of registrations, rendezvous points should have:
- a minimum acceptable **ttl** of `2H`
- a maximum acceptable **ttl** of `72H`
- a maximum **namespace** length of `255`

Rendezvous points are also recommend to allow:
- a maximum of `1000` registration for each peer
  - defend against trivial DoS attacks
- a maximum of `1000` peers should be returned per namespace query

Whilst the exact details in regard to PoW difficulty are unspecified, rendezvous
points are expected to scale the difficulty with the number of registrations for
an individual peer. For example by setting required difficulty to the active number
of registrations of a given peer.
