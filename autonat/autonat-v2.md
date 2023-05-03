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
dialing. As the server dials _exactly_ one address from the list, `autonat v2`
allows nodes to determine reachability for individual addresses. Using `autonat
v2` nodes can build an address pipeline where they can test individual addresses
discovered by different sources like identify, upnp mappings, circuit addresses
etc for reachability. Having a priority ordered list of addresses provides the
ability to verify low priority addresses. Implementations can generate low
priority address guesses and add them to requests for high priority addresses as
a nice to have. This is especially helpful when introducing a new transport.
Initially, such a transport will not be widely supported in the network.
Requests for verifying such addresses can be reused to get information about
other addresses

Compared to `autonat v1` there are two major differences
1. `autonat v1` allowed testing reachability for the node. `autonat v2` allows
testing reachability for an individual address
2. `autonat v2` provides a mechanism for nodes to verify whether the peer
actually successfully dialled an address.
3. `autonat v2` provides a mechanism for nodes to dial an IP address different
from the requesting node's observed IP address without risking amplification
attacks. `autonat v1` disallowed such dials to prevent amplification attacks.



## AutoNAT V2 Protocol


![Autonat V2 Interaction](autonat-v2.svg)


A node wishing to determine reachability of its adddresses sends a `DialRequest`
message to a peer on a stream with protocol ID `/libp2p/autonat/2.0.0/dial`.
Each `DialRequest` is sent on a new stream.

This `DialRequest` message has a list of `Candidate`s. Each item in this list
contains an address and a fixed64 nonce. The list is ordered in descending order
of priority for verfication.

Upon receiving this message the peer selects the first candidate from the list
of candidates that it is capable of dialing. The peer MUST NOT dial any
candidate other than this selected candidate. If this selected candidate address
has an IP address different from the requesting node's observed IP address, peer
initiates the Amplification attack prevention mechanism (see [Amplification
Attack Prevention](#amplification-attack-prevention) ). On completion, the peer
proceeds to the next step. If the selected address has the same IP address as
the requesting node's observed IP address, peer directly proceeds to the next
step skipping Amplification Attack prevention steps.


The peer dials the selected candidate's address, opens a stream with Protocol ID
`/libp2p/autonat/2.0.0/attempt` and sends a `DialAttempt` message with the
candidate nonce. The peer MUST close this stream after sending the `DialAttempt`
message.

Upon completion of the dial attempt, the peer sends a `DialResponse` message to
the initiator node on the `/libp2p/autonat/2.0.0/dial` stream with the index(0
based) of the candidate that it attempted to dial and the appropriate
`ResponseStatus`. see [Requirements For
ResponseStatus](#requirements-for-responsestatus)

The initiator MUST check that the nonce received in the `DialAttempt` is the
same as the nonce the initiator sent in the `Candidate` for the candidate index
received in `DialResponse`. If the nonce is different, the initiator MUST
discard this response.

The peer MUST close the stream after sending the response. The initiator MUST
close the stream after receiving the response.


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

### Amplification Attack Prevention

When a client asks a server to dial an address that is not the client's observed
IP address, the server asks the client to send him some non trivial amount of
bytes as a cost to dial a different IP address. To make amplification attacks
unattractive, the number of bytes is decided such that it's sufficiently larger
than a new connection handshake cost.

On receiving a `DialRequest`, the server selects the first address it is capable
of dialing. If this selected address has a IP different from the client's
observed ip, the server sends a `DialDataRequest` message with `numBytes` set to
a sufficiently large value on the `/libp2p/autonat/2.0.0/dial-request` stream

Upon receiving a `DialDataRequest` message, the client decides whether to accept
or reject the cost of dial. If the client rejects the cost, the client resets
the stream and the `DialRequest` is considered aborted. If the client accepts
the cost, the client starts transferring `numBytes` bytes to the server. The
server on receiving `numBytes` bytes proceeds to dial the candidate address. 

## Implementation Suggestions

For any given address, implementations SHOULD do the following
- periodically recheck reachability status
- query multiple peers to determine reachability

The suggested heuristic for implementations is to consider an address reachable
if more than 3 peers report a successful dial and to consider an address
unreachable if more than 3 peers report unsuccessful dials. 

Implementations are free to use different heuristics than this one

Implementations SHOULD only verify reachability for private addresses as defined
in [RFC 1918](https://datatracker.ietf.org/doc/html/rfc1918) with peers that are
on the same subnet


## RPC Messages

All RPC messages sent over a stream are prefixed with the message length in
bytes, encoded as an unsigned variable length integer as defined by the
[multiformats unsigned-varint spec][uvarint-spec]. 

All RPC messages on stream `/libp2p/autonat/2.0.0/dial` are of type
`DialMessage`. A `DialRequest` message is sent as a `DialMessage` with the
`dialRequest` field set to `DialRequest` message. `DialResponse` and
`DialDataRequest` are handled similarly. On stream
`/libp2p/autonat/2.0.0/attempt`, there is a single message type `AttemptMessage`
where `DialAttempt` is handled similarly. 

```proto
syntax = "proto3";

message DialMessage {
  oneof msg {
    DialRequest dialRequest   = 1;
    DialResponse dialResponse = 2;
    DialDataRequest dialDataRequest = 3;
  }
}

message Candidate {
  bytes addr = 1;
  fixed64 nonce = 2;
}

message DialRequest {
  repeated Candidate candidates = 1;
}

message DialDataRequest {
  uint64 numBytes = 1;
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
  int32 addrIdx = 2;
}

message AttemptMessage {
  oneof msg {
    DialAttempt dialAttempt = 1;
  }
}

message DialAttempt {
    fixed64 nonce = 1;
}
```

[uvarint-spec]: https://github.com/multiformats/unsigned-varint

