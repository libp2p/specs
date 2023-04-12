# AutonatV2: spec


| Lifecycle Stage | Maturity                 | Status | Latest Revision |
|-----------------|--------------------------|--------|-----------------|
| 1A              | Working Draft            | Active | r1, 2023-04-12  |

Authors: [@sukunrt]

Interest Group: [@marten-seemann], [@marcopolo], [@mxinden]

[@sukunrt]: https://github.com/sukunrt
[@marten-seemann]: https://github.com/marten-seemann
[@mxinden]: https://github.com/mxinden
[@marcopolo]: https://github.com/marcopolo


## Overview

A priori, a node cannot know if it is behind a NAT / firewall or if it is
publicly reachable. Knowing its NAT status is essential for the node to be
well-behaved in the network: A node that's behind a doesn't need to
advertise its (undialable) addresses to the rest of the network, preventing
superfluous dials from other peers. Furthermore, it might actively seek to
improve its connectivity by finding a relay server, which would allow other
peers to establish a relayed connection.

`autonat v2` allows nodes to determine reachability for individual addresses. 
Using `autonat v2` nodes can build an address pipeline where they can test 
individual addresses discovered by different sources like identify, upnp 
mappings, circuit addresses etc for reachability.

Compared to `autonat v1` there are two major differences
1. `autonat v1` allowed testing reachability for the node. `autonat v2` allows for testing reachability for an individual address
2. `autonat v2` provides a mechanism for nodes to verify whether the peer 
actually successfully dialled an address.


## AutoNAT V2 Protocol

A node wishing to determine reachability of a particular adddress sends a 
`DialRequest` message to peer B on a stream with protocol ID
`/libp2p/autonat/2.0.0/dial-request`. This `DialRequest` message has the 
address and a uint64 nonce. 

Upon receiving this message the peer attempts to dial the address and opens a 
stream with  Protocol ID `/libp2p/autonat/2.0.0/dial-attempt` and sends a 
`DialAttempt` message with the nonce received in the `DialRequest`. The peer 
MUST NOT dial any address other than the address provided in the `DialRequest` 
message.

Upon completion of the dial attempt, the peer sends a `DialResponse` to the 
initiator node on the `/libp2p/autonat/2.0.0/dial-request` stream.

The initiator SHOULD check that the nonce received in the `Dial` message is the 
same as the nonce the initiator sent in the `DialRequest` message. If the nonce 
received in the `Dial` message is different the initiator MUST discard this 
`DialResponse`

### Requirements for ResponseStatus

The `ResponseStatus` sent by the peer in the `DialResponse` message MUST be set
according to the following requirements

`OK`: the peer was able to dial the address successfully.
`E_DIAL_ERROR`: the peer attempted a dial and was unable to connect.
`E_DIAL_REFUSED`: the peer could have dialed the address but didn't attempt a 
dial because of rate limiting, resource limit reached or blacklisting.
`E_TRANSPORT_NOT_SUPPORTED`: the peer didn't dial because it didn't have the
ability to dial the requested transport.
`E_BAD_REQUEST`: the peer didn't dial because it was unable to decode the 
message. This includes inability to decode the requested address to dial.
`E_INTERNAL_ERROR`: error not classified within the above error codes occured 
on peer that prevented it from completing the request.

Implementations MUST count `OK` as a successful dial and MUST only count 
`E_DIAL_ERROR` as an unsuccessful dial. Implementations MUST discard error codes
other than these two in calculating the reachability of the requested address. 

### Consideration for DDOS Prevention

In order to prevent attacks like the one described in [RFC 3489, Section
12.1.1](https://www.rfc-editor.org/rfc/rfc3489#section-12.1.1) (see excerpt
below), implementations MUST NOT dial any multiaddress unless it is based on the
IP address the requesting node is observed as. This restriction as well implies 
that implementations MUST NOT accept dial requests via relayed connections as 
one can not validate the IP address of the requesting node.

> RFC 3489 12.1.1 Attack I: DDOS Against a Target
>
> In this case, the attacker provides a large number of clients with the same
> faked MAPPED-ADDRESS that points to the intended target. This will trick all
> the STUN clients into thinking that their addresses are equal to that of the
> target. The clients then hand out that address in order to receive traffic on
> it (for example, in SIP or H.323 messages). However, all of that traffic
> becomes focused at the intended target. The attack can provide substantial
> amplification, especially when used with clients that are using STUN to enable
> multimedia applications.


## Implementation Suggestions

For any given address, implementations SHOULD do the following
- periodically recheck reachability status
- query multiple peers to determine reachability

The suggested heuristic for implementations is to consider an address 
reachable if more than 3 peers report a successful dial and to consider an 
address unreachable if more than 3 peers report unsuccessful dials. 

Implementations are free to use different heuristics than this one


## Protobufs

All RPC messages sent over a stream are prefixed with the message length in
bytes, encoded as an unsigned variable length integer as defined by the
[multiformats unsigned-varint spec][uvarint-spec].

```proto
syntax = "proto3";

message Message {
  enum MessageType {
    DIAL_REQUEST  = 0;
    DIAL_RESPONSE = 1;
    DIAL_ATTEMPT  = 2;
  }

  enum ResponseStatus {
    OK                        = 0;
    E_DIAL_ERROR              = 100;
    E_DIAL_REFUSED            = 101;
    E_TRANSPORT_NOT_SUPPORTED = 102;
    E_BAD_REQUEST             = 200;
    E_INTERNAL_ERROR          = 300;
  }

  message DialRequest {
    bytes addr = 1;
    fixed64 nonce = 2;
  }

  message DialResponse {
    ResponseStatus status = 1;
    string statusText = 2;
  }

  message DialAttempt {
    fixed64 nonce = 1;
  }

  MessageType type = 1;
  DialRequest dialRequest = 2;
  DialResponse dialResponse = 3;
  DialAttempt dialAttempt = 4;
}
```

[uvarint-spec]: https://github.com/multiformats/unsigned-varint



