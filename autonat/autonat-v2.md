# AutonatV2: spec

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r2, 2023-04-15  |

Authors: [@sukunrt]

Interest Group: [@marten-seemann], [@marcopolo], [@mxinden]

[@sukunrt]: https://github.com/sukunrt
[@marten-seemann]: https://github.com/marten-seemann
[@mxinden]: https://github.com/mxinden
[@marcopolo]: https://github.com/marcopolo

## Overview

A priori, a node cannot know if it is behind a NAT / firewall or if it is
publicly reachable. Moreover, the node may be publicly reachable on some of its
addresses and not on others. Knowing the reachability status of its addresses
is crucial for proper network behavior: the node can avoid advertising
unreachable addresses, reducing unnecessary connection attempts from other
peers. If the node has no publicly accessible addresses, it may proactively
improve its connectivity by locating a relay server, enabling other peers to
connect through a relayed connection.

In `autonat v2` client sends a request with a priority ordered list of addresses
and a nonce. On receiving this request the server dials the first address in the
list that it is capable of dialing and provides the nonce. Upon completion of
the dial, the server responds to the client with the response containing the
dial outcome.

As the server dials _exactly_ one address from the list, `autonat v2` allows
nodes to determine reachability for individual addresses. Using `autonat v2`
nodes can build an address pipeline where they can test individual addresses
discovered by different sources like identify, upnp mappings, circuit addresses
etc for reachability. Having a priority ordered list of addresses provides the
ability to verify low priority addresses. Implementations can generate low
priority address guesses and add them to requests for high priority addresses as
a nice to have. This is especially helpful when introducing a new transport.
Initially, such a transport will not be widely supported in the network.
Requests for verifying such addresses can be reused to get information about
other addresses

The client can verify the server did successfully dial an address of the same
transport as it reported in the response by checking the local address of the
connection on which the nonce was received on.

Compared to `autonat v1` there are three major differences

1. `autonat v1` allowed testing reachability for the node. `autonat v2` allows
   testing reachability for an individual address.
2. `autonat v2` provides a mechanism for nodes to verify whether the peer
   actually successfully dialled an address.
3. `autonat v2` provides a mechanism for nodes to dial an IP address different
   from the requesting node's observed IP address without risking amplification
   attacks. `autonat v1` disallowed such dials to prevent amplification attacks.

## AutoNAT V2 Protocol

![Autonat V2 Interaction](autonat-v2.svg)

A client node wishing to determine reachability of its addresses sends a
`DialRequest` message to a server on a stream with protocol ID
`/libp2p/autonat/2/dial-request`. Each `DialRequest` is sent on a new stream.

