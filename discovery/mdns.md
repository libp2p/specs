# Multicast DNS (mDNS)

> Local peer discovery with zero configuration using multicast DNS.

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 1A              | Working Draft  | Active | r2, 2021-10-12  |

Authors: [@richardschneider]

Interest Group: [@yusefnapora], [@raulk], [@daviddias], [@jacobheun]

[@richardschneider]: https://github.com/richardschneider
[@yusefnapora]: https://github.com/yusefnapora
[@raulk]: https://github.com/raulk
[@daviddias]: https://github.com/daviddias
[@jacobheun]: https://github.com/jacobheun

See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Table of Contents

- [Multicast DNS (mDNS)](#multicast-dns-mdns)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Definitions](#definitions)
  - [Find All Peers](#find-all-peers)
    - [Request](#request)
    - [Answer](#answer)
    - [Examples](#examples)
  - [Direct Queries](#direct-queries)
    - [Example](#example)
  - [Find All Services](#find-all-services)
    - [Request](#request-1)
    - [Answer](#answer-1)
  - [References](#references)

## Overview

mDNS allows peers to discover each other when on the same local network with zero configuration. mDNS uses a multicast system of DNS records; this allows all peers on the local network to see all query answers.

When a peer starts or detects a network change, it SHOULD send a query for all peers. As answers come in, the peer adds the other peers' information into its local peer database.

The key words "MUST", "MUST NOT", "SHOULD", "SHOULD NOT" and "MAY" in this document are to be interpreted as described in [RFC 2119](https://tools.ietf.org/html/rfc2119).

## Definitions

- `service-name` is the DNS Service Discovery (DNS-SD) service name for all peers. On the public network, it MUST be `_p2p._udp.local`.
- `peer-name` is the unique identifier of the peer. It MUST be a valid DNS label of at most 63 bytes, and peers MUST compare it case-insensitively. It does not carry meaning; it only needs to be unique. Peers SHOULD generate a random, lower-case alphanumeric string of at least 32 characters in length when booting up their node. Peers SHOULD NOT use their Peer ID here because a future Peer ID could exceed the DNS label limit of 63 characters.
- `host-name` is the fully qualified name of the peer. It SHOULD be `<peer-name>.local`.

In [private networks](https://github.com/libp2p/specs/blob/master/pnet/Private-Networks-PSK-V1.md) the `service-name` MUST contain the base-16 encoding of the network's fingerprint (`<hex>`) in the format `_p2p-<hex>._udp.local`.
This prevents public and private networks from discovering each other's peers.

The fingerprint is derived from the network's 32-byte pre-shared key (PSK):

    fingerprint = SHA-256("libp2p-mdns-pnet-fingerprint" || PSK)[0:5]

where `PSK` is the raw decoded key (not the contents of the key file), `||` is concatenation, and `[0:5]` is the first 5 bytes of the digest. `<hex>` is the lower-case base-16 encoding of the fingerprint, 10 characters long. This keeps the service label within the 15-character limit for DNS-SD service names ([RFC 6763, section 7.2](https://tools.ietf.org/html/rfc6763#section-7.2)).

For example, the PSK `000102…1e1f` (bytes `0x00` to `0x1f`) has the fingerprint `587912df03`, so its `service-name` is `_p2p-587912df03._udp.local`.

The fingerprint only partitions discovery; it is not a security mechanism. Two networks with colliding fingerprints would discover each other's peers but still fail to connect, since connections are protected by the PSK itself.

## Find All Peers

### Request

    <service-name> PTR

For example, `_p2p._udp.local PTR` on the public network.

**Note:** a peer MUST respond to its own query. This allows other peers to passively discover it.

### Answer

On receipt of a `find all peers` query, a peer MUST respond with

    <service-name> PTR <peer-name>.<service-name>

The **additional records** of the response contain the peer's discovery details. The peer MUST include

    <peer-name>.<service-name> TXT "dnsaddr=..."

The TXT record MUST contain at least one multiaddress that the peer is listening on. Each multiaddress MUST be a TXT attribute with the form `dnsaddr=/.../p2p/<peer-id>`. A peer MAY include multiple `dnsaddr` attributes or TXT records; receivers MUST accept both.

Peers SHOULD NOT advertise circuit relay addresses or addresses for browser-only transports (WebSocket, WebTransport, WebRTC), since these are not useful for direct connections on the local network. Peers SHOULD only advertise addresses that are reachable on the local network, and SHOULD NOT advertise loopback addresses.

The peer SHOULD also include the following additional records, which allow generic DNS-SD tools to resolve it:

    <peer-name>.<service-name> SRV ... <host-name>
    <host-name>                A <ipv4 address>
    <host-name>                AAAA <ipv6 address>

On receipt of an answer:

- Receivers MUST ignore answers that carry their own Peer ID.
- Receivers MUST ignore TXT attributes that are not `dnsaddr=` or that fail to parse, and MUST NOT discard the rest of the response because of them.
- Receivers MUST use only the `dnsaddr` attributes to learn a peer's Peer ID and multiaddresses. They MUST NOT rely on SRV, A or AAAA records, whose contents (in particular the SRV port) are not meaningful to libp2p.

### Examples

1. Peer `abc123` sends a `find all peers` query and receives two answers: one from itself and one from another peer (`xyz789`) on the network. Additional records are omitted here.

    ```
    Q:  _p2p._udp.local.  PTR  ?                          # query from abc123
    A:  _p2p._udp.local.  PTR  abc123._p2p._udp.local.    # answer from abc123 (itself)
    A:  _p2p._udp.local.  PTR  xyz789._p2p._udp.local.    # answer from xyz789
    ```

2. The full response from peer `xyz789` in the example above, including its additional records:

    ```
    ;; ANSWER
    _p2p._udp.local.         120  IN  PTR   xyz789._p2p._udp.local.
    ;; ADDITIONAL
    xyz789._p2p._udp.local.  120  IN  TXT   "dnsaddr=/ip4/192.168.1.10/tcp/4001/p2p/12D3KooW…"
                                            "dnsaddr=/ip6/fe80::1/udp/4001/quic-v1/p2p/12D3KooW…"
    xyz789._p2p._udp.local.  120  IN  SRV   0 0 4001 xyz789.local.
    xyz789.local.            120  IN  A     192.168.1.10
    xyz789.local.            120  IN  AAAA  fe80::1
    ```

## Direct Queries

Many existing tools ignore the additional records and send individual queries for the peer's discovery details instead. To accommodate this, a peer SHOULD respond to the following queries:

- `<peer-name>.<service-name> SRV`
- `<peer-name>.<service-name> TXT`
- `<host-name> A`
- `<host-name> AAAA`

### Example

A peer asks `abc123` directly for its TXT record:

```
Q:  abc123._p2p._udp.local.  TXT  ?
A:  abc123._p2p._udp.local.  TXT  "dnsaddr=…" "dnsaddr=…"
```

## Find All Services

Service type enumeration is not needed for peers to discover each other. However, it is useful for network administrators to discover what is running on the network, and it lets generic DNS-SD tools find libp2p peers.

### Request

The following query enumerates all service types advertised on the local network:

    _services._dns-sd._udp.local PTR

### Answer

A peer MAY respond with its `service-name`:

    _services._dns-sd._udp.local PTR <service-name>

For example, on the public network:

    _services._dns-sd._udp.local PTR _p2p._udp.local

## References

- [RFC 1035 - Domain Names (DNS)](https://tools.ietf.org/html/rfc1035)
- [RFC 2119 - Key words for use in RFCs to Indicate Requirement Levels](https://tools.ietf.org/html/rfc2119)
- [RFC 6762 - Multicast DNS](https://tools.ietf.org/html/rfc6762)
- [RFC 6763 - DNS-Based Service Discovery](https://tools.ietf.org/html/rfc6763)
- [Multiaddr](https://github.com/multiformats/multiaddr)
