# AutonatV2: spec


| Lifecycle Stage | Maturity                 | Status | Latest Revision |
|-----------------|--------------------------|--------|-----------------|
| 1A              | Working Draft            | Active | r2, 2023-04-15  |

Authors: [@sukunrt]

Interest Group: [@marten-seemann], [@marcopolo], [@mxinden]

[@sukunrt]: https://github.com/sukunrt
[@marten-seemann]: https://github.com/marten-seemann
[@mxinden]: https://github.com/mxinden
[@marcopolo]: https://github.com/marcopolo


## Overview

A priori, a node cannot know if it is behind a NAT / firewall or if it is
publicly reachable. Knowing its NAT status is essential for the node to be
well-behaved in the network: A node that's behind a NAT / firewall doesn't need
to advertise its (undialable) addresses to the rest of the network, preventing
superfluous dials from other peers. Furthermore, it might actively seek to
improve its connectivity by finding a relay server, which would allow other
peers to establish a relayed connection.

In `autonat v2` client sends a priority ordered list of addresses. On receiving
this list the server dials the first address on the list that it is capable of
dialing. `autonat v2` allows nodes to determine reachability for individual
addresses. Using `autonat v2` nodes can build an address pipeline where they can
test individual addresses discovered by different sources like identify, upnp
mappings, circuit addresses etc for reachability. Having a priority ordered list
of addresses provides the ability to verify low priority addresses.
Implementations can generate low priority address guesses and add them to
requests for high priority addresses as a nice to have. This is especially
helpful when introducing a new transport. Initially, such a transport will not
be widely supported in the network. Requests for verifying such addresses can be
reused to get information about other addresses

Compared to `autonat v1` there are two major differences
1. `autonat v1` allowed testing reachability for the node. `autonat v2` allows
testing reachability for an individual address
2. `autonat v2` provides a mechanism for nodes to verify whether the peer
actually successfully dialled an address.


## AutoNAT V2 Protocol


![Autonat V2 Interaction](autonat-v2.svg)


A node wishing to determine reachability of its adddresses sends a `DialRequest`
message to a peer on a stream with protocol ID
`/libp2p/autonat/2.0.0/dial`. 

This `DialRequest` message has a list of `Candidate`s. Each item in
this list contains an address and a fixed64 nonce. The list is ordered in
descending order of priority for verfication.

Upon receiving this message the peer attempts to dial the first candidate from
the list of candidates that it is capable of dialing. It dials the candidate
address, opens a stream with Protocol ID `/libp2p/autonat/2.0.0/attempt` and
sends a `DialAttempt` message with the candidate nonce. The peer MUST NOT dial
any candidate other than the first candidate in the list that it is capable of
dialing.

Upon completion of the dial attempt, the peer sends a `DialResponse` message to
the initiator node on the `/libp2p/autonat/2.0.0/dial` stream with the
index(0 based) of the candidate that it attempted to dial and the appropriate
`ResponseStatus`. see [Requirements For
ResponseStatus](#requirements-for-responsestatus)

The initiator MUST check that the nonce received in the `DialAttempt` is the
same as the nonce the initiator sent in the `Candidate` for the candidate
index received in `DialResponse`. If the nonce is different, the initiator MUST
discard this response.


### Requirements for ResponseStatus

On receiving a `DialRequest` the peer selects the first candidate on the list it
is capable of dialing. This candidate address is referred to as _addr_. The
`ResponseStatus` sent by the peer in the `DialResponse` message MUST be set
according to the following requirements

`OK`: the peer was able to dial _addr_ successfully.

`E_DIAL_ERROR`: the peer attempted to dial _addr_ and was unable to connect. 

`E_DIAL_REFUSED`: the peer didn't attempt a dial because of rate limiting,
resource limit reached or blacklisting.

`E_TRANSPORT_NOT_SUPPORTED`: the peer didn't have the ability to dial any of the
requested addresses.

`E_BAD_REQUEST`: the peer didn't attempt a dial because it was unable to decode
the message.

`E_INTERNAL_ERROR`: error not classified within the above error codes occured on
peer that prevented it from completing the request.

Implementations MUST discard responses with status codes they do not understand

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

The suggested heuristic for implementations is to consider an address reachable
if more than 3 peers report a successful dial and to consider an address
unreachable if more than 3 peers report unsuccessful dials. 

Implementations are free to use different heuristics than this one


## RPC Messages

All RPC messages sent over a stream are prefixed with the message length in
bytes, encoded as an unsigned variable length integer as defined by the
[multiformats unsigned-varint spec][uvarint-spec]. 

All RPC messages on stream `/libp2p/autonat/2.0.0/dial` are of type
`DialMessage`. A `DialRequest` message is sent as a `DialMessage` with the `dialRequest`
field set and the `type` field set to `DIAL_REQUEST`. `DialResponse` is handled
similarly.

On stream `/libp2p/autonat/2.0.0/attempt`, there is a single message type
`AttemptMessage`

```proto
syntax = "proto3";

message DialMessage {
  enum Type {
    DIAL_REQUEST  = 0;
    DIAL_RESPONSE = 1;
  }

  Type type          = 1;
  DialRequest dialRequest   = 2;
  DialResponse dialResponse = 3;
}

message Candidate {
  bytes addr = 1;
  fixed64 nonce = 2;
}

message DialRequest {
  repeated Candidate candidates = 1;
}

message DialResponse {
  enum ResponseStatus {
      OK                        = 0;
      E_DIAL_ERROR              = 100;
      E_DIAL_REFUSED            = 101;
      E_TRANSPORT_NOT_SUPPORTED = 102;
      E_BAD_REQUEST             = 200;
      E_INTERNAL_ERROR          = 300;
    }

    ResponseStatus status = 1;
    string statusText = 2;
    int32 addrIdx = 3;
}

message AttemptMessage {
  enum Type {
    DIAL_ATTEMPT = 0;
  }

  Type type = 1;
  DialAttempt dialAttempt = 2;
}

message DialAttempt {
    fixed64 nonce = 1;
}
```

[uvarint-spec]: https://github.com/multiformats/unsigned-varint

