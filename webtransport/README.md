# libp2p WebTransport

| Lifecycle Stage | Maturity                 | Status | Latest Revision |
|-----------------|--------------------------|--------|-----------------|
| 1A              | DRAFT                    | Active | r0, 2022-04-03  |

Authors: [@marten-seemann]

Interest Group: TODO

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

## Introduction

WebTransport is a way for browsers to establish a stream-multiplexed and bidirectional connection to servers using QUIC.

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
* `/ip6/fe80::1ff:fe23:4567:890a/udp/1234/quic/webtransport/certhash/<hash1>/certhash/<hash2>/certhash/<hash3>`

If it is able to present a CA-signed certificate the list of certificate hashes SHOULD be empty. When using self-signed certificates, the server MUST include the hash(es) in the multiaddr.

## WebTransport HTTP endpoint

WebTransport needs a HTTPS URL to establish a WebTransport session, e.g. `https://example.com/webtransport`. As multiaddrs don't allow the encoding of URLs, this spec standardizes the endpoint. The HTTP endpoint of a libp2p WebTransport servers MUST be located at `/.well-known/libp2p-webtransport`.

To allow future evolution of the way we run the libp2p handshake over WebTransport, we use a URL parameter. The handshake described in this document MUST be signaled by setting the `type` URL parameter to `noise`.

Example: The WebTransport URL of a WebTransport server advertising `/ip4/1.2.3.4/udp/1443/quic/webtransport/` would be `https://1.2.3.4:1443/.well-known/libp2p-webtransport?type=noise`.

## Security Handshake

Unfortunately, the self-signed certificate doesn't allow the nodes to authenticate each others' peer IDs. It is therefore necessary to run an additional libp2p handshake on a newly established WebTransport connection.
The first stream that the client opens on a new WebTransport session is used to perform a libp2p handshake using Noise (https://github.com/libp2p/specs/tree/master/noise). The client SHOULD start the handshake right after sending the CONNECT request, without waiting for the server's response.

In order to verify that the end-to-end encryption of the connection, the peers need to establish that no MITM intercepted the connection. To do so, the client MUST include the certificate hash that was used to establish the connection as payload of the first Noise message (the `e` message). This payload is not encrypted, but the Noise handshake provides integrity protection.
If the client was willing to accept multiple certificate hashes, but cannot determine with certificate was actually used to establish the connection (this will commonly be the case for browser clients), it MUST include a list of all certificate hashes.

Certificate hashes are encoded using the following protobuf message:
```proto
syntax = "proto2";

message WebTransport {
  repeated bytes cert_hashes = 1;
}
```

On receipt of the `e` message, the server MUST verify the list of certificate hashes. If the list is empty, it MUST fail the handshake. For every certificate in the list, it checks if it possesses a certificate with the corresponding hash. If so, it continues with the handshake. However, if there is even a single certificate hash in the list that it cannot associate with a certificate, it MUST abort the handshake.

For the client, the libp2p connection is fully established once it has sent the last Noise handshake message. For the server, receipt (and successful verification) of that message completes the handshake.
