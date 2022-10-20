# WebRTC

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r0, 2022-10-14  |

Authors: [@mxinden]

Interest Group: [@marten-seemann]

[@marten-seemann]: https://github.com/marten-seemann
[@mxinden]: https://github.com/mxinden/

<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-refresh-toc -->
**Table of Contents**

- [WebRTC](#webrtc)
    - [Motivation](#motivation)
    - [Addressing](#addressing)
    - [Connection Establishment](#connection-establishment)
        - [Browser to public Server](#browser-to-public-server)
    - [Multiplexing](#multiplexing)
        - [Ordering](#ordering)
        - [Head-of-line blocking](#head-of-line-blocking)
        - [`RTCDataChannel` negotiation](#rtcdatachannel-negotiation)
        - [`RTCDataChannel` label](#rtcdatachannel-label)
    - [Connection Security](#connection-security)
    - [Previous, ongoing and related work](#previous-ongoing-and-related-work)
- [FAQ](#faq)

<!-- markdown-toc end -->

## Motivation

1. **No need for trusted TLS certificates.** Enable browsers to connect to
   public server nodes without those server nodes providing a TLS certificate
   within the browsers trustchain. Note that we can not do this today with our
   Websocket transport as the browser requires the remote to have a trusted TLS
   certificate. Nor can we establish a plain TCP or QUIC connection from within
   a browser.

## Addressing

WebRTC multiaddresses are composed of an IP and UDP address component, followed
by `/webrtc` and a multihash of the certificate that the node uses.

Examples:
- `/ip4/1.2.3.4/udp/1234/webrtc/certhash/<hash>/p2p/<peer-id>`
- `/ip6/fe80::1ff:fe23:4567:890a/udp/1234/webrtc/certhash/<hash>/p2p/<peer-id>`

The TLS certificate fingerprint in `/certhash` is a
[multibase](https://github.com/multiformats/multibase) encoded
[multihash](https://github.com/multiformats/multihash).

For compatibility implementations MUST support hash algorithm
[`sha-256`](https://github.com/multiformats/multihash) and base encoding
[`base64url`](https://github.com/multiformats/multibase). Implementations MAY
support other hash algorithms and base encodings, but they may not be able to
connect to all other nodes.

## Connection Establishment

### Browser to public Server

Scenario: Browser _A_ wants to connect to server node _B_ where _B_ is publicly
reachable but _B_ does not have a TLS certificate trusted by _A_.

1. Server node _B_ generates a TLS certificate, listens on a UDP port and
   advertises the corresponding multiaddress (see [#addressing]) through some
   external mechanism.

   Given that _B_ is publicly reachable, _B_ acts as a [ICE
   Lite](https://www.rfc-editor.org/rfc/rfc5245) agent. It listens on a UDP port
   for incoming STUN and SCTP packets and multiplexes based on source IP and
   source port.

2. Browser _A_ discovers server node _B_'s multiaddr, containing _B_'s IP, UDP
  port, TLS certificate fingerprint and libp2p peer ID (e.g.
  `/ip6/2001:db8::/udp/1234/webrtc/certhash/<hash>/p2p/<peer-id>`),
  through some external mechanism.

3. _A_ instantiates a `RTCPeerConnection`. See
   [`RTCPeerConnection()`](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/RTCPeerConnection).

   _A_ (i.e. the browser) SHOULD NOT reuse the same certificate across
   `RTCPeerConnection`s. Reusing the certificate can be used to identify _A_
   across connections by on-path observers given that WebRTC uses TLS 1.2.

4. _A_ constructs _B_'s SDP answer locally based on _B_'s multiaddr. _A_
   generates a random string and sets that string as the username (_ufrag_ or
   _username fragment_) and password on the SDP of the remote's answer. Finally _A_
   sets the remote answer via
   [`RTCPeerConnection.setRemoteDescription()`](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/setRemoteDescription).

5. _A_ creates a local offer via
   [`RTCPeerConnection.createOffer()`](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/createOffer).
   _A_ sets the same username and password on the local offer as done in (4) on
   the remote answer. Finally _A_ sets the modified offer via
   [`RTCPeerConnection.setLocalDescription()`](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/setLocalDescription).

   Note that this process, oftentimes referred to as "SDP munging" is disallowed
   by the specification, but not enforced across the major browsers (Safari,
   Firefox, Chrome) due to use-cases in the wild. See also
   https://bugs.chromium.org/p/chromium/issues/detail?id=823036

6. Once _A_ sets the SDP offer and answer, it will start sending STUN requests
   to _B_. _B_ reads the _ufrag_ from the incoming STUN request's _username_
   field. _B_ then infers _A_'s SDP offer using the IP, port, and _ufrag_ of the
   request as follows:

   1. _B_ sets the the `ice-ufrag` and `ice-pwd` equal to the value read from
      the `username` field.

   2. _B_ sets an arbitrary sha-256 digest as the remote fingerprint as it does
      not verify fingerprints at this point.

   3. _B_ sets the connection field (`c`) to the IP and port of the incoming
      request `c=IN <ip> <port>`.

   _B_ sets this offer as the remote description. _B_ generates an answer and
   sets it as the local description.

   The _ufrag_ in combination with the IP and port of _A_ can be used by _B_
   to identify the connection, i.e. demultiplex incoming UDP datagrams per
   incoming connection.

   Note that this step requires _B_ to allocate memory for each incoming STUN
   message from _A_. This could be leveraged for a DOS attack where _A_ is
   sending many STUN messages with different ufrags using different UDP source
   ports, forcing _B_ to allocate a new peer connection for each. _B_ SHOULD
   have a rate limiting mechanism in place as a defense measure. See also
   https://datatracker.ietf.org/doc/html/rfc5389#section-16.1.2.

7. _A_ and _B_ execute the DTLS handshake as part of the standard WebRTC
   connection establishment.

   At this point _B_ does not know the TLS certificate fingerprint of _A_. Thus
   _B_ can not verify _A_'s TLS certificate fingerprint during the DTLS
   handshake. Instead _B_ needs to _disable certificate fingerprint
   verification_ (see e.g. [Pion's `disableCertificateFingerprintVerification`
   option](https://github.com/pion/webrtc/blob/360b0f1745c7244850ed638f423cda716a81cedf/settingengine.go#L62)).

   On success of the DTLS handshake the connection provides confidentiality and
   integrity but not authenticity. The latter is guaranteed through the
   succeeding Noise handshake. See [Connection Security
   section](#connection-security).

8. Messages on the established `RTCDataChannel` are framed using the message
   framing mechanism described in [Multiplexing](#multiplexing).

9. The remote is authenticated via an additional Noise handshake. See
   [Connection Security section](#connection-security).

WebRTC can run both on UDP and TCP. libp2p WebRTC implementations MUST support
UDP and MAY support TCP.

## Multiplexing

The WebRTC browser APIs do not support half-closing of streams nor resets of the
sending part of streams.
[`RTCDataChannel.close()`](https://developer.mozilla.org/en-US/docs/Web/API/RTCDataChannel/close)
flushes the remaining messages and closes the local write and read side. After
calling `RTCDataChannel.close()` one can no longer read from the channel. This
lack of functionality is problematic, given that libp2p protocols running on top
of transport protocols, like WebRTC, expect to be able to half-close or reset a
stream. See [Connection Establishment in
libp2p](https://github.com/libp2p/specs/blob/master/connections/README.md#definitions).

To support half-closing and resets of streams, libp2p WebRTC uses message
framing. Messages on a `RTCDataChannel` are embedded into the Protobuf message
below and sent on the `RTCDataChannel` prefixed with the message length in
bytes, encoded as an unsigned variable length integer as defined by the
[multiformats unsigned-varint spec][uvarint-spec].

It is an adaptation from the [QUIC RFC]. When in doubt on the semantics of
these messages, consult the [QUIC RFC].

``` proto
syntax = "proto2";

package webrtc.pb;

message Message {
  enum Flag {
    // The sender will no longer send messages on the stream.
    FIN = 0;
    // The sender will no longer read messages on the stream. Incoming data is
    // being discarded on receipt.
    STOP_SENDING = 1;
    // The sender abruptly terminates the sending part of the stream. The
    // receiver can discard any data that it already received on that stream.
    RESET_STREAM = 2;
  }

  optional Flag flag=1;

  optional bytes message = 2;
}
```

Note that in contrast to QUIC (see [QUIC RFC - 3.5 Solicited State
Transitions](https://www.rfc-editor.org/rfc/rfc9000.html#section-3.5)) a libp2p
WebRTC endpoint receiving a `STOP_SENDING` frame SHOULD NOT send a
`RESET_STREAM` frame in reply. The `STOP_SENDING` frame is used for accurate
accounting of the number of bytes sent for connection-level flow control in
QUIC. The libp2p WebRTC message framing is not concerned with flow-control and
thus does not need the `RESET_STREAM` frame to be send in reply to a
`STOP_SENDING` frame.

Encoded messages including their length prefix MUST NOT exceed 16kiB to support
all major browsers. See ["Understanding message size
limits"](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Using_data_channels#understanding_message_size_limits).
Implementations MAY choose to send smaller messages, e.g. to reduce delays
sending _flagged_ messages.

### Ordering

Implementations MAY expose an unordered byte stream abstraction to the user by
overriding the default value of `ordered` `true` to `false` when creating a new
data channel via
[`RTCPeerConnection.createDataChannel`](https://www.w3.org/TR/webrtc/#dom-peerconnection-createdatachannel).

### Head-of-line blocking

WebRTC datachannels and the underlying SCTP is message-oriented and not
stream-oriented (e.g. see
[`RTCDataChannel.send()`](https://developer.mozilla.org/en-US/docs/Web/API/RTCDataChannel/send)
and
[`RTCDataChannel.onmessage()`](https://developer.mozilla.org/en-US/docs/Web/API/RTCDataChannel#example)).
libp2p streams on the other hand are byte oriented. Thus we run into the risk of
head-of-line blocking.

Given that the browser does not give us access to the MTU on a given connection,
we can not make an informed decision on the optimal message size.

We follow the recommendation of QUIC, requiring ["a minimum IP packet size of at
least 1280
bytes"](https://datatracker.ietf.org/doc/html/draft-ietf-quic-transport-29#section-14).
An SCTP packet common header is 12 bytes long. An SCTP data chunk header size is
16 bytes. Thus implementations SHOULD choose a message size equal or below 1252
bytes. Long term we hope to be able to give better recommendations based on
real-world experiments.

### `RTCDataChannel` negotiation

`RTCDataChannel`s are negotiated in-band by the WebRTC user agent (e.g. Firefox,
Pion, ...). In other words libp2p WebRTC implementations MUST NOT change the
default value `negotiated: false` when creating a `RTCDataChannel` via
`RTCPeerConnection.createDataChannel`.

The WebRTC user agent (i.e. not the application) decides on the `RTCDataChannel`
ID based on the local node's connection role. For the interested reader see
[RF8832 Protocol
Overview](https://www.rfc-editor.org/rfc/rfc8832.html#section-4). It is
RECOMMENDED that user agents reuse IDs once their `RTCDataChannel` closes. IDs
MAY be reused according to RFC 8831: "Streams are available for reuse after a
reset has been performed", see [RFC 8831 6.7 Closing a Data Channel
](https://datatracker.ietf.org/doc/html/rfc8831#section-6.7). Up to 65535
(`2^16`) concurrent data channels can be opened at any given time.

According to RFC 8832 a `RTCDataChannel` initiator "MAY start sending messages
containing user data without waiting for the reception of the corresponding
DATA_CHANNEL_ACK message", thus using `negotiated: false` does not imply an
additional round trip for each new `RTCDataChannel`.

### `RTCDataChannel` label

`RTCPeerConnection.createDataChannel()` requires passing a `label` for the
to-be-created `RTCDataChannel`. When calling `createDataChannel` implementations
MUST pass an empty string. When receiving an `RTCDataChannel` via
`RTCPeerConnection.ondatachannel` implementations MUST NOT require `label` to be
an empty string. This allows future versions of this specification to make use
of the `RTCDataChannel` `label` property.

## Connection Security

Note that the below uses the message framing described in
[multiplexing](#multiplexing).

While WebRTC offers confidentiality and integrity via TLS, one still needs to
authenticate the remote peer by its libp2p identity.

After [Connection Establishment](#connection-establishment):

1. _A_ and _B_ open a WebRTC data channel with `id: 0` and `negotiated: true`
   ([`pc.createDataChannel("", {negotiated: true, id:
   0});`](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/createDataChannel)).

2. _B_ starts a Noise `XX` handshake on the new channel. See
   [noise-libp2p](https://github.com/libp2p/specs/tree/master/noise).

   _A_ and _B_ use the [Noise
   Prologue](https://noiseprotocol.org/noise.html#prologue) mechanism. More
   specifically _A_ and _B_ set the Noise _Prologue_ to
   `libp2p-webrtc-noise:<FINGERPRINT_A><FINGERPRINT_B>` before starting the
   actual Noise handshake. `<FINGERPRINT_A><FINGERPRINT_B>` is the concatenation
   of the two TLS fingerprints of _A_ (Noise handshake responder) and then _B_
   (Noise handshake initiator), in their multihash byte representation.

   On Chrome _A_ can access its TLS certificate fingerprint directly via
   `RTCCertificate#getFingerprints`. Firefox does not allow _A_ to do so. Browser
   compatibility can be found
   [here](https://developer.mozilla.org/en-US/docs/Web/API/RTCCertificate). In
   practice, this is not an issue since the fingerprint is embedded in the local
   SDP string.

3. On success of the authentication handshake, the used datachannel is
   closed and the plain WebRTC connection is used with its multiplexing
   capabilities via datachannels. See [Multiplexing](#multiplexing).

Note: WebRTC supports different hash functions to hash the TLS certificate (see
https://datatracker.ietf.org/doc/html/rfc8122#section-5). The hash function used
in WebRTC and the hash function used in the multiaddr `/certhash` component MUST
be the same. On mismatch the final Noise handshake MUST fail.

_A_ knows _B_'s fingerprint hash algorithm through _B_'s multiaddr. _B_ could
infer _A_'s fingerprint hash algorithm through _A_'s TLS certificate signature.
Or _B_ could assume _A_ to use the same hash algorithm it discovers through
_B_'s multiaddr. For now implementations MAY assume both _A_ and _B_ to use
sha-256. Future iterations of this specification may add support for other hash
algorithms in a backwards compatible way.

Implementations SHOULD setup all the necessary callbacks (e.g.
[`ondatachannel`](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/datachannel_event))
before starting the Noise handshake. This is to avoid scenarios like one where
_A_ initiates a stream before _B_ got a chance to set the `ondatachannel`
callback. This would result in _B_ ignoring all the messages coming from _A_
targeting that stream.

Implementations MAY open streams before completion of the Noise handshake.
Applications MUST take special care what application data they send, since at
this point the peer is not yet authenticated. Similarly, the receiving side MAY
accept streams before completion of the handshake.

## Previous, ongoing and related work

- Work in progress implementations of this specification:
  - https://github.com/little-bear-labs/js-libp2p-webrtc/
  - https://github.com/libp2p/go-libp2p/pull/1655
  - https://github.com/libp2p/rust-libp2p/pull/2622
- Past related work:
  - Proof of concept for the server side (native) and the client side (Rust in
    WASM): https://github.com/wngr/libp2p-webrtc
  - WebRTC using STUN and TURN: https://github.com/libp2p/js-libp2p-webrtc-star

## Test vectors

### Noise prologue

All of these test vectors represent hex-encoded bytes.

#### Both client and server use SHA-256

Here client is _A_ and server is _B_.

```
client_fingerprint = "3e79af40d6059617a0d83b83a52ce73b0c1f37a72c6043ad2969e2351bdca870"
server_fingerprint = "30fc9f469c207419dfdd0aab5f27a86c973c94e40548db9375cca2e915973b99"

prologue = "6c69627032702d7765627274632d6e6f6973653a12203e79af40d6059617a0d83b83a52ce73b0c1f37a72c6043ad2969e2351bdca870122030fc9f469c207419dfdd0aab5f27a86c973c94e40548db9375cca2e915973b99"
```

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

- _Why exchange fingerprints in an additional authentication handshake on top of
  an established WebRTC connection? Why not only exchange signatures of ones TLS
  fingerprints signed with ones libp2p private key on the plain WebRTC
  connection?_

  Once _A_ and _B_ established a WebRTC connection, _A_ sends
  `signature_libp2p_a(fingerprint_a)` to _B_ and vice versa. While this has the
  benefit of only requring two messages, thus one round trip, it is prone to a
  key compromise and replay attack. Say that _E_ is able to attain
  `signature_libp2p_a(fingerprint_a)` and somehow compromise _A_'s TLS private
  key, _E_ can now impersonate _A_ without knowing _A_'s libp2p private key.

  If one requires the signatures to contain both fingerprints, e.g.
  `signature_libp2p_a(fingerprint_a, fingerprint_b)`, the above attack still
  works, just that _E_ can only impersonate _A_ when talking to _B_.

  Adding a cryptographic identifier of the unique connection (i.e. session) to
  the signature (`signature_libp2p_a(fingerprint_a, fingerprint_b,
  connection_identifier)`) would protect against this attack. To the best of our
  knowledge the browser does not give us access to such identifier.

- _Why use Protobuf for WebRTC message framing. Why not use our own,
  potentially smaller encoding schema?_

  The Protobuf framing adds an overhead of 5 bytes. The unsigned-varint prefix
  adds another 2 bytes. On a large message the overhead is negligible (`(5
  bytes + 2 bytes) / (16384 bytes - 7 bytes) = 0.000427246`). On a small
  message, e.g. a multistream-select message with ~40 bytes the overhead is high
  (`(5 bytes + 2 bytes) / 40 bytes = 0.175`) but likely irrelevant.

  Using Protobuf allows us to evolve the protocol in a backwards compatibile way
  going forward. Using Protobuf is consistent with the many other libp2p
  protocols. These benefits outweigh the drawback of additional overhead.

- _Can a browser know upfront its UDP port which it is listening for incoming
  connections on? Does the browser reuse the UDP port across many WebRTC
  connections? If that is the case one could connect to any public node, with
  the remote telling the local node what port it is perceived on. Thus one could
  use libp2p's identify and AutoNAT protocol instead of relying on STUN._

  No, a browser uses a new UDP port for each `RTCPeerConnection`.

- _Why not load a remote node's certificate into one's browser trust-store and
  then connect e.g. via WebSocket._

  This would require a mechanism to discover remote node's certificates upfront.
  More importantly, this does not scale with the number of connections a typical
  peer-to-peer application establishes.

- _Why not use a central TURN servers? Why rely on libp2p's Circuit Relay v2
  instead?_

  As a peer-to-peer networking library, libp2p should rely as little as possible
  on central infrastructure.

- _Can an attacker launch an amplification attack with the STUN endpoint of
  the server?_

  We follow the reasoning of the QUIC protocol, namely requiring:

  > an endpoint MUST limit the amount of data it sends to the unvalidated
  > address to three times the amount of data received from that address.

  https://datatracker.ietf.org/doc/html/rfc9000#section-8

  This is the case for STUN response messages which are only slight larger than
  the request messages. See also
  https://datatracker.ietf.org/doc/html/rfc5389#section-16.1.2.

- _Why does B start the Noise handshake and not A?_

  Given that WebRTC uses DTLS 1.2, _B_ is the one that can send data first.

[QUIC RFC]: https://www.rfc-editor.org/rfc/rfc9000.html
[uvarint-spec]: https://github.com/multiformats/unsigned-varint
