# WebRTC Direct

| Lifecycle Stage | Maturity                  | Status | Latest Revision |
|-----------------|---------------------------|--------|-----------------|
| 2A              | Candidate Recommendation  | Active | r2, 2026-06-20  |

Authors: [@mxinden]

Interest Group: [@marten-seemann], [@dozyio], [@lidel]

[@marten-seemann]: https://github.com/marten-seemann
[@mxinden]: https://github.com/mxinden/
[@dozyio]: https://github.com/dozyio
[@lidel]: https://github.com/lidel

## Motivation

**No need for trusted TLS certificates.** Enable browsers to connect to public
server nodes without those server nodes providing a TLS certificate within the
browser's trustchain. Note that we can not do this today with our Websocket
transport as the browser requires the remote to have a trusted TLS certificate.
Nor can we establish a plain TCP or QUIC connection from within a browser. We
can establish a WebTransport connection from the browser (see [WebTransport
specification](../webtransport)).

## Addressing

WebRTC Direct multiaddresses are composed of an IP and UDP address component, followed
by `/webrtc-direct` and a multihash of the certificate that the node uses.

Examples:
- `/ip4/1.2.3.4/udp/1234/webrtc-direct/certhash/<hash>/p2p/<peer-id>`
- `/ip6/fe80::1ff:fe23:4567:890a/udp/1234/webrtc-direct/certhash/<hash>/p2p/<peer-id>`

