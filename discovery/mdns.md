# Multicast DNS
Author: Richard Schneider (makaretu@gmail.com)


## Overview

The goal is to allow peers to discover each other when on the same local network with zero configuration. 
MDNS uses a multicast system of DNS records; this allows all peers on the local network to see all query responses.

Conceptually, it is very simple.  When a peer starts (or detects a network change), it sends a query for all peers. 
As responses come in, the peer adds the other peers information into is local database of peers.

## Definitions

`service-name` is the DNS-SD service name for all peers. It is defined as `_p2p._udp.local`.

`host-name` is the fully qualified name of the peer.  It is derived from the peer's name and `p2p.local`.

`peer-name` is the case-insenstive unique identifier of the peer and less than 64 characters.  
It is normally the base-32 encoding of peer's ID. 

If the encoding of the peer's ID exceeds 63 characters, then the [Split at 63rd character](https://github.com/ipfs/in-web-browsers/issues/89#issue-341357014) 
workaround can be used.

## Peer Discovery

### Request

To find all peers, a DNS message is sent with the question `_p2p._udp.local PTR`. 
Peers will then start responding with their details.  

Note that a peer must respond to it's own query.  This allows other peers to passively discover it.

### Response

On receipt of a `find all peers` query, a peer sends a DNS response message (QR = 1) that contains
the **answer**

    <service-name> PTR <peer-name>.<service-name>
    
The **additional records** of the response contain the peer's discovery details

    <peer-name>.<service-name> TXT "dnsaddr=..."
    
The TXT record contains the multiaddresses that the peer is listening on.  Each multiaddress 
is a TXT attribute with the form `dnsaddr=.../p2p/QmId`.  Multiple `dnsaddr` attributes 
and/or TXT records are allowed.

## DNS Service Discovery

DNS-SD support is not needed for peers to discover each other.  However, it is 
extremely usefull for network administrators to discover what is running on the 
network.

### Meta Query

This allows discovery of all services.  The question is `_services._dns-sd._udp.local PTR`.

A peer responds with the answer

    _services._dns-sd._udp.local PTR <service-name>
    
### Find All Response

On receipt of a `find all peers` query, the following **additional records** should be included

    <peer-name>.<service-name> SRV ... <host-name>
    <host-name>              A <ipv4 address>
    <host-name>              AAAA <ipv6 address>
   
### Gotchas

Many existing tools ignore the Additional Records and always send individual queries for the 
peer's discovery details. To accomodate this, a peer should respond to the following queries:

- `<peer-name>.<service-name> SRV`
- `<peer-name>.<service-name> TXT`
- `<host-name> A`
- `<host-name> AAAA`

## Issues

- MDNS requires link local addresses.  Loopback and "nat busting" addresses should not sent and must
 be ignored on receipt?
 
## References

- [RFC 1035 - Domain Names (DNS)](https://tools.ietf.org/html/rfc1035)
- [RFC 6762 - Multicast DNS](https://tools.ietf.org/html/rfc6762)
- [RFC 6763 - DNS-Based Service Discovery](https://tools.ietf.org/html/rfc6763)
- [Multiaddr](https://github.com/multiformats/multiaddr)

## Worked Example

Asumming that `peer-id` is `QmQusTXc1Z9C1mzxsqC9ZTFXCgSkpBRGgW4Jk2QYHxKE22`.  Then the `peer-name` is `ciqcmoputolsfsigvm7nx5fwkko2eq26h46qhbj6o4co7uyn2f2srdy`.

To make the examples more readable `id` and `name` are used.


### Meta Query

Find all services on the local network.

#### Question

`_services._dns-sd._udp.local PTR`

#### Answer

_services._dns-sd._udp.local IN PTR _p2p._udp.local

### Find All Peers

Find all peers on the local network

#### Question

_p2p._udp.local PTR

#### Answer

_p2p._udp.local IN PTR `name`._p2p._udp.local

#### Additional Records

- `name`._p2p._udp.local IN TXT dnsaddr=/ip6/fe80::7573:b0a8:46b0:bfea/tcp/4001/ipfs/`id`
- `name`._p2p._udp.local IN TXT dnsaddr=/ip4/192.168.178.21/tcp/4001/ipfs/'id'
