# WebRTC

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active |                 |

Authors: [@mxinden]

Interest Group: [@marten-seemann]

<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-refresh-toc -->
**Table of Contents**

- [WebRTC](#webrtc)
    - [Motivation](#motivation)
    - [Requirements](#requirements)
    - [Addressing](#addressing)
    - [Connection Establishment](#connection-establishment)
        - [Browser to public Server](#browser-to-public-server)
            - [Open Questions](#open-questions)
        - [Browser to Browser](#browser-to-browser)
            - [Open Questions](#open-questions-1)
    - [Connection Security](#connection-security)
        - [Open Questions](#open-questions-2)
    - [Multiplexing](#multiplexing)
    - [General Open Questions](#general-open-questions)
    - [Previous, ongoing and related work](#previous-ongoing-and-related-work)
- [FAQ](#faq)

<!-- markdown-toc end -->


## Motivation

1. **No need for valid TLS certificates.** Enable browsers to connect to public
   server nodes without those server nodes providing a TLS certificate within
   the browsers trustchain. Note that we can not do this today with our
   Websocket transport.

2. **Hole punching in the browser**: Enable two browsers or a browser and a
   non-public server node to connect.

## Requirements

- Loading a remote nodes certificate into ones browser trust-store is not an
  option, i.e. doesn't scale.

- No dependency on central STUN and/or TURN servers.

## Addressing

WebRTC multiaddresses are composed of an IP and UDP address component, followed
by `/webrtc` and a multihash of the certificate that the node uses.

Examples:
- `/ip4/1.2.3.4/udp/1234/webrtc/certhash/<hash>/p2p/<peer-id>`
- `/ip6/fe80::1ff:fe23:4567:890a/udp/1234/webrtc/certhash/<hash>/p2p/<peer-id>`

## Connection Establishment

### Browser to public Server

Scenario: Browser _A_ wants to connect to server node _B_ where _B_ is publicly
reachable but _B_ does not have a TLS certificate trusted by _A_.

As a preparation browser _A_ [generates a
certificate](https://www.w3.org/TR/webrtc/#dom-rtcpeerconnection-generatecertificate)
and [gets the certificate's
fingerprint](https://www.w3.org/TR/webrtc/#dom-rtccertificate-getfingerprints).

1. Browser _A_ discovers server node _B_'s multiaddr, containing _B_'s IP, UDP
  port, TLS certificate fingerprint and libp2p peer ID (e.g.
  `/ip6/2001:db8::/udp/1234/webrtc/certhash/<hash>/p2p/<peer-id>`),
  through some external mechanism.

2. _A_ instantiates a `RTCPeerConnection`, passing its local certificate as a
   parameter. See
   [`RTCPeerConnection()`](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/RTCPeerConnection).

3. _A_ constructs _B_'s SDP offer locally based on _B_'s multiaddr and sets it
   via
   [`RTCPeerConnection.setRemoteDescription()`](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/setRemoteDescription).

4. _A_ establishes the connection to _B_. _B_ learns of _A_ TLS fingerprint
   through A's STUN message USERNAME attribute. See Open Questions below for
   potential better solutions.

5. See [Connection Security](#connection-security).

6. See [Multiplexing](#multiplexing).

#### Open Questions

- Can _Browser_ generate a _valid_ SDP packet for the remote node based on the
  remote's Multiaddr, where that Multiaddr contains the IP, UDP port and TLS
  certificate fingerprint (e.g.
  `/ip6/2001:db8::/udp/1234/webrtc/certhash/<hash>/p2p/<peer-id>`)? _Valid_ in
  the sense that this generated SDP packet can then be used to establish a
  WebRTC connection to the remote.

  Yes.

- Do the major (Go / Rust / ...) WebRTC implementations allow us to accept a
  WebRTC connection from a remote node without previously receiving an SDP
  packet from such host?

- How does the server learn the TLS certificate fingerprint of the browser? Is
  embedding A's TLS certificate fingerprint in A's STUN message USERNAME
  attribute the best option?

### Browser to Browser

Scenario: Browser _A_ wants to connect to Browser node _B_ with the help of
server node _R_.

- Replace STUN with libp2p's identify and AutoNAT
  - https://github.com/libp2p/specs/tree/master/identify
  - https://github.com/libp2p/specs/blob/master/autonat/README.md
- Replace TURN with libp2p's Circuit Relay v2
  - https://github.com/libp2p/specs/blob/master/relay/circuit-v2.md
- Use DCUtR over Circuit Relay v2 to transmit SDP information
  1. Transform ICE candidates in SDP to multiaddresses.
  2. Transmit the set of multiaddresses to the remote via DCUtR.
  3. Transform the set of multiaddresses back to the remotes SDP.
  4. https://github.com/libp2p/specs/blob/master/relay/DCUtR.md

#### Open Questions

- Can _Browser_ know upfront its UDP port which it is listening for incoming
  connections on? Does the browser reuse the UDP port across many WebRTC
  connections? If that is the case one could connect to any public node, with
  the remote telling the local node what port it is perceived on.

- Can _Browser_ control the lifecycle of its local TLS certificate, i.e. can
  _Browser_ use the same TLS certificate for multiple WebRTC connections?

  Yes. For the lifetime of the page, one can generate a certificate once and
  reuse it across connections. See also
  https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/RTCPeerConnection#using_certificates

- Can two _Browsers_ exchange their SDP packets via a third server node using
  Circuit Relay v2 and DCUtR? Instead of exchanging the original SDP packets,
  could they exchange their multiaddr and construct the remote's SDP packet
  based on it?

## Connection Security

While WebRTC offers confidentiality and integrity via TLS, one still needs to
authenticate the remote peer by its libp2p identity.

After [Connection Establishment](#connection-establishment):

1. _A_ initiates some authentication handshake _X_ to _B_ on a datachannel,
   where _X_ allows _A_ and _B_ to authenticate each other's peer IDs. _X_ could
   for example be Noise. See WebTransport specification as an example
   https://github.com/libp2p/specs/pull/404. Still to be specified here for
   WebRTC.

### Open Questions

- Can a _Browser_ access the fingerprint of its TLS certificate?

  Chrome allows you to access the fingerprint of any locally-created certificate
  directly via `RTCCertificate#getFingerprints`. Firefox does not allow you to
  do so. Browser compatibility can be found
  [here](https://developer.mozilla.org/en-US/docs/Web/API/RTCCertificate). In
  practice, this is not an issue since the fingerprint is embedded in the local
  SDP string.

- Is the above proposed #protocol secure?

- On the server side, can one derive the TLS certificate in a deterministic way
  based on a node's libp2p private key? Benefit would be that a node only needs
  to persist the libp2p private key and not the TLS key material while still
  maintaining a fixed TLS certificate fingerprint.

## Multiplexing

After [Connection Security](#connection-security):

1. On success of the authentication handshake _X_, the used datachannel is
   closed and the plain WebRTC connection is used with its multiplexing
   capabilities via datachannels.

### Open Questions

- Can we use WebRTC’s data channels in _Browser_ to multiplex a single
  connection, or do we need to run an additional multiplexer (e.g. yamux) on top
  of a WebRTC connection and WebRTC datachannel? In other words, does WebRTC
  provide all functionality of a libp2p muxer like Yamux (e.g. flow control)?

  Yes, with WebRTC's datachannels running on top of SCTP, there is no need for
  additional multiplexing.

## General Open Questions

_Where _Browser_ is replaced with the major desktop browsers of today (Chrome,
Safari, Edge, Firefox)._

- Should libp2p's WebRTC stack limit itself to using UDP only, or support WebRTC
  on top of both UDP and TCP?

## Previous, ongoing and related work

- Proof of concept for the server side in rust-libp2p:
  https://github.com/libp2p/rust-libp2p/pull/2622

- Proof of concept for the server side (native) and the client side (Rust in
  WASM): https://github.com/wngr/libp2p-webrtc

- WebRTC using STUN and TURN: https://github.com/libp2p/js-libp2p-webrtc-star

# FAQ

- _Why exchange the TLS certificate fingerprint in the multiaddr? Why not
  base it on the libp2p public key?_

  Browsers do not allow loading a custom certificate. One can only generate a
  certificate via
  [rtcpeerconnection-generatecertificate](https://www.w3.org/TR/webrtc/#dom-rtcpeerconnection-generatecertificate).

- _Why not embed the peer ID in the TLS certificate, thus rendering the
  additional "peer certificate" exchange obsolete?_

  Browsers do not allow editing the properties of the TLS certificate.

- _How about distributing the multiaddr in a signed peer record, thus rendering
  the additional "peer certificate" exchange obsolete?_

  Signed peer records are not yet rolled out across the many libp2p protocols.
  Making the libp2p WebRTC protocol dependent on the former is not deemed worth
  it at this point in time. Later versions of the libp2p WebRTC protocol might
  adopt this optimization.

  Note, one can role out a new version of the libp2p WebRTC protocol through a
  new multiaddr protocol, e.g. `/webrtc-2`.

- _Why do an authentication handshake on top of an established WebRTC
  connection? Why not only exchange signatures of ones TLS fingerprint signed
  with ones libp2p private key?_

  This is prone to replay attacks.
