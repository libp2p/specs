# WebRTC browser-to-browser

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r0, 2022-12-15  |

## Motivation

1. **Hole punching in the browser**: Enable two browsers or a browser and a server node to connect even though one or both are behind a NAT / firewall.

   TODO: Doucment use-case where A is a browser and B is a non-browser but behind firewall and/or NAT.

## Connection Establishment

### Browser to Browser

Scenario: Browser _A_ wants to connect to Browser node _B_ with the help of server node _R_.
Both _A_ and _B_ can not listen for incoming connections due to the restriction of the browser platform and being behind a NAT and/or firewall.

TODO: Define which node on a relayed connection is _A_ and which one is _B_, i.e. which one initiates (offer) and which one responds (answer).

1. _A_ and _B_ establish a relayed connection through some protocol, e.g. the Circuit Relay v2 protocol.
   Note that further steps depend on the relayed connection to be authenticated, i.e. that data send on the relayed connection can be trusted.

2. _A_ creates an `RTCPeerConnection`.
   See [#STUN] on what STUN servers to configure at creation time.
   _A_ creates an SDP offer via `RTCPeerConnection.createOffer()`.
   _A_ initiates the signaling protocol to _B_ via the relayed connection from (1), see [#Signaling protocol] and sends the offer to _B_.

3. _B_ creates an `RTCPeerConnection`.
   Again see [#STUN] on what STUN servers to configure at creation time.
   _B_ receives _A_'s offer send in (2) via the signaling protocol stream and provides the offer to its `RTCPeerConnection` via `RTCPeerConnection.setRemoteDescription`.
   _B_ then creates an answer via `RTCPeerConnection.createAnswer` and sends it to _A_ via the existing signaling protocol stream (see [#signaling protocol]).

4. _A_ receives _B_'s answer via the signaling protocol stream and sets it locally via `RTCPeerConnection.setRemoteDescription`.

5. TODO: Define ICE candidate exchange.

5. Messages on `RTCDataChannel`s on the established `RTCPeerConnection` are framed using the message framing mechanism described in [Multiplexing](#multiplexing).

The above browser-to-browser WebRTC connection establishment replaces the existing [libp2p WebRTC star](https://github.com/libp2p/js-libp2p-webrtc-star) and [libp2p WebRTC direct](https://github.com/libp2p/js-libp2p-webrtc-direct) protocols.

#### Open Questions

- Instead of using trickle ICE, we could as well wait for the candidate gathering.
  See https://github.com/pion/webrtc/blob/c1467e4871c78ee3f463b50d858d13dc6f2874a4/examples/insertable-streams/main.go#L141-L142 as one example.
  In the browser, one can wait for the [`icegatheringstatechange` event](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/icegatheringstatechange_event).

## STUN

TODO: Specify

## Signaling protocol

TODO: Extend

Protocol id `/webrtc-direct`

Messages are sent prefixed with the message length in bytes, encoded as an unsigned variable length integer as defined by the [multiformats unsigned-varint spec][uvarint-spec].

``` protobuf
// TODO: Support for offer, answer and ICE candidates
```

## FAQ

- Why is there no additional Noise handshake needed?

  This specification (browser-to-browser) requires _A_ and _B_ to exchange their SDP offer and answer over an authenticated channel.
  Offer and answer contain the TLS certificate fingerprint.
  The browser validates the TLS certificate fingerprint through the TLS handshake on the direct connection.

  In contrast, the browser-to-server specification allows exchange of the server's multiaddr, containing the server's TLS certificate fingerprint, over unauthenticated channels.
  In other words, the browser-to-server specification does not consider the TLS certificate fingerprint in the server's multiaddr to be trusted.
