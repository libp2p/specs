# Multicast DNS
Author: Richard Schneider (makaretu@gmail.com)


## Overview

The goal is to allow peers to discover each other when on the same local network with zero configuration. 
MDNS uses a multicast system of DNS records; this allows all peers on the local network to see all query responses.

Conceptually, it is very simple.  When a peer starts (or detects a network change), it sends a query for all peers. 
As responses come in, the peer adds the other peers information into is local database of peers.

## Definitions

`service-name` is the DNS-SD service name for all IPFS peers. It is defined as `_ipfs._udp.local`.

`host-name` is the name of the peer.  It is derived from the peer's ID and `ipfs.local`, for example 
`Qmid.ipfs.local`.

`peer-id` is the ID of the peer.  It normally is the base-58 enconding of the hash of the peer's public key.

`port` is a port that the peer listens on. Normally 4001.

## Peer Discovery

### Request

To find all peers, a DNS message is sent with the question `_ipfs._udp.local PTR`. 
Peers will then start responding with their details.  

Note that a peer must respond to it's own query.  Thus allows other peers to passively discover it.

### Response

On receipt of a `find all peers` query, a peer sends a DNS response message (QR = 1) that contains
the **answer**

    <service-name> PTR <peer-id>.<service-name>
    
The **additional records** of the response contain the peer's discovery details

    <peer-id>.<service-name> SRV ... <port> <host-name>
    <peer-id>.<service-name> TXT ...
    <host-name>              A <ipv4 address>
    <host-name>              AAAA <ipv6 address>
   

Multiple A and AAAA records are expected. The `TXT` is not needed for IPFS peer discovery, but is required by DNS-SD.

#### Multiported Peers

If a peer is listening on multiple ports, it must respond with multiple `SRV` records for each 
port it is listening on. If the ports do not listen on the same IP addresses, then each 'SRV' record 
must have a different `host-name`.

#### Multiaddress 

For this spec, a multiaddress has the form `/<ip>/<addr>/tcp/<port>/ipfs/<peer-id>`. A multiaddress is
generated from the various Additional Records. 

`peer-id` is the first label of the SRV name

`port` is the the SRV port

`ip` is "ip4" for an A record or "ip6" for an AAAA record.

`addr` is the ip4/ip6 address from the A/AAAA record.


## DNS Service Discovery

DNS-SD support is not needed for IPFS peers to discover each other.  However, it is 
extremely usefull for network admistrators to discover what is running on the 
network.

### Meta Query

This allows discovery of all services.  The question is `_services._dns-sd._udp.local PTR`.

A peer responds with the answer

    _services._dns-sd._udp.local PTR <service-name>
    
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

## Worked Example

**TODO**
