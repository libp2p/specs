# WebRTC browser-to-browser

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r0, 2022-12-15  |

## Motivation

1. **Hole punching in the browser**: Enable two browsers or a browser and a
   server node to connect even though one or both are behind a NAT / firewall.

   TODO: Doucment use-case where A is a browser and B is a non-browser but behind firewall and/or NAT.

## Connection Establishment

### Browser to Browser

Scenario: Browser _A_ wants to connect to Browser node _B_ with the help of
server node _R_.

1. _B_ runs inside a browser and can thus not listen for incoming connections.
   _B_ connects to a public server node _R_ and uses the Circuit Relay v2
   protocol to make a reservation.

2. _B_ advertises its relayed address through some external mechanism.

3. _A_ discovers _B_'s relayed address. _A_ connects to _R_ and establishes a
   relayed connection to _B_ via the Circtui Relay v2 protocol.

4. _A_ and _B_ both create a `RTCPeerConnection` and generate an _offer_ and an
   _answer_ respectively. See `icegatheringstatechange` below on how these may
   already contain the addresses of the loca node.

5. _A_ and _B_ exchange the generated _offer_ and _answer_ through some protocol
   (e.g. an altered DCUtR) via the relayed connection.

   - One could alter DCUtR or identify-push.
   - We should support ICE trickle candidates.
   - We can design our own protocol catered for SDP offer and answer.
   - Contrary to what browser-to-server does, ideally we would exchange ufrag (username + password).

6. _A_ and _B_ set the exchanged _offer_ and _answer_ and thus initiate the
   connection establishment.

7. Messages on the established `RTCDataChannel` are framed using the message
   framing mechanism described in [Multiplexing](#multiplexing).

8. The remote is authenticated via an additional Noise handshake. See
   [Connection Security](#connection-security).

The above browser-to-browser WebRTC connection establishment replaces the
existing [libp2p WebRTC star](https://github.com/libp2p/js-libp2p-webrtc-star)
and [libp2p WebRTC direct](https://github.com/libp2p/js-libp2p-webrtc-direct)
protocols.

#### Open Questions

- Instead of using trickle ICE, we could as well wait for the candidate
  gathering. See
  https://github.com/pion/webrtc/blob/c1467e4871c78ee3f463b50d858d13dc6f2874a4/examples/insertable-streams/main.go#L141-L142
  as one example. In the browser, one can wait for the
  [`icegatheringstatechange`
  event](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/icegatheringstatechange_event).

## FAQ

- Can _Browser_ control the lifecycle of its local TLS certificate, i.e. can
  _Browser_ use the same TLS certificate for multiple WebRTC connections?

  Yes. For the lifetime of the page, one can generate a certificate once and
  reuse it across connections. See also
  https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/RTCPeerConnection#using_certificates

  TODO: Reference privacy considerations.
