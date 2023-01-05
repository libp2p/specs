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
server node _R_. Both _A_ and _B_ can not listen for incoming connections due to
the restriction of the browser platform and being behind a NAT and/or firewall.

1. _A_ and _B_ establish a relayed connection through some protocol, e.g. the
   Circuit Relay v2 protocol. Note that further steps depend on the relayed
   connection to be authenticated, i.e. that data send on the relayed connection
   can be trusted.

2. _A_ and _B_ both create a `RTCPeerConnection` and generate an _offer_ and an
   _answer_ respectively. See `icegatheringstatechange` below on how these may
   already contain the addresses of the loca node.

   _A_ and _B_ SHOULD NOT reuse certificates across `RTCPeerConnection`s.
   Reusing the certificate can be used to identify a node across connections by
   on-path observers given that WebRTC uses TLS 1.2.

3. _A_ and _B_ exchange the generated _offer_ and _answer_ through some protocol
   (e.g. an altered DCUtR) via the relayed connection.

   - One could alter DCUtR or identify-push.
   - We should support ICE trickle candidates.
   - We can design our own protocol catered for SDP offer and answer.
   - Contrary to what browser-to-server does, ideally we would exchange ufrag (username + password).

4. _A_ and _B_ set the exchanged _offer_ and _answer_ and thus initiate the
   connection establishment.

5. Messages on the established `RTCDataChannel` are framed using the message
   framing mechanism described in [Multiplexing](#multiplexing).

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

- Why is there no additional Noise handshake needed?

  This specification (browser-to-browser) requires _A_ and _B_ to exchange their
  SDP offer and answer over an authenticated channel. Offer and answer contain
  the TLS certificate fingerprint. The browser validates the TLS certificate
  fingerprint through the TLS handshake on the direct connection.

  In contrast, the browser-to-server specification allows exchange of the
  server's multiaddr, containing the server's TLS certificate fingerprint, over
  unauthenticated channels. In other words, the browser-to-server specification
  does not consider the TLS certificate fingerprint in the server's multiaddr to
  be trusted.