This `DialRequest` message has a list of addresses and a fixed64 `nonce`. The
list is ordered in descending order of priority for verification. AutoNAT V2 is
primarily for testing reachability on Public Internet. Client SHOULD NOT send any
private address as defined in [RFC
1918](https://datatracker.ietf.org/doc/html/rfc1918#section-3) in the list. The Server SHOULD NOT dial any private address.

Upon receiving this request, the server selects an address from the list to
dial. The server SHOULD use the first address it is willing to dial. The server
MUST NOT dial any address other than this one. If this selected address has an
IP address different from the requesting node's observed IP address, server
initiates the Amplification attack prevention mechanism (see [Amplification
Attack Prevention](#amplification-attack-prevention) ). On completion, the
server proceeds to the next step. If the selected address has the same IP
address as the client's observed IP address, server proceeds to the next step
skipping Amplification Attack Prevention steps.

The server dials the selected address, opens a stream with Protocol ID
`/libp2p/autonat/2/dial-back` and sends a `DialBack` message with the nonce
received in the request. The client on receiving this message replies with
a `DialBackResponse` message with the status set to `OK`. The client MUST
close this stream after sending the response. The dial back response provides
the server assurance that the message was delivered so that it can close the
connection.

Upon completion of the dial back, the server sends a `DialResponse` message to
the client node on the `/libp2p/autonat/2/dial-request` stream. The response
contains `addrIdx`, the index of the address the server selected to dial and
`DialStatus`, a dial status indicating the outcome of the dial back. The
`DialStatus` for an address is set according to [Requirements for
DialStatus](#requirements-for-dialstatus). The response also contains an
appropriate `ResponseStatus` set according to [Requirements For
ResponseStatus](#requirements-for-responsestatus).

The client MUST check that the nonce received in the `DialBack` is the same as
the nonce it sent in the `DialRequest`. If the nonce is different, it MUST
discard this response.

The server MUST close the stream after sending the response. The client MUST
close the stream after receiving the response.

### Requirements for DialStatus

On receiving a `DialRequest`, the server first selects an address that it will
dial.

If server chooses to not dial any of the requested addresses, `ResponseStatus`
is set to `E_DIAL_REFUSED`. The fields `addrIdx` and `DialStatus` are
meaningless in this case. See [Requirements For
ResponseStatus](#requirements-for-responsestatus).

If the server selects an address for dialing, `addrIdx` is set to the
index(zero-based) of the address on the list and the `DialStatus` is set
according to the following consideration:

If the server was unable to connect to the client on the selected address,
`DialStatus` is set to `E_DIAL_ERROR`, indicating the selected address is not
publicly reachable.

If the server was able to connect to the client on the selected address, but an
error occured while sending an nonce on the `/libp2p/autonat/2/dial-back`
stream, `DialStatus` is set to `E_DIAL_BACK_ERROR`. This might happen in case of
resource limited situations on client or server, or when either the client or
the server is misconfigured.

If the server was able to connect to the client and successfully send a nonce on
the `/libp2p/autonat/2/dial-back` stream, `DialStatus` is set to `OK`.

### Requirements for ResponseStatus

The `ResponseStatus` sent by the server in the `DialResponse` message MUST be
set according to the following requirements

`E_REQUEST_REJECTED`: The server didn't serve the request because of rate
limiting, resource limit reached or blacklisting.

`E_DIAL_REFUSED`: The server didn't dial back any address because it was
incapable of dialing or unwilling to dial any of the requested addresses.

`E_INTERNAL_ERROR`: Error not classified within the above error codes occured on
server preventing it from completing the request.

`OK`: The server completed the request successfully. A request is considered
a success when the server selects an address to dial and dials it, successfully or unsuccessfully.

Implementations MUST discard responses with status codes they do not understand.

### Amplification Attack Prevention

![Interaction](autonat-v2-amplification-attack-prevention.svg)

When a client asks a server to dial an address that is not the client's observed
IP address, the server asks the client to send some non trivial amount of bytes
as a cost to dial a different IP address. To make amplification attacks
unattractive, servers SHOULD ask for 30k to 100k bytes. Since most handshakes
cost less than 10k bytes in bandwidth, 30kB is sufficient to make attacks
unattractive.

On receiving a `DialRequest`, the server selects the first address it is capable
of dialing. If this selected address has a IP different from the client's
observed IP, the server sends a `DialDataRequest` message with the selected
address's index(zero-based) and `numBytes` set to a sufficiently large value on
the `/libp2p/autonat/2/dial-request` stream

Upon receiving a `DialDataRequest` message, the client decides whether to accept
or reject the cost of dial. If the client rejects the cost, the client resets
the stream and the `DialRequest` is considered aborted. If the client accepts
the cost, the client starts transferring `numBytes` bytes to the server. The
client transfers these bytes wrapped in `DialDataResponse` protobufs where the
`data` field in each individual protobuf is limited to 4096 bytes in length.
This allows implementations to use a small buffer for reading and sending the
data. Only the size of the `data` field of `DialDataResponse` protobufs is
counted towards the bytes transferred. Once the server has received at least
numBytes bytes, it proceeds to dial the selected address. Servers SHOULD allow
the last `DialDataResponse` message received from the client to be larger than
the minimum required amount. This allows clients to serialize their
`DialDataResponse` message once and reuse it for all Requests.

If an attacker asks a server to dial a victim node, the only benefit the
attacker gets is forcing the server and the victim to do a cryptographic
handshake which costs some bandwidth and compute. The attacker by itself can do
a lot of handshakes with the victim without spending any compute by using the
same key repeatedly. The only benefit of going via the server to do this attack
is not spending bandwidth required for a handshake. So the prevention mechanism
only focuses on bandwidth costs. There is a minor benefit of bypassing IP
blocklists, but that's made unattractive by the fact that servers may ask 5x
more data than the bandwidth cost of a handshake.

#### Related Work

UDP based protocol's, like QUIC and DNS-over-UDP, need to prevent similar amplification attacks caused by IP spoofing. To verify that received packets don't have a spoofed IP, the server sends a random token to the client, which echoes the token back. For example, in QUIC, an attacker can use the victim's IP in the initial packet to make it process a much larger `ServerHello` packet. QUIC servers use a Retry Packet containing a token to validate that the client can receive packets at the address it claims. See [QUIC Address Validation](https://datatracker.ietf.org/doc/html/rfc9000#name-address-validation) for details of the scheme. 

## Implementation Suggestions

For any given address, client implementations SHOULD do the following

- Periodically recheck reachability status.
- Query multiple servers to determine reachability.

The suggested heuristic for implementations is to consider an address reachable
if more than 3 servers report a successful dial and to consider an address
unreachable if more than 3 servers report unsuccessful dials. Implementations
are free to use different heuristics than this one

Servers SHOULD NOT reuse their listening port when making a dial back. In case
the client has reused their listen port when dialing out to the server, not
reusing the listen port for attempts prevents accidental hole punches. Clients
SHOULD only rely on the nonce and not on the peerID for verifying the dial back
as the server is free to use a separate peerID for the dial backs.

Servers SHOULD determine whether they have IPv6 and IPv4 connectivity. IPv4 only servers SHOULD refuse requests for dialing IPv6 addresses and IPv6 only
servers SHOULD refuse requests for dialing IPv4 addresses.

## RPC Messages

All RPC messages sent over a stream are prefixed with the message length in
bytes, encoded as an unsigned variable length integer as defined by the
[multiformats unsigned-varint spec][uvarint-spec].

All RPC messages on stream `/libp2p/autonat/2/dial-request` are of type
`Message`. A `DialRequest` message is sent as a `Message` with the `msg` field
set to `DialRequest`. `DialResponse` and `DialDataRequest` are handled
similarly.

On stream `/libp2p/autonat/2/dial-back`, a `DialAttempt` message is sent
directly

```proto3

message Message {
    oneof msg {
        DialRequest dialRequest   = 1;
        DialResponse dialResponse = 2;
        DialDataRequest dialDataRequest = 3;
        DialDataResponse dialDataResponse = 4;
    }
}


message DialRequest {
    repeated bytes addrs = 1;
    fixed64 nonce = 2;
}


message DialDataRequest {
    uint32 addrIdx = 1;
    uint64 numBytes = 2;
}


enum DialStatus {
    UNUSED            = 0;
    E_DIAL_ERROR      = 100;
    E_DIAL_BACK_ERROR = 101;
    OK                = 200;
}


message DialResponse {
    enum ResponseStatus {
        E_INTERNAL_ERROR   = 0;
        E_REQUEST_REJECTED = 100;
        E_DIAL_REFUSED     = 101;
        OK  = 200;
    }

    ResponseStatus status = 1;
    uint32 addrIdx        = 2;
    DialStatus dialStatus = 3;
}


message DialDataResponse {
    bytes data = 1;
}


message DialBack {
    fixed64 nonce = 1;
}

message DialBackResponse {
    enum DialBackStatus {
        OK = 0;
    }

    DialBackStatus status = 1;
}
```

[uvarint-spec]: https://github.com/multiformats/unsigned-varint
