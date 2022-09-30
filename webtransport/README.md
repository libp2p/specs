# libp2p WebTransport

| Lifecycle Stage | Maturity                 | Status | Latest Revision |
|-----------------|--------------------------|--------|-----------------|
| 1A              | Candidate Recommendation | Active | r0, 2022-09-28  |

Authors: [@marten-seemann]

Interest Group: [@MarcoPolo], [@mxinden]

See the [lifecycle document](../00-framework-01-spec-lifecycle.md) for context about maturity level
and spec status.

## Introduction

[WebTransport](https://datatracker.ietf.org/doc/draft-ietf-webtrans-overview/) is a way for browsers to establish a stream-multiplexed and bidirectional connection to servers. The WebTransport protocol is currently under development at the IETF. The primary way to do by running on top of a HTTP/3 connection [WebTransport over HTTP/3](https://datatracker.ietf.org/doc/draft-ietf-webtrans-http3/). For situations where it is not possible to establish a HTTP/3 connection, there's a HTTP/2 fallback ([WebTransport using HTTP/2](https://datatracker.ietf.org/doc/draft-ietf-webtrans-http2/)).

In this document, we mean WebTransport over HTTP/3 when using the term WebTransport.

Chrome has implemented and shipped support for [draft-02](https://datatracker.ietf.org/doc/draft-ietf-webtrans-http3/02/), and Firefox [is working](https://bugzilla.mozilla.org/show_bug.cgi?id=1709355) on WebTransport support.

The most exciting feature for libp2p (other than the numberous performance benefits that QUIC gives us) is that the W3C added a browser API allowing browsers to establish connections to nodes with self-signed certificates, provided they know the hash of the certificate in advance: [`serverCertificateHashes`](https://www.w3.org/TR/webtransport/#dom-webtransportoptions-servercertificatehashes). This API is already [implemented in Chrome](https://chromestatus.com/feature/5690646332440576). Firefox is working on a WebTransport implementation and is [likely to implement](https://github.com/mozilla/standards-positions/issues/167#issuecomment-1015951396) `serverCertificateHashes` as well.

## Certificates

Since most libp2p nodes don't possess a TLS certificate signed by a Certificate Authority, servers use a self-signed certificates. According to the [w3c WebTransport certification](https://www.w3.org/TR/webtransport/), the validity of the certificate MUST be at most 14 days, and must not use an RSA key. Nodes then include the hash of one (or more) certificates in their multiaddr (see [Addressing](#addressing)).

Servers need to take care to regularly renew their certificate. In the following, the RECOMMENDED logic for rolling certificates is described. At first boot of the node, it creates one self-signed certificate with a validity of 14 days, starting immediately, and another certificate with the 14 day valididity period starting on the expiry date of the first certificate. The node advertises a multiaddr containing the certificate hashes of these two certificates.
Once the first certificate has expired, the node prepares the next certificate, and updates the multiaddr it advertises.

## Addressing

Webtransport multiaddresses are composed of a QUIC multiaddr, followed by `/webtransport` and a list of multihashes of the certificates that the server uses.
Examples:
* `/ip4/1.2.3.4/udp/443/quic/webtransport/certhash/<hash1>`
* `/ip6/fe80::1ff:fe23:4567:890a/udp/1234/quic/webtransport/certhash/<hash1>/certhash/<hash2>/certhash/<hash3>`

## WebTransport HTTP endpoint

WebTransport needs a HTTPS URL to establish a WebTransport session, e.g. `https://example.com/webtransport`. At the point of writing multiaddresses don't allow the encoding of URLs, therefore this spec standardizes the endpoint. The HTTP endpoint of a libp2p WebTransport server MUST be located at `/.well-known/libp2p-webtransport`.

To allow future evolution of the way we run the libp2p handshake over WebTransport, we use a URL parameter. The handshake described in this document MUST be signaled by setting the `type` URL parameter to `noise`.

Example: The WebTransport URL of a WebTransport server advertising `/ip4/1.2.3.4/udp/1443/quic/webtransport/` would be `https://1.2.3.4:1443/.well-known/libp2p-webtransport?type=noise`.

## Security Handshake

Unfortunately, the self-signed certificate doesn't allow the nodes to authenticate each others' peer IDs. It is therefore necessary to run an additional libp2p handshake on a newly established WebTransport connection.
The first stream that the client opens on a new WebTransport session is used to perform a libp2p handshake using Noise (https://github.com/libp2p/specs/tree/master/noise). The client SHOULD start the handshake right after sending the CONNECT request, without waiting for the server's response.

In order to verify end-to-end encryption of the connection, the peers need to establish that no MITM intercepted the connection. To do so, the server MUST include the certificate hash of the currently used certificate as well as the certificate hashes of all future certificates it has already advertised to the network in the `webtransport_certhashes` Noise extension (see Noise Extension section of the [Noise spec](/noise/README.md)). The hash of recently used, but expired certificates SHOULD also be included.

On receipt of the `webtransport_certhashes` extension, the client MUST verify that the certificate hash of the certificate that was used on the connection is contained in the server's list. If the client was willing to accept multiple certificate hashes, but cannot determine which certificate was actually used to establish the connection (this will commonly be the case for browser clients), it MUST verify that all certificate hashes are contained in the server's list. If verification fails, it MUST abort the handshake.

For the client, the libp2p connection is fully established once it has sent the last Noise handshake message. For the server, processing of that message completes the handshake.
