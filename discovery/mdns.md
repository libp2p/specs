# Multicast DNS (mDNS)

> Local peer discovery with zero configuration using multicast DNS.

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 0A              | Working Draft  | Active | r1, 2019-05-05  |

Authors: [@richardschneider]

Interest Group: [@yusefnapora], [@raulk], [@daviddias], [@jacobheun]

[@richardschneider]: https://github.com/richardschneider
[@yusefnapora]: https://github.com/yusefnapora
[@raulk]: https://github.com/raulk
[@daviddias]: https://github.com/daviddias
[@jacobheun]: https://github.com/jacobheun

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Table of Contents

- [Multicast DNS (mDNS)](#multicast-dns-mdns)
    - [Table of Contents](#table-of-contents)
    - [Overview](#overview)
    - [Definitions](#definitions)
    - [Peer Discovery](#peer-discovery)
        - [Request](#request)
        - [Response](#response)
    - [DNS Service Discovery](#dns-service-discovery)
        - [Meta Query](#meta-query)
        - [Find All Response](#find-all-response)
        - [Gotchas](#gotchas)
    - [Issues](#issues)
    - [References](#references)
    - [Worked Examples](#worked-examples)
        - [Meta Query](#meta-query-1)
            - [Question](#question)
            - [Answer](#answer)
        - [Find All Peers](#find-all-peers)
            - [Question](#question-1)
            - [Answer](#answer-1)
            - [Additional Records](#additional-records)

## Overview

The goal is to allow peers to discover each other when on the same local network with zero configuration. mDNS uses a multicast system of DNS records; this allows all peers on the local network to see all query responses.

Conceptually, it is very simple. When a peer starts (or detects a network change), it sends a query for all peers. As responses come in, the peer adds the other peers' information into its local database of peers.

## Definitions

- `service-name` is the DNS Service Discovery (DNS-SD) service name for all peers. It is defined as `_p2p._udp.local`.
- `host-name` is the fully qualified name of the peer. It is derived from the peer's name and `p2p.local`.
- `peer-name` is the case-insensitive unique identifier of the peer, and is less than 64 characters. It is normally the base-32 encoding of the peer's ID.

   If the encoding of the peer's ID exceeds 63 characters, then the [Split at 63rd character](https://github.com/ipfs/in-web-browsers/issues/89#issue-341357014) workaround can be used.

If a [private network](https://github.com/libp2p/specs/blob/master/pnet/Private-Networks-PSK-V1.md) is in use, then the `service-name` contains the base-16 encoding of the network's fingerprint  as in `_p2p-X._udp.local`. 
The prevents public and private networks from discovering each other's peers.

## Peer Discovery

### Request

To find all peers, a DNS message is sent with the question `_p2p._udp.local PTR`. Peers will then start responding with their details.

Note that a peer must respond to its own query. This allows other peers to passively discover it.

### Response

On receipt of a `find all peers` query, a peer sends a DNS response message (QR = 1) that contains the **answer**

```
<service-name> PTR <peer-name>.<service-name>
```

The **additional records** of the response contain the peer's discovery details:

```
<peer-name>.<service-name> TXT "dnsaddr=..."
```

The TXT record contains the multiaddresses that the peer is listening on. Each multiaddress is a TXT attribute with the form `dnsaddr=/.../p2p/QmId`. Multiple `dnsaddr` attributes and/or TXT records are allowed.

## DNS Service Discovery

DNS-SD support is not needed for peers to discover each other. However, it is extremely useful for network administrators to discover what is running on the network.

### Meta Query

This allows discovery of all services. The question is `_services._dns-sd._udp.local PTR`.

A peer responds with the answer

```
    _services._dns-sd._udp.local PTR <service-name>
```   
   
### Find All Response

On receipt of a `find all peers` query, the following **additional records** should be included

```
    <peer-name>.<service-name> SRV ... <host-name>
    <host-name>              A <ipv4 address>
    <host-name>              AAAA <ipv6 address>
```

### Gotchas

Many existing tools ignore the Additional Records, and always send individual queries for the peer's discovery details. To accomodate this, a peer should respond to the following queries:

- `<peer-name>.<service-name> SRV`
- `<peer-name>.<service-name> TXT`
- `<host-name> A`
- `<host-name> AAAA`

## Issues

[ ] mDNS requires link-local addresses. Loopback and "NAT busting" addresses should not sent and must be ignored on receipt?
 
## References

- [RFC 1035 - Domain Names (DNS)](https://tools.ietf.org/html/rfc1035)
- [RFC 6762 - Multicast DNS](https://tools.ietf.org/html/rfc6762)
- [RFC 6763 - DNS-Based Service Discovery](https://tools.ietf.org/html/rfc6763)
- [Multiaddr](https://github.com/multiformats/multiaddr)

## Worked Examples

Asumming that `peer-id` is `QmQusTXc1Z9C1mzxsqC9ZTFXCgSkpBRGgW4Jk2QYHxKE22`, then the `peer-name` is `ciqcmoputolsfsigvm7nx5fwkko2eq26h46qhbj6o4co7uyn2f2srdy` (base32 encoding of the peer ID).

To make the examples more readable `id` and `name` are used.

### Meta Query

Goal: find all services on the local network.

#### Question

```
_services._dns-sd._udp.local PTR
```

#### Answer

```
_services._dns-sd._udp.local IN PTR _p2p._udp.local
```

### Find All Peers

Goal: find all peers on the local network.

#### Question

```
_p2p._udp.local PTR
```

#### Answer

```
_p2p._udp.local IN PTR `name`._p2p._udp.local
```

#### Additional Records

- `name`._p2p._udp.local IN TXT dnsaddr=/ip6/fe80::7573:b0a8:46b0:bfea/tcp/4001/ipfs/`id`
- `name`._p2p._udp.local IN TXT dnsaddr=/ip4/192.168.178.21/tcp/4001/ipfs/'id'
