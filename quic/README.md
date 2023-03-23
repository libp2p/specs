# QUIC in libp2p

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 3A              | Recommendation | Active | r1, 2022-12-30  |

Authors: [@marten-seemann]

Interest Group: [@elenaf9], [@MarcoPolo]

[@marten-seemann]: https://github.com/marten-seemann
[@elenaf9]: https://github.com/elenaf9
[@MarcoPolo]: https://github.com/MarcoPolo

See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## QUIC vs. TCP

QUIC [RFC9000] is, alongside TCP, one of the transports that allows non-browser libp2p nodes to establish connections to each other.
Due to its inherently faster handshake latency (a single network-roundtrip), and generally better performance characteristics, it is RECOMMENDED that libp2p implementations offer QUIC as one of their transports.
However, UDP is blocked in a small fraction of networks, therefore it is RECOMMENDED that libp2p nodes offer a TCP-based connection option as a fallback.

### Multiaddress

A QUIC multiaddress encodes the IP address and UDP port. For example, these are valid QUIC multiaddresses:
* `/ip4/127.0.0.1/udp/1234/quic-v1`: A QUIC listener running on localhost on port 1234.
* `/ip6/2001:db8:3333:4444:5555:6666:7777:8888/udp/443/quic-v1`: A QUIC listener running on 2001:db8:3333:4444:5555:6666:7777:8888 on port 443.
* `/ip4/12.34.56.78/udp/4321/quic`: A QUIC listener, supporting QUIC draft-29 (see below) 

### QUIC Versions

When IPFS first rolled out QUIC support, RFC 9000 was not finished yet. Back then, QUIC was rolled out based on [IETF QUIC working group draft-29].
Nodes supporting draft-29 use the `/quic` multiaddress component (instead of `/quic-v1`) to signal support for the draft version.
Nodes supporting RFC 9000 use the `/quic-v1` multiaddress component.

New implementations SHOULD implement support for RFC 9000. Support for draft-29 is currently being phased out of production networks, and will be deprecated at some point in the future.

### ALPN

"libp2p" is used as the application protocol for ALPN.
Note that QUIC enforces the use of ALPN, so the handshake will fail if both peers can't agree on the application protocol.

### Peer Authentication

Peers authenticate each other using the TLS handshake logic described in the [libp2p TLS spec].

[RFC9000]: https://datatracker.ietf.org/doc/html/rfc9000
[IETF QUIC working group draft-29]: https://datatracker.ietf.org/doc/html/draft-ietf-quic-transport-29
[libp2p TLS spec]: ../tls
