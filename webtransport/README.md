# libp2p WebTransport

| Lifecycle Stage | Maturity                 | Status | Latest Revision |
|-----------------|--------------------------|--------|-----------------|
| 1A              | DRAFT                    | Active | r0, 2022-04-03  |

Authors: [@marten-seemann]

Interest Group: TODO

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

## Introduction

WebTransport is a way for browsers to establish a stream-multiplexed connection to servers that allows bidirectional streaming.

The WebTransport protocol is currently under development at the IETF. Chrome has implemented and shipped support for [draft-02](https://datatracker.ietf.org/doc/draft-ietf-webtrans-http3/).

The most exciting feature for libp2p (other than the improved performance and hole punching success rates that QUIC gives us) is that the W3C added a browser API allowing browsers to establish connections to nodes with self-signed certificates, provided they know the hash of the certificate in advance: `[serverCertificateHashes](https://www.w3.org/TR/webtransport/#dom-webtransportoptions-servercertificatehashes)`. This API is already [implemented in Chrome](https://chromestatus.com/feature/5690646332440576). Firefox is working on a WebTransport implementation and is [likely to implement](https://github.com/mozilla/standards-positions/issues/167#issuecomment-1015951396) `serverCertificateHashes` as well.

## Certificates

Server nodes can choose between 2 modes of operation:
1. They possess a certificate that's accepted by the WebPKI (i.e. a certificate signed by a well-known certificate authority). Due to the p2p nature of libp2p, obtaining such a certificate will only be practical for a small number of nodes.
2. They use a self-signed certificate. According to the [w3c WebTransport certification](https://www.w3.org/TR/webtransport/), the validity of the certificate MUST be at most 14 days. Nodes then include the hash of one (or more) certificates in their multiaddr (see [#addressing]).

When using self-signed certificates, nodes need to take care to regularly renew their certificate. In the following, the RECOMMENDED logic for rolling certificates is described. At first boot of the node, it creates a self-signed certificate with a validity of 14 days, and publishes a multiaddr containing the hash of that certificate. After 10 days, the node prepares the next certificate, setting the `NotBefore` date of that certificate to the expiration date (or shortly before that) of the first certificate, and an expiration of 14 days after that. The node continues using the old certificate until its expiry date, but it already advertises a multiaddr containing both certificate hashes. This way, clients will be able to connect to the node, even if they cache the multiaddr for multiple days.

## Addressing

Webtransport multiaddresses are composed of a QUIC multiaddr, followed by `/webtransport` and a list of multihashes of the certificates that the server uses.
Examples:
* `/ip4/1.2.3.4/udp/443/quic/webtransport/`
* `/ip6/fe80::1ff:fe23:4567:890a/udp/1234/quic/webtransport/<hash1><hash2><hash3>`

If it is able to present a CA-signed certificate the list of certificate hashes SHOULD be empty. When using self-signed certificates, the server MUST include the hash(es) in the multiaddr.

## WebTransport HTTP endpoint

WebTransport needs a HTTPS URL to establish a WebTransport session, e.g. `https://example.com/webtransport`. As multiaddrs don't allow the encoding of URLs, this spec standardizes the endpoint. The HTTP endpoint of a libp2p WebTransport servers MUST be located at `/.well-known/libp2p-webtransport`.

To allow future evolution of the way we run the libp2p handshake over WebTransport, we use a URL parameter. The handshake described in this document MUST be signaled by setting the `type` URL parameter to `multistream`.

Example: The WebTransport URL of a WebTransport server advertising `/ip4/1.2.3.4/udp/1443/quic/webtransport/` would be `https://1.2.3.4:1443/.well-known/libp2p-webtransport?type=multistream`.

## Security Handshake

Unfortunately, the self-signed certificate doesn't allow the nodes to authenticate each others' peer IDs. It is therefore necessary to run an additional libp2p handshake on a newly established WebTransport connection.
Once a WebTransport session is established, the clients opens a new stream and initiates a libp2p handshake (selecting the security protocol by running multistream, then performing the selected handshake).

Note: Once we include the security protocol in the multiaddr (see https://github.com/libp2p/specs/pull/353), we will be able to shave off two (!!) round-trips here: Not running multistream saves one round trip. Furthermore, we'll be able to run the WebTransport handshake (i.e. the CONNECT request) in parallel with the cryptographic handshake, for example by transmitting the first handshake message as a URL parameter. The specifics of this is left to a future iteration of this spec.

## Securing Streams

All streams other than the stream used for the security handshake are protected using Salsa20. Two (symmetric) keys are derived from the master secrect established during the handshake, one for sending and for receiving on the stream.

When using TLS, the 32 byte key used by Salsa20 is derived using the algorithm described in RFC 5705. In Go, this is achieved by using [`tls.ConnectionState.ExportKeyingMaterial`](https://pkg.go.dev/crypto/tls#ConnectionState.ExportKeyingMaterial). The label is `libp2p-webtransport-stream-<perspective>`, where `<perspective>` is `client` or `server`, respectively, depending on which side is sending on the stream, and the context is the QUIC stream ID, serialized as a uint64 in network byte order.

TODO: We need a similar construction for Noise.