The TLS certificate fingerprint in `/certhash` is a
[multibase](https://github.com/multiformats/multibase) encoded
[multihash](https://github.com/multiformats/multihash).

WebRTC Direct v1 and v2 share the same `/webrtc-direct` multiaddr. The server
picks the version from the ICE username fragment prefix, not from a separate
multiaddr protocol.

For compatibility implementations MUST support hash algorithm
[`sha-256`](https://github.com/multiformats/multihash) and base encoding
[`base64url`](https://github.com/multiformats/multibase). Implementations MAY
support other hash algorithms and base encodings, but they may not be able to
connect to all other nodes.

## Connection Establishment

There are two connection establishment flows, v1 and v2. New connections SHOULD
use v2: v1 relies on SDP munging that browsers are removing, so its
browser-to-server path will stop working in the near future (see [Browser to
public Server v2](#browser-to-public-server-v2-no-sdp-munging) for details). v1
is documented here because existing peers still use it; servers SHOULD keep
accepting it while browsers still allow v1 and the ecosystem of web clients
migrates to v2.

### Browser to public Server v1 (SDP munging)

Scenario: Browser _A_ wants to connect to server node _B_ where _B_ is publicly
reachable but _B_ does not have a TLS certificate trusted by _A_.

1. Server node _B_ generates a TLS certificate, listens on a UDP port and
   advertises the corresponding multiaddress (see [#addressing]) through some
   external mechanism.

   Given that _B_ is publicly reachable, _B_ acts as a [ICE
   Lite](https://www.rfc-editor.org/rfc/rfc5245) agent. It binds to a UDP port
   waiting for incoming STUN and SCTP packets and multiplexes based on source IP
   and source port.

2. Browser _A_ discovers server node _B_'s multiaddr, containing _B_'s IP, UDP
  port, TLS certificate fingerprint and optionally libp2p peer ID (e.g.
  `/ip6/2001:db8::/udp/1234/webrtc-direct/certhash/<hash>/p2p/<peer-id>`), through some
  external mechanism.

3. _A_ instantiates a `RTCPeerConnection`. See
   [`RTCPeerConnection()`](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/RTCPeerConnection).

   _A_ (i.e. the browser) SHOULD NOT reuse the same certificate across
   `RTCPeerConnection`s. Reusing the certificate can be used to identify _A_
   across connections by on-path observers given that WebRTC uses TLS 1.2.

4. _A_ constructs _B_'s SDP answer locally based on _B_'s multiaddr.

   _A_ generates a random string prefixed with `libp2p+webrtc+v1/` and sets it
   as both the username fragment (`ice-ufrag`) and password (`ice-pwd`) in the
   synthetic remote answer SDP.

   _A_ MUST set the `a=max-message-size:16384` SDP attribute. See reasoning
   [multiplexing] for rational.

   Finally _A_ sets the remote answer via
   [`RTCPeerConnection.setRemoteDescription()`](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/setRemoteDescription).

5. _A_ creates a local offer via
   [`RTCPeerConnection.createOffer()`](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/createOffer).
   _A_ sets the same username and password on the local offer as done in (4) on
   the remote answer.

   _A_ MUST set the `a=max-message-size:16384` SDP attribute. See reasoning
   [multiplexing] for rational.

   Finally _A_ sets the modified offer via
   [`RTCPeerConnection.setLocalDescription()`](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/setLocalDescription).

   Note that this process, oftentimes referred to as "SDP munging" is disallowed
   by the specification, but not enforced across the major browsers (Safari,
   Firefox, Chrome) due to use-cases in the wild. See also
   https://bugs.chromium.org/p/chromium/issues/detail?id=823036

   Chromium is rolling out the [`WebRTC-NoSdpMangleUfrag`][nosdpmangle] field
   trial, which blocks this ufrag munging and so breaks this step.
   [Browser to public Server v2](#browser-to-public-server-v2-no-sdp-munging)
   avoids munging altogether and is the most future-proof way to establish
   browser-to-server connections; new deployments SHOULD prefer it.

6. Once _A_ sets the SDP offer and answer, it will start sending STUN requests
   to _B_. _B_ reads the _ufrag_ from the incoming STUN request's _username_
   field. _B_ then infers _A_'s SDP offer using the IP, port, and _ufrag_ of the
   request as follows:

   1. _B_ sets the the `ice-ufrag` and `ice-pwd` equal to the value read from
      the `username` field.

   2. _B_ sets an arbitrary sha-256 digest as the remote fingerprint as it does
      not verify fingerprints at this point.

   3. _B_ sets the connection field (`c`) to the IP of the incoming
      request `c=IN <IP4|IP6> <ip>`.

   4. _B_ sets the `a=max-message-size:16384` SDP attribute. See reasoning
      [multiplexing] for rational.

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

8. Messages on each `RTCDataChannel` are framed using the message
   framing mechanism described in [Multiplexing].

9. The remote is authenticated via an additional Noise handshake. See
   [Connection Security section](#connection-security).

### Browser to public Server v2 (no SDP munging)

v2 keeps the same no-signaling model and the same `/webrtc-direct` multiaddr as
v1, but it never munges the local SDP offer. It exists because browsers are
taking munging away: Chromium's [`WebRTC-NoSdpMangleUfrag`][nosdpmangle] field
trial blocks any change to `a=ice-ufrag` (and `a=ice-pwd`) between `createOffer`
and `setLocalDescription`, so _B_ can no longer predict _A_'s credentials the way
v1 step (5) relies on. See the WebRTC issue [411871813][webrtc-411871813], the
[discuss-webrtc notice][discuss-webrtc-psa], and the [`getStats` side
channel][webrtc-stats-789] that prompted it. Instead of munging, _A_ leaves its
local credentials alone and puts its own ICE password into the username fragment
of the synthetic remote answer, where _B_ reads it back from the STUN `USERNAME`
with no signaling channel.

_B_ picks the version from `server_ufrag`, the part of the STUN `USERNAME` before
the first `:` (an ICE ufrag never contains `:`). The prefix `libp2p+webrtc+v2/`
selects this flow; `libp2p+webrtc+v1/` selects
[v1](#browser-to-public-server-v1-sdp-munging). The `libp2p+webrtc+` namespace is
reserved for versions: if _B_ does not recognize the version, or sees no such
prefix, it MUST reject the connection rather than guess a version, so _B_ never
mistakes a future version for an older one. A _B_ that supports both flows MUST
serve them on the same UDP port and route each incoming connection by this
prefix.

1. _A_ and _B_ perform steps (1), (2), and (3) from
   [Browser to public Server v1 (SDP munging)](#browser-to-public-server-v1-sdp-munging).
   As in v1, _B_ is ICE _controlled_: it acts as an [ICE
   Lite](https://www.rfc-editor.org/rfc/rfc8445) agent that answers connectivity
   checks but never starts its own.

2. _A_ creates a local offer via
   [`RTCPeerConnection.createOffer()`](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/createOffer)
   and sets it via
   [`RTCPeerConnection.setLocalDescription()`](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/setLocalDescription).
   _A_ MUST NOT modify ("munge") the local offer's `a=ice-ufrag` or `a=ice-pwd`;
   they stay as the browser-generated random values. We call them `client_ufrag`
   and `client_pwd` below.

3. _A_ reads its local ICE password `client_pwd` from the `a=ice-pwd` line of
   [`RTCPeerConnection.localDescription`](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/localDescription)
   after step (2), so it sees the value the browser actually chose. An ICE
   password is 22 to 256 `ice-char`s (`ALPHA / DIGIT / "+" / "/"`, which never
   includes `:`); see [RFC 8839], section 5.4 for the grammar and [RFC 8445],
   section 5.3 for the randomness requirement. Browser-generated passwords meet
   this. If _A_ cannot read a valid password back, it MUST abort the dial rather
   than continue with an incomplete credential.

   _A_ builds _B_'s synthetic remote answer and sets both the ICE username
   fragment and password to `libp2p+webrtc+v2/` followed by `client_pwd`:
   - `a=ice-ufrag:libp2p+webrtc+v2/<client_pwd>`
   - `a=ice-pwd:libp2p+webrtc+v2/<client_pwd>`

   The resulting `server_ufrag` MUST be a valid ICE username fragment (4 to 256
   `ice-char`s, [RFC 8839], section 5.4); the 17-character prefix counts toward
   this limit, so it caps how long `client_pwd` can be. The answer is an ICE Lite
   answer (`a=ice-lite`) with `a=setup:passive`, which makes _A_ the DTLS client
   and _B_ the DTLS server. _A_ MUST set `a=max-message-size:16384` and take the
   remote fingerprint from _B_'s `/certhash`. _A_ sets the remote answer via
   [`RTCPeerConnection.setRemoteDescription()`](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/setRemoteDescription).

4. _A_ starts sending STUN connectivity checks. The browser signs each check's
   `MESSAGE-INTEGRITY` with the ICE password it took from the synthetic answer
   (`libp2p+webrtc+v2/<client_pwd>`) and sets its `USERNAME` attribute to
   `server_ufrag:client_ufrag` ([RFC 8445], section 7.2.2). _B_ splits the
   `USERNAME` on the first `:` into `server_ufrag` and `client_ufrag`, and MUST
   check that both are well-formed ICE username fragments (the `ice-char` set and
   length bounds of [RFC 8839], section 5.4), rejecting the connection otherwise.
   This keeps attacker-controlled bytes such as `CR`/`LF` out of the SDP _B_
   builds in step (5). The `libp2p+webrtc+v2/` prefix on `server_ufrag` selects
   this flow (see version selection above).

5. _B_ recovers `client_pwd` by stripping the `libp2p+webrtc+v2/` prefix from
   `server_ufrag`. If the result is not a valid ICE password (22 to 256
   `ice-char`s, [RFC 8839], section 5.4), _B_ MUST reject the connection. _B_
   then infers _A_'s SDP offer as in v1 step (6), except the username fragment
   and password now differ:
   1. `a=ice-ufrag` = `client_ufrag`
   2. `a=ice-pwd` = `client_pwd` (the value recovered above)
   3. an arbitrary sha-256 remote fingerprint (verification is disabled, see v1
      step (7))
   4. `c=IN <IP4|IP6> <ip>` from the incoming STUN packet source
   5. `a=max-message-size:16384`
   6. `a=setup:actpass` (or `active`); _B_ answers as the DTLS server

6. Before generating its answer, _B_ MUST set its own local ICE username fragment
   and password to `server_ufrag` (the exact value _A_ embedded,
   `libp2p+webrtc+v2/<client_pwd>`). ICE needs this: _A_ signs its checks with
   this value and expects _B_'s STUN responses to use it too. _B_ sets the
   inferred offer from step (5) as the remote description, then generates its
   answer and sets it as the local description. That answer is an ICE Lite answer
   with `a=setup:passive` (so _B_ is the DTLS server) and carries the credentials
   set above.

7. _A_ and _B_ continue with steps (7), (8), and (9) from
   [Browser to public Server v1 (SDP munging)](#browser-to-public-server-v1-sdp-munging).

## Transport Support

WebRTC can run both on UDP and TCP. libp2p WebRTC implementations MUST support
UDP and MAY support TCP.

## Connection Security

Note that the below uses the message framing described in
[multiplexing].

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
   `<PREFIX><FINGERPRINT_A><FINGERPRINT_B>` before starting the actual Noise
   handshake. `<PREFIX>` is the UTF-8 byte representation of the string
   `libp2p-webrtc-noise:`. `<FINGERPRINT_A><FINGERPRINT_B>` is the concatenation
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
   capabilities via datachannels. See [Multiplexing].

Note: WebRTC supports different hash functions to hash the TLS certificate (see
https://datatracker.ietf.org/doc/html/rfc8122#section-5). The hash function used
in WebRTC and the hash function used in the multiaddr `/certhash` component MUST
be the same. On mismatch the final Noise handshake MUST fail.

_A_ knows _B_'s fingerprint hash algorithm through _B_'s multiaddr. _A_ MUST use
the same hash algorithm to calculate the fingerprint of its (i.e. _A_'s) TLS
certificate. _B_ assumes _A_ to use the same hash algorithm it discovers through
_B_'s multiaddr. For now implementations MUST support sha-256. Future iterations
of this specification may add support for other hash algorithms.

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

  Most new versions roll out within the same `/webrtc-direct` multiaddr by adding
  a `libp2p+webrtc+<version>/` ICE username fragment prefix, the way v2 was added
  alongside v1 (see [Connection Establishment](#connection-establishment)). A new
  multiaddr protocol (e.g. `/webrtc-direct-3`) is only needed for a wire change
  the prefix cannot negotiate, for example one the dialer needs to know from the
  multiaddr before it opens the connection.

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

[multiplexing]: ./README.md#multiplexing
[RFC 8445]: https://www.rfc-editor.org/rfc/rfc8445
[RFC 8839]: https://www.rfc-editor.org/rfc/rfc8839
[nosdpmangle]: https://webrtc-review.googlesource.com/c/src/+/385721
[webrtc-411871813]: https://issues.webrtc.org/issues/411871813
[discuss-webrtc-psa]: https://groups.google.com/g/discuss-webrtc/c/PIJZN5MTZF4
[webrtc-stats-789]: https://github.com/w3c/webrtc-stats/issues/789
