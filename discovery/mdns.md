# Multicast DNS
Author: Richard Schneider (makaretu@gmail.com)


## Overview

The goal is to allow peers to discover each other when on the same local network with zero configuration. 
MDNS uses a multicast system of DNS records; this allows all peers on the local network to see all query responses.

Conceptually, it is very simple.  When a peer starts (or detects a network change), it sends a query for all peers. 
As responses come in, the peer adds the other peers information into is local database of peers.

## Definitions

`service-name` is the DNS-SD service name for all peers. It is defined as `_p2p._udp.local`.

`host-name` is the name of the peer.  It is derived from the peer's ID and `p2p.local`, for example 
`Qmid.p2p.local`.

`peer-id` is the ID of the peer.  It normally is the base-58 enconding of the hash of the peer's public key.

`port` is a port that the peer listens on. Normally 4001.

## Peer Discovery

### Request

To find all peers, a DNS message is sent with the question `_p2p._udp.local PTR`. 
Peers will then start responding with their details.  

Note that a peer must respond to it's own query.  Thus allows other peers to passively discover it.

### Response

On receipt of a `find all peers` query, a peer sends a DNS response message (QR = 1) that contains
the **answer**

    <service-name> PTR <peer-id>.<service-name>
    
The **additional records** of the response contain the peer's discovery details

    <peer-id>.<service-name> TXT "dnsaddr=..."
    
The TXT record contains the multiaddresses that the peer is listening on.  Each multiaddress 
is a TXT attribute with the form `dnsaddr=/ip4/.../tcp/.../p2p/QmId`.  Multiple `dnsaddr` attributes 
are expected.

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

    <peer-id>.<service-name> SRV ... <port> <host-name>
    <host-name>              A <ipv4 address>
    <host-name>              AAAA <ipv6 address>
   
If a peer is listening on multiple ports, it should respond with multiple `SRV` records for each 
port it is listening on. 

### Gotchas

Many existing tools ignore the Additional Records and always send individual queries for the 
peer's discovery details. To accomodate this, a peer should respond to the following queries:

- `<peer-id>.<service-name> SRV`
- `<peer-id>.<service-name> TXT`
- `<host-name> A`
- `<host-name> AAAA`

## References

- [RFC 1035 - Domain Names (DNS)](https://tools.ietf.org/html/rfc1035)
- [RFC 6762 - Multicast DNS](https://tools.ietf.org/html/rfc6762)
- [RFC 6763 - DNS-Based Service Discovery](https://tools.ietf.org/html/rfc6763)
- [Multiaddr](https://github.com/multiformats/multiaddr)

## Worked Example

**TODO**
