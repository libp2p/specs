<!-- mxinden TODO: Update
https://github.com/libp2p/specs/tree/master/connections#protocol-negotiation in
Protocol Select pull request. -->

<!-- mxinden TODO: Hole Punching is not only concerned with punching holes into
NATs, but Firewalls and NATs. Should this fact be stressed in this document? -->

<!-- mxinden TODO: Consistently use either dialer/listener or client/server -->

# Protocol Select

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 1A              | Working Draft  | Active | r0, 2021-XX-XX  |

Authors: [@marten-seemann], [@mxinden]

Interest Group:

[@marten-seemann]: https://github.com/marten-seemann
[@mxinden]: https://github.com/mxinden

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Table of Contents

- [Protocol Select](#protocol-select)
    - [Table of Contents](#table-of-contents)
    - [Introduction](#introduction)
        - [Improvements over _[Multistream Select]_](#improvements-over-_multistream-select_)
    - [High-Level Overview](#high-level-overview)
        - [Basic Flow](#basic-flow)
        - [Secure Channel Selection](#secure-channel-selection)
        - [TCP Simultaneous Open](#tcp-simultaneous-open)
            - [Coordinated TCP Simultaneous Open](#coordinated-tcp-simultaneous-open)
            - [Uncoordinated TCP Simultaneous Open](#uncoordinated-tcp-simultaneous-open)
        - [Connection Protocol Negotiation](#connection-protocol-negotiation)
            - [Early data optimization](#early-data-optimization)
            - [0-RTT](#0-rtt)
        - [Stream Protocol Negotiation](#stream-protocol-negotiation)
            - [Initiator](#initiator)
            - [Listener](#listener)
    - [Transitioning from [Multistream Select]](#transitioning-from-multistream-select)
        - [Multiphase Rollout](#multiphase-rollout)
            - [Phase 1](#phase-1)
            - [Phase 2](#phase-2)
            - [Phase 3](#phase-3)
        - [Additional Rollout Mechanisms](#additional-rollout-mechanisms)
        - [Heuristics](#heuristics)
            - [TCP](#tcp)
            - [QUIC](#quic)
            - [Protocol Differentiation](#protocol-differentiation)
    - [Protocol Specification](#protocol-specification)
        - [Protocol Evolution](#protocol-evolution)
            - [Non-Breaking Changes](#non-breaking-changes)
            - [Breaking Changes](#breaking-changes)
    - [Extensions](#extensions)
        - [Protocol IDs](#protocol-ids)
    - [FAQ](#faq)

## Introduction

_Protocol Select_ is a protocol negotiation protocol. It is aimed at negotiating
libp2p protocols on connections and streams. It replaces the _[Multistream
Select]_ protocol.

### Improvements over _[Multistream Select]_

- **Downgrade attacks** and **censorship resistance**

  Given that **[Multistream Select]** negotiates a connection's security
  protocol unencrypted and unauthenticated it is prone to [downgrade attack]s.
  In addition, a man-in-the-middle can detect that a given connection is used
  to carry libp2p traffic, allowing attackers to censor such connections.

  **Protocol Select** is combined with a change to the Multiaddr format,
  advertising the secure channel protocol through the latter instead of
  negotiating them in-band. Thus [Downgrade attack]s are no longer possible at
  the protocol negotiation level and a man-in-the-middle can no longer detect
  a connection being used for libp2p traffic through the negotation process.

- **Connection establishment**

  In addition to making us vulnerable to downgrade attacks, negotiating the
  security protocol takes one round-trip in the common case with **[Multistream
  Select]**. On top of that negotiating a stream multiplexer (on TCP) takes
  another round-trip.

  **Protocol Select** on the other hand depends on security protocols being
  advertised, thereby eliminating the need for negotiating them. For optimized
  implementations, stream muxer negotiation will take zero round-trips for the
  client (depending on the details of the cryptographic handshake protocol). In
  that case, the client will be able to immediately open a stream after
  completing the cryptographic handshake. In addition the protocol supports
  zero-round-trip optimistic stream protocol negotiation when proposing a single
  protocol.

- **Data schema**

  The **[Multistream Select]** protocol is defined as a plaintext protocol
  with no strict schema definition, making both implementation and protocol
  evolution time consuming and error-prone. See [rust-libp2p/1795] showcasing
  complexity for implementors and [specs/196] to showcase difficulty evolving
  protocol.

  The **Protocol Select** protocol will use a binary data format defined in a
  machine parseable schema language allowing protocol evolution at the schema
  level.

- **Bandwidth**

  **Multistream Select** is not as bandwidth efficient as it could be. For
  example negotiating a protocol requires sending the protocol name back and
  forth. For human readability protocol names are usually long strings (e.g.
  `/ipfs/kad/1.0.0`).

  **Protocol Select** will include the option to improve bandwidth efficiency
  e.g. around protocol names in the future. While _Protocol Select_ will not
  solve this in the first iteration, the protocol is designed with this
  optimization in mind, and allows for a smooth upgrade in a future iteration.

## High-Level Overview

### Basic Flow

Both endpoints, client and server, send a list of supported protocols. Whether
an endpoint sends its list before or after it has received the remote's list
depends on the context and is detailed below. Nodes SHOULD order the list by
preference. Once an endpoint receives a list from a remote, the protocol to be
used on the connection or stream is determined by intersecting ones own and the
remote list, as follows:

1. All protocols that aren't supported by both endpoints are removed from the
   clients' list of protocols.

2. The protocol chosen is the first protocol of the client's list.

If there is no overlap between the two lists, the two endpoints can not
communicate and thus both endpoints MUST close the connection or stream.

### Secure Channel Selection

Conversely to [Multistream Select], secure channel protocols are not dynamically
negotiated in-band. Instead, they are announced upfront in the peer multiaddrs
(**TODO**: add link to multiaddr spec). This way, implementations can jump
straight into a cryptographic handshake, thus curtailing the possibility of
packet-inspection-based censorship and dynamic downgrade attacks.

Given that there is no in-band security protocol negotiation, nodes have to
listen on different ports for each offered security protocol. As an example a
node supporting both [Noise] and [TLS] over TCP will need to listen on two TCP
ports e.g. `/ip6/2001:DB8::/tcp/9090/noise` and `/ip6/2001:DB8::/tcp/443/tls`.

Advertising the secure channel protocol through the peer's Multiaddr instead of
negotiating the protocol in-band forces users to advertise an updated Multiaddr
when changing the secure channel protocol in use. This is especially cumbersome
when using hardcoded Multiaddresses. Users may leverage the [dnsaddr] Multiaddr
protocol as well as using a new UDP or TCP port for the new protocol to ease the
transition.

Note: A peer MAY advertise a Multiaddr that includes a secure channel handshake
protocol like `/noise` even if it doesn't support Protocol Select. See
[Heuristic section](#heuristic) below for details on how listeners can
differentiate the negotiation protocol spoken by the dialer on incoming
connections.

### TCP Simultaneous Open

TCP allows the establishment of a single connection if two endpoints start
initiating a connection at the same time. This is called _TCP Simultaneous
Open_. Since many application protocols running on top of a connection (most
notably the secure channel protocols e.g. TLS) assume their role (client /
server) based on who initiated the connection, TCP Simultaneous Open connections
need special handling. This special handling is described below, differentiating
between two cases of TCP Simultaneous Open: coordinated and uncoordinated.

#### Coordinated TCP Simultaneous Open

When doing Hole Punching over TCP, the [_Direct Connection Upgrade through
Relay_][DCUTR] protocol coordinates the two nodes to _simultaneously_ dial each
other, thus, when successful, resulting in a TCP Simultaneous Open connection.
The two nodes are assigned their role (client / server) out-of-band by the
[_Direct Connection Upgrade through Relay_][DCUTR] protocol.

#### Uncoordinated TCP Simultaneous Open

In the uncoordinated case, where two nodes coincidentally simultaneously dial
each other, resulting in a TCP Simultaneous Open connection, the secure channel
protocol handshake will fail, given that both nodes assume to be in the
initiating / client role. E.g. in the case of TLS the protocol will report the
receipt of a ClientHello while it expected a ServerHello. Once the security
handshake failed due to TCP Simultaneous Open, i.e. due to both sides assuming
to be the client, nodes SHOULD close the connection and back off for a random
amount of time before trying to reconnect.

### Connection Protocol Negotiation

This section only applies if Protocol Select is run over a transport that is not
natively multiplexed. For transports that provide stream multiplexing on the
transport layer (e.g. QUIC) this section should be ignored.

While the first protocol to be negotiated on a non-multiplexed connection is
currently always a multiplexer protocol, future libp2p versions might want to
negotiate non-multiplexer protocols as the first protocol on a connection.

#### Early data optimization

Some handshake protocols (TLS 1.3, Noise) support sending of *Early Data*. We
use the term *Early Data* to mean any application data that is sent before the
proper completion of the handshake.

In _Protocol Select_ endpoints make use of Early Data to speed up protocol
negotiation. As soon as an endpoints reaches a state during the handshake where
it can send encrypted application data, it sends a list of supported protocols,
no matter whether it is in the role of a client or server. Note that depending
on the handshake protocol used (and the optimisations implemented), either the
client or the server might arrive at this state first.

When using TLS 1.3, the server can send Early Data after it receives the
ClientHello. Early Data is encrypted, but at this point of the handshake the
client's identity is not yet verified.

While Noise in principle allows sending of unencrypted data, endpoints MUST NOT
use this to send their list of protocols. An endpoint MAY send it as soon it is
possible to send encrypted data, even if the peers' identity is not verified at
that point.

Handshake protocols (or implementations of handshake protocols) that don't
support sending of Early Data will have to run the protocol negotiation after
the handshake completes.

#### 0-RTT

When using 0-RTT session resumption as offered by TLS 1.3 and Noise, clients
SHOULD remember the protocol they used before and optimistically offer that
protocol only. A client can then optimistically send application data, not waiting
for the list of supported protocols by the server. If the server still supports
the protocol, it will choose the protocol offered by the client when intersecting the
two lists, and proceed with the connection. If not, the list intersection fails
and the connection is closed, which needs to be handled by the upper protocols.

### Stream Protocol Negotiation

Contrary to the above [Connection Protocol
Negotiation](#Connection-Protocol-Negotiation) and its early data optimization,
we assume that the initiator of a stream is always the endpoint able to send
data first.

Note: While libp2p currently does not support nested stream protocols, e.g. a
compression protocol wrapping bitswap, future versions of libp2p might change
that. The above assumption of the initiator being the endpoint to send data
first, does not apply to protocol negotiations following the first negotiation -
a nested negotiation - on a stream.

#### Initiator

The initiator of a new stream is the first endpoint to send a message. We
differentiate in the following two scenarios.

1. **Optimistic Protocol Negotiation**: The endpoint knows exactly which
   protocol it wants to use. It then only sends this protocol. It MAY start
   sending application data right after the _Protocol Select_ protobuf message.
   Since it has not received confirmation from the remote peer for the protocol,
   any such data might be lost in such case.

2. **Multi Protocol Negotiation**: The endpoint wants to use any of a set of
   protocols, and lets the remote peer decide which one. It then sends the list
   of protocols. It MUST wait for the peer's protocol choice before sending
   application data.

An initiator MUST treat the receipt of an empty list of protocols in response to
its list of protocols as a negotiation failure and thus a stream error.

#### Listener

The listening endpoint replies to a list of protocols from the initiator by
either:

- Sending back a single entry list with the protocol it would like to speak.

- Rejecting all proposed protocols by replying with an empty list of protocols.

## Transitioning from [Multistream Select]

Protocol Select is not compatible with [Multistream Select] both in its
semantics as well as on the wire. Live libp2p-based networks, currently using
[Multistream Select], will need to follow the multiphased roll-out strategy
detailed below to guarantee a smooth transition.

### Multiphase Rollout

#### Phase 1

In the first phase of the transition from [Multistream Select] to Protocol
Select, nodes in the network are upgraded to support both [Multistream Select]
and Protocol Select when accepting inbound connections, i.e. when acting as a
listener. Differentiating the two protocols as a listener is detailed in the
[Heuristics](#heuristics) section below. Nodes, when dialing, MUST NOT yet use
Protocol Select, but instead continue to use [Multistream Select].

Once a large enogh fraction of the network has upgraded, one can transition to
phase 2.

#### Phase 2

With a large enough fraction of the network supporting Protocol Select on
inbound connections, nodes MAY start using Protocol Select on outbound
connections.

After a large enough fraction of the network has upgraded, i.e. uses Protocol
Select for outbound connections, one can transition to phase 3.

#### Phase 3

Given that a large enough fraction of the network uses Protocol Select for both
out- and inbound connections, nodes can drop support for [Multistream Select]
concluding the transition.

### Additional Rollout Mechanisms

When attempting to upgrade an outbound connection with Protocol Select to a node
that does not yet support Protocol Select, the connection attempt will fail:

* TCP: when the cryptographic handshake is started

* QUIC: when the first stream is opened

Implementations MAY implement a fallback mechanism: If the step described above
fails, they close the current connection and dial a new connection, this time
using [Multistream Select].

Note that it takes one connection attempt to discover this failure and an
additional attempt to perform the fallback. Thus this upgrade mechanism should
only be used in addition to the above multiphase rollout to ease the transition.

<!-- TODO Find a better name than `Heuristics` -->
### Heuristics

When accepting a connection, an endpoint doesn't know whether the remote peer is
going to speak [Multistream Select] or Protocol Select to negotiate connection
or stream protocols. The below first describes **at which stage** of a TCP and
QUIC connection the two protocol negotiation protocols need to be
differentiated, followed by **how** one can differentiate the two.

#### TCP

Note: Since we decouple the multiaddr change (TODO: Be more specific. What is
the multiaddr change?) from support for Protocol Select, dialing a TCP based
address that contains the security handshake protocol *does not* imply that
we'll speak Protocol Select.

The first message received on a freshly established and secured TCP connection
will be a message trying to negotiate the stream muxer using either Protocol
Select or [Multistream Select].

#### QUIC

Since QUIC neither negotiates a security nor a stream muxer protocol, we'll have
wait a bit longer before we can distinguish between [Multistream Select] and
Protocol Select, namely until the client opens the first stream. Conversely,
this means that a server won't be able to open a stream until it has determined
which protocol is used.

#### Protocol Differentiation

Both Protocol Select and [Multistream Select] prefix their messages with the
varint encoded message length. The first message send by [Multistream Select] is
`/multistream/1.0.0`. Implementations should read the first few bytes and
proceed with either [Multistream Select] or Protocol Select depending on whether
it equals `/multistream/1.0.0` or not.

## Protocol Specification

Messages are encoded according to the Protobuf definition below using the
`proto2` syntax. The encoded messages are prefixed with their length in bytes,
encoded as an unsigned variable length integer as defined by the [multiformats
unsigned-varint spec][uvarint-spec].

Messages are encoded via the `ProtoSelect` message type. With the current
version of _Protocol Select_ detailed in this document, the `version` field of
the `ProtocolSelect` message is set to `1`. Implementations MUST reject messages
with a `version` other than the current version. See [Protocol
Evolution](#Protocol-Evolution) for details. Both the `Offer` and the `Use`
messages are wrapped with the `ProtocolSelect` message at all time.

```protobuf
message ProtoSelect {
    uint32 version = 1;

    message Protocol {
        oneof protocol {
            string name = 1;
        }
    }
    repeated Protocol protocols = 2;
}
```

<!-- TODO: Document what `name` is. E.g. UTF-8 and same as used in Multistream
Select. -->

### Protocol Evolution

While we can not foresee all future use-cases of _Protocol Select_, we can
design _Protocol Select_ in a way to be easy to evolve, and thus be able to
adapt _Protocol Select_ to support those unknown future use-cases.

#### Non-Breaking Changes

Non-breaking changes to the protocol can be done at the schema level, more
specifically through the _Protocol Buffer_ framework. Instead of enumerating the
various update mechanisms, we refer to the _[Updating a Message Type]_ section
of the _Protocol Buffer_ specification.

As an example for a non-breaking change, say we would like to exchange a made up
name via the _Protocol Select_ protocol. We can simply extend the `ProtoSelect`
message type by an `optional string name = 4;` field. Updated implementations
would be able to extract the name from the payload, old implementations would
simply ignore the new field.

#### Breaking Changes

When making breaking changes to the _Protocol Select_ protocol,
implementations need to be able to differentiate the old and the new version on
the wire. This is done via the `version` field in the `ProtoSelect` message,
treated as an ordinal monotonically increasing number, with each increase
identifying a new breaking version of the protocol.

As an example for a made-up breaking change, say we would like the listed
protocols in the `Offer` message to enumerate the protocols that the local node
does *not* support. One would bump the `version` field by `1`. Implementations
supporting both versions are able to differentiate an old and new version
message. Implementations supporting only the old version would reject a new
version message and fail the negotiation. Roll-out strategies need to cope with
such negotiation failure, e.g. through retries with an older version.


## Extensions

### Protocol IDs

The first version of _Protocol Select_ will allow specifying protocols by their
_Protocol Name_, i.e. human readable string representation, only. In order to
optimize on bandwidth, future versions might introduce alternative
representations in a non-breaking manner.

More specifically, this extension would allow specifying protocols by their
_Protocol ID_. A _Protocol ID_ is a [Multicodec] or a combination of
[Multicodec]s. Implementations can specify a protocol either via a _Protocol
Name_ or a _Protocol ID_ by extending the `Protocol` message type definition as
follows:

```diff
message Protocol {
    oneof protocol {
        string name = 1;
+       uint64 id = 2;
    }
}
```

_Protocol Name_ and _Protocol ID_ can be used interchangeably. To ease roll-out
of a _Protocol ID_ for a protocol that has previously been negotiated via its
_Protocol Name_, one might leverage one (or multiple) of the following
mechanisms:

- Extending the libp2p identify protocol, allowing nodes to announce their
  supported protocols both by _Protocol Name_ and _Protocol ID_, thus signaling
  the support for the _Protocol ID_ extension for the concrete protocols.

- Including a protocol both by its _Protocol Name_ and _Protocol ID_ in the list
  of supported protocols.

  Note, when optimistically negotiating a stream protocol as an initiator, with a
  remote which might or might not support a protocol's _Protocol ID_, one can
  send a list containing both the _Protocol Name_ and the _Protocol ID_ for the
  same protocol and directly optimistically send application data.

## FAQ

* _Why don't we define something more sophisticated for uncoordinated TCP
  Simultaneous Open?_

  We make use of TCP Simultaneous Open for NAT Traversal. In this situation, we
  coordinate the roles of client and server using the DCUtR protocol, so there's
  no need to do anything beyond that. The only situation where a Simultaneous
  Open might otherwise occur in the wild is when two peers happen to dial each
  other at the same time. This should occur rarely, and if it happens, a sane
  strategy would be to re-dial the peer after a (randomized) exponential
  backoff.

* _Why don't we use the peer IDs to break the tie on uncoordinated TCP
  Simultaneous Open?_

  We cannot assume that the remote peer knows our peer ID when it is dialing us.
  While this is true in *most* cases, it is possible to dial a multiaddr without
  knowing the peer's ID, and derive the ID from the information presented during
  the handshake.

* _Why don't we use the presence of a security protocol in the multiaddr to
  signal support for Protocol Select?_

  First of all, it's nice to keep unrelated parts of the system independent from
  each other. More importantly though, the proposed logic only works with TCP
  addresses. For QUIC, we didn't plan to change the multiaddr, so we'd have to
  build logic to distinguish between multistream and Protocol Select anyway. We
  _could_ change the multicodec for QUIC, but that would be yet another change
  we'd tie into Protocol Select.

* _Why statically out-of-band specify Protocol Name and Protocol ID mapping, why
  not negotiate mapping in-band?_

  An alternative approach to the proposed _Protocol Name_ _Protocol ID_ mapping
  would be to have a dialer use a _Protocol Name_ at first. A listener could,
  when replying with a `Use` specify a _Protocol Name_ _Protocol ID_ mapping.
  One could then use the _Protocol ID_ instead of the _Protocol Name_ for future
  negotiations on that same connection.

  While this approach would reliev us of the need to specify the _Protocol Name_
  _Protocol ID_ mapping in e.g. libp2p/specs, it does add state to be kept
  across negotiations, thus complicating implementations and potentially
  resulting in state-mismatch edge-cases. Another argument for the current
  approach is that one already has to specify the _Protocol Name_ for each
  protocol, the effort to specify a _Protocol ID_ in addition thus seems
  negligible.

* _Why not two messages, e.g. `Offer` and `Use`?_
* _Why did you use proto2 and not proto3?_
* _Why not include Protocol IDs from the start_?

[Multistream Select]: https://github.com/multiformats/multistream-select
[Noise]: https://github.com/libp2p/specs/tree/master/noise
[TLS]: https://github.com/libp2p/specs/blob/master/tls/tls.md
[DCUtR]: https://github.com/libp2p/specs/pull/173
[uvarint-spec]: https://github.com/multiformats/unsigned-varint
[dnsaddr]: https://github.com/multiformats/multiaddr/blob/master/protocols/DNSADDR.md
[Updating a Message Type]: https://developers.google.com/protocol-buffers/docs/proto#updating
[Multicodec]: https://github.com/multiformats/multicodec
