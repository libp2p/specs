# WebRTC

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r0, 2023-03-03  |

Authors: [@mxinden]

## Motivation

libp2p transport protocol enabling two private nodes (e.g. two browsers) to establish a direct connection.

Browser _A_ wants to connect to Browser node _B_ with the help of server node _R_.
Both _A_ and _B_ cannot listen for incoming connections due to running in a constrained environment (i.e. a browser) with its only transport capability being the W3C WebRTC `RTCPeerConnection` API and being behind a NAT and/or firewall.
Note that _A_ and/or _B_ may as well be non-browser nodes behind NATs and/or firewalls.
However, for two non-browser nodes using TCP or QUIC hole punching with [DCUtR] will be the more efficient way to establish a direct connection.

On a historical note, this specification replaces the existing [libp2p WebRTC star](https://github.com/libp2p/js-libp2p-webrtc-star) and [libp2p WebRTC direct](https://github.com/libp2p/js-libp2p-webrtc-direct) protocols.

## Connection Establishment

1. _B_ advertises support for the WebRTC browser-to-browser protocol by appending `/webrtc` to its relayed multiaddr, meaning it takes the form of `<relayed-multiaddr>/webrtc/p2p/<b-peer-id>`.

2. Upon discovery of _B_'s multiaddress, _A_ learns that _B_ supports the WebRTC transport and knows how to establish a relayed connection to _B_ to run the `/webrtc-signaling` protocol on top.

3. _A_ establish a relayed connection to _B_.
   Note that further steps depend on the relayed connection to be authenticated, i.e. that data sent on the relayed connection can be trusted.

4. _A_ (outbound side of relayed connection) creates an `RTCPeerConnection` provided by a W3C compliant WebRTC implementation (e.g. a browser).
   See [STUN](#stun) section on what STUN servers to configure at creation time.
   _A_ creates an SDP offer via `RTCPeerConnection.createOffer()`.
   _A_ initiates the signaling protocol to _B_ via the relayed connection from (1), see [Signaling Protocol](#signaling-protocol) and sends the offer to _B_.
   Note that _A_ being the initiator of the stream is merely a convention preventing both nodes to simultaneously initiate a new connection thus potentially resulting in two WebRTC connections.
   _A_ MUST as well be able to handle an incoming signaling protocol stream to support the case where _B_ initiates the signaling process.

5. On reception of the incoming stream, _B_ (inbound side of relayed connection) creates an `RTCPeerConnection`.
   Again see [STUN](#stun) section on what STUN servers to configure at creation time.
   _B_ receives _A_'s offer sent in (2) via the signaling protocol stream and provides the offer to its `RTCPeerConnection` via `RTCPeerConnection.setRemoteDescription`.
   _B_ then creates an answer via `RTCPeerConnection.createAnswer` and sends it to _A_ via the existing signaling protocol stream (see [Signaling Protocol](#signaling-protocol)).

6. _A_ receives _B_'s answer via the signaling protocol stream and sets it locally via `RTCPeerConnection.setRemoteDescription`.

7. _A_ and _B_ send their local ICE candidates via the existing signaling protocol stream to enable trickle ICE.
   Both nodes continuously read from the stream, adding incoming remote candidates via `RTCPeerConnection.addIceCandidate()`.

8. On successful establishment of the direct connection, _B_ and _A_ close the signaling protocol stream.
   On failure _B_ and _A_ reset the signaling protocol stream.

   Behavior for transferring data on a relayed connection, in the case where the direct connection failed, is out of scope for this specification and dependent on the application.

9. Messages on `RTCDataChannel`s on the established `RTCPeerConnection` are framed using the message framing mechanism described in [multiplexing].

## STUN

A node needs to discover its public IP and port, which is forwarded to the remote node in order to connect to the local node.
On non-browser libp2p nodes doing a hole punch with TCP or QUIC, the libp2p node discovers its public address via the [identify] protocol.
One cannot use the [identify] protocol on browser nodes to discover ones public IP and port given that the browser uses a new port for each connection.
For example say that the local browser node establishes a WebRTC connection C1 via browser-to-server to a server node and runs the [identify] protocol.
The returned observed public port P1 will most likely (depending on the NAT) be a different port than the port observed on another connection C2.
The only browser supported mechanism to discover ones public IP and port for a given WebRTC connection is the non-libp2p protocol STUN.
This is why this specification depends on STUN, and thus the availability of one or more STUN servers for _A_ and _B_ to discovery their public addresses.

There are various publicly available STUN servers.
As an alternative one may operate dedicated STUN servers for a given libp2p network.
Further specification of the usage of STUN is out of scope for this specifitcation.

As an aside, note that _A_ and _B_ do not need to use the same STUN server in order to establish a direct WebRTC connection.

## Signaling Protocol

The protocol id is `/webrtc-signaling`.
Messages are sent prefixed with the message length in bytes, encoded as an unsigned variable length integer as defined by the [multiformats unsigned-varint spec][uvarint-spec].

``` protobuf
syntax = "proto3";

message Message {
    // Specifies type in `data` field.
    enum Type {
        // String of `RTCSessionDescription.sdp`
        SDP_OFFER = 0;
        // String of `RTCSessionDescription.sdp`
        SDP_ANSWER = 1;
        // String of `RTCIceCandidate.toJSON()`
        ICE_CANDIDATE = 2;
    }

    optional Type type = 1;
    optional string data = 2;
}
```

## FAQ

- Why is there no additional Noise handshake needed?

  This specification (browser-to-browser) requires _A_ and _B_ to exchange their SDP offer and answer over an authenticated channel.
  Offer and answer contain the TLS certificate fingerprint.
  The browser validates the TLS certificate fingerprint through the DTLS handshake during the WebRTC connection establishment.

  In contrast, the browser-to-server specification allows exchange of the server's multiaddr, containing the server's TLS certificate fingerprint, over unauthenticated channels.
  In other words, the browser-to-server specification does not consider the TLS certificate fingerprint in the server's multiaddr to be trusted.

- Why use a custom signaling protocol? Why not use [DCUtR]?

  DCUtR offers time synchronization through a two-step protocol (first `Connect`, then `Sync`).
  This is not needed for WebRTC.

  DCUtR does not provide a mechanism to trickle local address candidates to the remote as they are discovered.
  Trickling candidates just-in-time allows for faster WebRTC connection establishment.

- Why does _A_ and not _B_ initiate the signaling protocol?

  In [DCUtR] _B_ (inbound side of the relayed connection) initiates the [DCUtR] protocol by opening the [DCUtR] protocol stream.
  The reason is that in case _A_ is publicly reachable, _B_ might be able to use connection reversal to connect to _A_ directly.
  This reason does not apply to the WebRTC browser-to-browser protocol.
  Given that _A_ and _B_ at this point already have a relayed connection established, they might as well use it to exchange SDP, instead of using connection reversal and WebRTC browser-to-server.
  Thus, for the WebRTC browser-to-browser protocol, _A_ initiates the signaling protocol by opening the signaling protocol stream.

[DCUtR]: ./../relay/DCUtR.md
[identify]: ./../identify/README.md
[multiplexing]: ./README.md#multiplexing
[uvarint-spec]: https://github.com/multiformats/unsigned-varint
