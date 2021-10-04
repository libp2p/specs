# Addressing in libp2p
> How network addresses are encoded and used in libp2p

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Recommendation | Active | r0, 2021-07-22  |


Authors: [@yusefnapora]

Interest Group: [@mxinden, @Stebalien, @raulk, @marten-seemann, @vyzo]

[@yusefnapora]: https://github.com/yusefnapora
[@mxinden]: https://github.com/mxinden/

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Table of Contents

- [Addressing in libp2p](#addressing-in-libp2p)
    - [Table of Contents](#table-of-contents)
    - [Overview](#overview)
    - [multiaddr in libp2p](#multiaddr-in-libp2p)
        - [multiaddr basics](#multiaddr-basics)
        - [Composing multiaddrs](#composing-multiaddrs)
            - [Encapsulation](#encapsulation)
            - [Decapsulation](#decapsulation)
        - [The p2p multiaddr](#the-p2p-multiaddr)
            - [Historical Note: the `ipfs` multiaddr Protocol](#historical-note-the-ipfs-multiaddr-protocol)
    - [Transport multiaddrs](#transport-multiaddrs)
        - [IP and Name Resolution](#ip-and-name-resolution)
            - [dnsaddr Links](#dnsaddr-links)
        - [TCP](#tcp)
        - [WebSockets](#websockets)
        - [QUIC](#quic)
        - [`p2p-circuit` Relay Addresses](#p2p-circuit-relay-addresses)

## Overview

libp2p makes a distinction between a peer's **identity** and its **location**.
A peer's identity is stable, verifiable, and valid for the entire lifetime of
the peer (whatever that may be for a given application). Peer identities are
derived from public keys as described in the [peer id spec][peer-id-spec].

On a particular network, at a specific point in time, a peer may have one or
more locations, which can be represented using addresses. For example, I may be
reachable via the global IPv4 address of 7.7.7.7 on TCP port 1234.

In a system that only supported TCP/IP or UDP over IP, we could easily write our
addresses with the familiar `<ip>:<port>` notation and store them as tuples of
address and port. However, libp2p was designed to be transport agnostic, which
means that we can't assume that we'll even be using an IP-backed network at all.

To support a growing set of transport protocols without special-casing each
addressing scheme, libp2p uses [multiaddr][multiaddr-repo] to encode network
addresses for all supported transport protocols, in a self-describing manner.

This document does not cover the address format ([multiaddr][multiaddr-repo]),
but rather [how multiaddr is used in libp2p](#multiaddr-in-libp2p). For details
on the former, visit linked spec. For more information on other use cases, or to
find links to multiaddr implementations in various languages, see the [mulitaddr
repository][multiaddr-repo].

## multiaddr in libp2p

multiaddrs are used throughout libp2p for encoding network addresses. When
addresses need to be shared or exchanged between processes, they are encoded in
the binary representation of multiaddr.

When exchanging addresses, peers send a multiaddr containing both their network
address and peer id, as described in [the section on the `p2p`
multiaddr](#the-p2p-multiaddr).

### multiaddr basics

A multiaddr is a sequence of instructions that can be traversed to some
destination.

For example, the `/ip4/7.7.7.7/tcp/1234` multiaddr starts with `ip4`, which is
the lowest-level protocol that requires an address. The `tcp` protocol runs on
top of `ip4`, so it comes next.

The multiaddr above consists of two components, the `/ip4/7.7.7.7` component,
and the `/tcp/1234` component. It's not possible to split either one further;
`/ip4` alone is an invalid multiaddr, because the `ip4` protocol was defined to
require a 32 bit address. Similarly, `tcp` requires a 16 bit port number.

Although we referred to `/ip4/7.7.7.7` and `/tcp/1234` as "components" of a
larger TCP/IP address, each is actually a valid multiaddr according to the
multiaddr spec. However, not every **syntactically valid multiaddr is a
functional description of a process in the network**. As we've seen, even a
simple TCP/IP connection requires composing two multiaddrs into one. See the
section on [composing multiaddrs](#composing-multiaddrs) for information on how
multiaddrs can be combined, and the
[Transport multiaddrs section](#transport-multiaddrs) for the combinations that
describe valid transport addresses.

The [multiaddr protocol table][multiaddr-proto-table] contains all currently
defined protocols and the length of their address components.

### Composing multiaddrs

As shown above, protocol addresses can be composed within a multiaddr in a way
that mirrors the composition of protocols within a networking stack.

The terms generally used to describe composition of multiaddrs are
"encapsulation" and "decapsulation", and they essentially refer to adding and
removing protocol components from a multiaddr, respectively.

#### Encapsulation

A protocol is said to be "encapsulated within" another protocol when data from
an "inner" protocol is wrapped by another "outer" protocol, often by re-framing
the data from the inner protocol into the type of packets, frames or datagrams
used by the outer protocol.

Some examples of protocol encapsulation are HTTP requests encapsulated within
TCP/IP streams, or TCP segments themselves encapsulated within IP datagrams.

The multiaddr format was designed so that addresses encapsulate each other in
the same manner as the protocols that they describe. The result is an address
that begins with the "outermost" layer of the network stack and works
progressively "inward". For example, in the address `/ip4/7.7.7.7/tcp/80/ws`,
the outermost protocol is IPv4, which encapsulates TCP streams, which in turn
encapsulate WebSockets.

All multiaddr implementations provide a way to _encapsulate_ two multiaddrs into
a composite. For example, `/ip4/7.7.7.7` can encapsulate `/tcp/42` to become
`/ip4/7.7.7.7/tcp/42`.

#### Decapsulation

Decapsulation takes a composite multiaddr and removes an "inner" multiaddr from
it, returning the result.

For example, if we start with `/ip4/7.7.7.7/tcp/1234/ws` and decapsulate `/ws`,
the result is `/ip4/7.7.7.7/tcp/1234`.

It's important to note that decapsulation returns the original multiaddr up to
the last occurrence of the decapsulated multiaddr. This may remove more than
just the decapsulated component itself if there are more protocols encapsulated
within it. Using our example above, decapsulating either `/tcp/1234/ws` _or_
`/tcp/1234` from `/ip4/7.7.7.7/tcp/ws` will result in `/ip4/7.7.7.7`. This is
unsurprising if you consider the utility of the `/ip4/7.7.7.7/ws` address that
would result from simply removing the `tcp` component.

### The multiaddr security component

Peers MAY advertise their addresses without a security protocol, e.g.
`/ip4/6.6.6.6/tcp/1234/` or `/ip4/6.6.6.6/udp/1234/quic`. The security handshake
protocol is then negotiated using [multistream-select](../connections/README.md#multistream-select). This is
the way the libp2p handshake worked until mid 2021.
This poses a security problem, as the negotiation was not authenticated and
therefore susceptible to man-in-the-middle attacks. A MITM could modify the list
of supported handshake protocols, thereby forcing a downgrade to a (potentially)
less secure handshake protocol. Note that since QUIC is standardized to use
TLS 1.3, no handshake protocol needs to be negotiated when using QUIC.

Peers SHOULD encapsulate the security protocol in the addresses they advertise,
for example `/ip4/6.6.6.6/tcp/1234/tls` for a TLS 1.3 server listening on TCP
port 1234 and `/ip4/6.6.6.6/tcp/1235/noise` for a Noise server listening on TCP
port 1235. QUIC multiaddrs remain unchanged.
The nodes jump straight into a cryptographic handshake, thus curtailing the
possibility of packet-inspection-based censorship and dynamic downgrade attacks.
This also applies to circuit addresses: the security protocol is encoded in the
`<destination address>` as defined in [`p2p-circuit` Relay Addresses](#p2p-circuit-relay-addresses).

Advertising the secure channel protocol through the peer's Multiaddr instead of
negotiating the protocol in-band forces users to advertise an updated Multiaddr
when changing the secure channel protocol in use. This is especially cumbersome
when using hardcoded Multiaddresses. Users may leverage the [dnsaddr] Multiaddr
protocol as well as using a new UDP or TCP port for the new protocol to ease the
transition.

Implementations using [Protocol Select](https://github.com/libp2p/specs/pull/349/)
(**TODO**: update link) MUST encapsulate the security protocol in the multiaddr.
Note that it’s not valid to assume that any node that encapsulated the security
protocol in their multiaddr also supports Protocol Select.


### The p2p multiaddr

libp2p defines the `p2p` multiaddr protocol, whose address component is the
[peer id][peer-id-spec] of a libp2p peer. The text representation of a `p2p`
multiaddr looks like this:

```
/p2p/QmYyQSo1c1Ym7orWxLYvCrM2EmxFTANf8wXmmE7DWjhx5N
```

Where `QmYyQSo1c1Ym7orWxLYvCrM2EmxFTANf8wXmmE7DWjhx5N` is the string representation
of a peer's peer ID derived from its public key.

By itself, a `p2p` address does not give you enough addressing information to
locate a peer on the network; it is not a transport address. However, like the
`ws` protocol for WebSockets, a `p2p` address can be [encapsulated
within](#encapsulation) another multiaddr.

For example, the above `p2p` address can be combined with the transport address
on which the node is listening:

```
/ip4/7.7.7.7/tcp/1234/p2p/QmYyQSo1c1Ym7orWxLYvCrM2EmxFTANf8wXmmE7DWjhx5N
```

This combination of transport address plus `p2p` address is the format in which
peers exchange addresses over the wire in the [identify protocol][identify-spec]
and other core libp2p protocols.

#### Historical Note: the `ipfs` multiaddr Protocol

The `p2p` multiaddr protocol was originally named `ipfs`, and we've been eliminating
support for the ipfs string representation of this multiaddr component. It may be
printed as `/ipfs/<peer-id>` instead of `/p2p/<peer-id>` in its string representation
depending on the implementation in use. Both names resolve to the same protocol code,
and they are equivalent in the binary form.


## Transport multiaddrs

Because multiaddr is an open and extensible format, it's not possible to
guarantee that any valid multiaddr is semantically meaningful or usable in a
particular network. For example, the `/tcp/42` multiaddr, while valid, is not
useful on its own as a locator.

This section covers the types of multiaddr supported by libp2p transports. It's
possible that this section will go out of date as new transport modules are
developed, at which point pull-requests to update this document will be greatly
appreciated.

### IP and Name Resolution

Most libp2p transports use the IP protocol as a foundational layer, and as a
result, most transport multiaddrs will begin with a component that represents an
IPv4 or IPv6 address.

This may be an actual address, such as `/ip4/7.7.7.7` or
`/ip6/fe80::883:a581:fff1:833`, or it could be something that resolves to an IP
address, like a domain name.

libp2p will attempt to resolve "name-based" addresses into IP addresses. The
current [multiaddr protocol table][multiaddr-proto-table] defines four
resolvable or "name-based" protocols:

| protocol  | description                                                        |
|-----------|--------------------------------------------------------------------|
| `dns`     | Resolves DNS A and AAAA records into both IPv4 and IPv6 addresses. |
| `dns4`    | Resolves DNS A records into IPv4 addresses.                        |
| `dns6`    | Resolves DNS AAAA records into IPv6 addresses.                     |
| `dnsaddr` | Resolves multiaddrs from a special TXT record.                     |


When the `/dns` protocol is used, the lookup may result in both IPv4 and IPv6
addresses, in which case IPv6 will be preferred. To explicitly resolve to IPv4
or IPv6 addresses, use the `/dns4` or `/dns6` protocols, respectively.

Note that in some restricted environments, such as inside a web browser, libp2p
may not have access to the resolved IP addresses at all, in which case the
runtime will determine what IP version is used.

When a name-based multiaddr encapsulates another multiaddr, only the name-based
component is affected by the lookup process. For example, if `example.com`
resolves to `1.2.3.4`, libp2p will resolve the address
`/dns4/example.com/tcp/42` to `/ip4/1.2.3.4/tcp/42`.

#### dnsaddr Links

A libp2p-specific DNS-backed format, `/dnsaddr` resolves addresses from a `TXT`
record associated with the `_dnsaddr` subdomain of a given domain.

Note that this is different from [dnslink](https://dnslink.io/), which uses
`TXT` records to reference content addressed objects.

For example, resolving `/dnsaddr/libp2p.io` will perform a `TXT` lookup for
`_dnsaddr.libp2p.io`. If the result contains entries of the form
`dnsaddr=<multiaddr>`, the embedded multiaddrs will be parsed and used.

For example, asking the DNS server for the TXT records of one of the bootstrap
nodes, `ams-2.bootstrap.libp2p.io`, returns the following records:
```
> dig +short _dnsaddr.ams-2.bootstrap.libp2p.io txt
"dnsaddr=/dns4/ams-2.bootstrap.libp2p.io/tcp/443/wss/p2p/QmbLHAnMoJPWSCR5Zhtx6BHJX9KiKNN6tpvbUcqanj75Nb"
"dnsaddr=/ip6/2604:1380:2000:7a00::1/tcp/4001/p2p/QmbLHAnMoJPWSCR5Zhtx6BHJX9KiKNN6tpvbUcqanj75Nb"
"dnsaddr=/ip4/147.75.83.83/tcp/4001/p2p/QmbLHAnMoJPWSCR5Zhtx6BHJX9KiKNN6tpvbUcqanj75Nb"
"dnsaddr=/ip6/2604:1380:2000:7a00::1/udp/4001/quic/p2p/QmbLHAnMoJPWSCR5Zhtx6BHJX9KiKNN6tpvbUcqanj75Nb"
"dnsaddr=/ip4/147.75.83.83/udp/4001/quic/p2p/QmbLHAnMoJPWSCR5Zhtx6BHJX9KiKNN6tpvbUcqanj75Nb"
"dnsaddr=/dns6/ams-2.bootstrap.libp2p.io/tcp/443/wss/p2p/QmbLHAnMoJPWSCR5Zhtx6BHJX9KiKNN6tpvbUcqanj75Nb"
```

The `dnsaddr` lookup serves a similar purpose to a standard A-record DNS lookup,
however there are differences that can be important for some use cases. The most
significant is that the `dnsaddr` entry contains a full multiaddr, which may
include a port number or other information that an A-record lacks, and it may
even specify a non-IP transport. Also, there are cases in which the A-record
already serves a useful purpose; using `dnsaddr` allows a second "namespace" for
libp2p registrations.

### TCP

The libp2p TCP transport is supported in all implementations and can be used
wherever TCP/IP sockets are accessible.

Addresses for the TCP transport are of the form `<ip-multiaddr>/tcp/<tcp-port>`,
where `<ip-multiaddr>` is a multiaddr that resolves to an IP address, as
described in the [IP and Name Resolution section](#ip-and-name-resolution).
The `<tcp-port>` argument must be a 16-bit unsigned integer.

### WebSockets

WebSocket connections are encapsulated within TCP/IP sockets, and the WebSocket
multiaddr format mirrors this arrangement.

A libp2p WebSocket multiaddr is of the form `<tcp-multiaddr>/ws` or
`<tcp-multiaddr>/wss` (TLS-encrypted), where `<tcp-multiaddr`> is a valid
mulitaddr for the TCP transport, as [described above](#tcp).

### QUIC

QUIC sessions are encapsulated within UDP datagrams, and the libp2p QUIC
multiaddr format mirrors this arrangement.

A libp2p QUIC multiaddr is of the form `<ip-multiaddr>/udp/<udp-port>/quic`,
where `<ip-multiaddr>` is a multiaddr that resolves to an IP address, as
described in the [IP and Name Resolution section](#ip-and-name-resolution).
The `<udp-port>` argument must be a 16-bit unsigned integer in network byte order.


### `p2p-circuit` Relay Addresses

The libp2p [circuit relay protocol][relay-spec] allows a libp2p peer A to
communicate with another peer B via a third party C. This is useful for
circumstances where A and B would be unable to communicate directly.

Once a connection to the relay is established, peers can accept incoming
connections through the relay, using a `p2p-circuit` address.

Like the `ws` WebSocket multiaddr protocol the `p2p-circuit` multiaddr does not
carry any additional address information. Instead it is composed with two other
multiaddrs to describe a relay circuit.

A full `p2p-circuit` address that describes a relay circuit is of the form:
`<relay-multiaddr>/p2p-circuit/<destination-multiaddr>`.

`<relay-multiaddr>` is the full address for the peer relaying the traffic (the
"relay node").

The details of the transport connection between the relay node and the
destination peer are usually not relevant to other peers in the network, so
`<destination-multiaddr>` generally only contains the `p2p` address of the
destination peer.

A full example would be:

```
/ip4/127.0.0.1/tcp/5002/p2p/QmdPU7PfRyKehdrP5A3WqmjyD6bhVpU1mLGKppa2FjGDjZ/p2p-circuit/p2p/QmVT6GYwjeeAF5TR485Yc58S3xRF5EFsZ5YAF4VcP3URHt
```

Here, the destination peer has the peer id
`QmVT6GYwjeeAF5TR485Yc58S3xRF5EFsZ5YAF4VcP3URHt` and is reachable through a
relay node with peer id `QmdPU7PfRyKehdrP5A3WqmjyD6bhVpU1mLGKppa2FjGDjZ` running
on TCP port 5002 of the IPv4 loopback interface.

#### Relay addresses and multiaddr security component

Instead of negotiating the security protocol in-band, security protocols should
be encapsulated in the multiaddr (see [The multiaddr security component
section](#the-multiaddr-security-component)). Establishing a single relayed
connection involves 3 security protocol upgrades:

1. Upgrading the connection from the source to the relay.

   The security protocol is specified in the relay multiaddr (before
   `p2p-circuit`).

   Example: `/ip4/6.6.6.6/tcp/1234/tls/p2p/QmRelay/p2p-circuit/<destination-multiaddr>`

2. Upgrading the connection from the relay to the destination.

   The security protocol is specified in the destination multiaddr (after
   `p2p-circuit`).

   Note: Specifying this security protocol is only necessary for active
   relaying. In the case of passive relaying the connection established by the
   destination to the relay will be used to relay the connection.

   Example:
   - Passive relaying: `<relay-multiaddr>/p2p-circuit/p2p/QmDestination`
   - Active relaying: `<relay-multiaddr>/p2p-circuit/ip4/6.6.6.6/tcp/1234/tls/p2p/QmDestination`

3. Upgrading the relayed connection from the source to the destination.

   The security protocol is specified by appending
   `/p2p-circuit-security/<relayed-connection-security-protocol>` to the full
   address.

   Example: `<relay-mulitaddr>/p2p-circuit/<destination-multiaddr>/p2p-circuit-security/tls`

   Note: One might be tempted to not specify (3) and simply use the security
   protocol in (2). This would break if the security protocol used for (2) can
   not be used for (3), e.g. in the case where the relay establishes a QUIC
   connection to the destination secured via TLS and the source only supports
   Noise.

   See [Security protocol selection for the relayed connection] for details on
   how the above integrates with the circuit relayv 2 _Hop_ and _Stop_ protocol.


[peer-id-spec]: ../peer-ids/peer-ids.md
[identify-spec]: ../identify/README.md
[multiaddr-repo]: https://github.com/multiformats/multiaddr
[multiaddr-proto-table]: https://github.com/multiformats/multiaddr/blob/master/protocols.csv
[relay-spec]: ../relay/README.md
[Security protocol selection for the relayed connection]: ../relay/circuit-v2.md#security-protocol-selection-for-the-relayed-connection
