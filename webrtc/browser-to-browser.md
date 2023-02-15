# WebRTC browser-to-browser

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r0, 2022-12-15  |

## Motivation

**Hole punching in the browser** - Enable two browsers or a browser and a non-browser node to connect even though one or both are behind a NAT / firewall.

On a historical note, this specification replaces the existing [libp2p WebRTC star](https://github.com/libp2p/js-libp2p-webrtc-star) and [libp2p WebRTC direct](https://github.com/libp2p/js-libp2p-webrtc-direct) protocols.

## Connection Establishment

Scenario: Browser _A_ wants to connect to Browser node _B_ with the help of server node _R_.
Both _A_ and _B_ can not listen for incoming connections due to the restriction of the browser platform and being behind a NAT and/or firewall.
Note that _A_ and/or _B_ may as well be non-browser nodes behind NATs and/or firewalls.
However, for two non-browser nodes using TCP or QUIC hole punching with [DCUtR] will be the more efficient way to establish a direct connection.


1. _A_ and _B_ establish a relayed connection through some protocol, e.g. the Circuit Relay v2 protocol.
   The relayed connection is established from _A_ to _B_ (see same role distribution in [DCUtR] protocol).
   Note that further steps depend on the relayed connection to be authenticated, i.e. that data sent on the relayed connection can be trusted.

2. _B_ (inbound side of relayed connection) creates an `RTCPeerConnection`.
   See [STUN](#stun) section on what STUN servers to configure at creation time.
   _B_ creates an SDP offer via `RTCPeerConnection.createOffer()`.
   _B_ initiates the signaling protocol to _A_ via the relayed connection from (1), see [Signaling Protocol](#signaling-protocol) and sends the offer to _A_.

3. _A_ (outbound side of relayed connection) creates an `RTCPeerConnection`.
   Again see [STUN](#stun) section on what STUN servers to configure at creation time.
   _A_ receives _B_'s offer sent in (2) via the signaling protocol stream and provides the offer to its `RTCPeerConnection` via `RTCPeerConnection.setRemoteDescription`.
   _A_ then creates an answer via `RTCPeerConnection.createAnswer` and sends it to _B_ via the existing signaling protocol stream (see [Signaling Protocol](#signaling-protocol)).

4. _B_ receives _A_'s answer via the signaling protocol stream and sets it locally via `RTCPeerConnection.setRemoteDescription`.

5. _B_ and _A_ send their local ICE candidates via the existing signaling protocol stream.
   Both nodes continuously read from the stream, adding incoming remote candidates via `RTCPeerConnection.addIceCandidate()`.

6. On successful establishment of the direct connection, _A_ and _B_ close the signaling protocol stream.
   On failure _A_ and _B_ reset the signaling protocol stream.

   Behavior for transferring data on a relayed connection, in the case where the direct connection failed, is out of scope for this specification and dependent on the application.

7. Messages on `RTCDataChannel`s on the established `RTCPeerConnection` are framed using the message framing mechanism described in [multiplexing].

## STUN

A node needs to discover its public IP and port, which is forwarded to the remote node in order to connect to the local node.
On non-browser libp2p nodes doing a hole punch with TCP or QUIC, the libp2p node discovers its public address via the [identify] protocol.
One can not use the [identify] protocol on browser nodes to discover ones public IP and port given that the browser uses a new port for each connection.
For example say that the local browser node establishes a WebRTC connection C1 via browser-to-server to a server node and runs the [identify] protocol.
The returned observed public port P1 will most likely (depending on the NAT) be a different port than the port observed on another connection C2.
The only browser supported mechanism to discover ones public IP and port for a given connection is the non-libp2p protocol STUN.
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

## Open Questions

- Do we need a mechanism for browsers to advertise support for WebRTC browser-to-browser?

  Say that browser B supports WebRTC browser-to-browser.
  B listens via a relay and advertises its relayed address.
  A discovers B's relayed address.
  At this point A does not know whether B is a browser and thus supports WebRTC browser-to-browser, or whether B is e.g. a laptop potentially supporting TCP and QUIC hole punching via DCUtR but not WebRTC browser-to-browser.
  In the latter case, A can not establish a direct connection to B.

  Potential solution would be for B to advertise some protocol after the `/p2p-circuit` within its Multiaddr, e.g. `/ip6/<RELAY_IP>/udp/4001/p2p/<RELAY_PEER_ID>/p2p-circuit/webrtc-direct/p2p/<B_PEER_ID>`.
  As an alternative, A can discover B's support via the identify protocol on the relayed connection or by optimistically opening a stream using the signaling protocol.
  Both of the latter options imply long latency (direct connection + relayed connection + stream establishment / identify exchange) on success and on failure happen at the expense of a wasted relayed connection.

## FAQ

- Why is there no additional Noise handshake needed?

  This specification (browser-to-browser) requires _A_ and _B_ to exchange their SDP offer and answer over an authenticated channel.
  Offer and answer contain the TLS certificate fingerprint.
  The browser validates the TLS certificate fingerprint through the TLS handshake on the direct connection.

  In contrast, the browser-to-server specification allows exchange of the server's multiaddr, containing the server's TLS certificate fingerprint, over unauthenticated channels.
  In other words, the browser-to-server specification does not consider the TLS certificate fingerprint in the server's multiaddr to be trusted.

- Why use a custom signaling protocol? Why not use [DCUtR]?

  DCUtR offers time synchronization through a two-step protocol (first `Connect`, then `Sync`).
  This is not needed for WebRTC.

  DCUtR does not provide a mechanism to trickle local address candidates to the remote as they are discovered.
  Trickling candidates just-in-time allows for faster WebRTC connection establishment.

[DCUtR]: ./../relay/DCUtR.md
[identify]: ./../identify/README.md
[multiplexing]: ./README.md#multiplexing
[uvarint-spec]: https://github.com/multiformats/unsigned-varint
