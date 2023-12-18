# Stream multiplexer negotiation in security handshake <!-- omit in toc -->


| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r1, 2022-12-07  |

Authors: [@julian88110], [@marten-seemann]

Interest Group: [@marcopolo], [@mxinden]

[@marten-seemann]: https://github.com/marten-seemann
[@marcopolo]: https://github.com/marcopolo
[@mxinden]: https://github.com/mxinden
[@julian88110]: https://github.com/julian88110

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Table of Contents <!-- omit in toc -->

- [Overview](#overview)
- [Design](#design)
  - [Multiplexer Negotiation over TLS](#multiplexer-negotiation-over-tls)
  - [Multiplexer Negotiation over Noise](#multiplexer-negotiation-over-noise)
- [Privacy](#privacy)
- [Alternative options considered](#alternative-options-considered)

## Overview

Transports that don't support native stream multiplexing (e.g. TCP, WebSocket) negotiate
a stream multiplexer after completion of the cryptographic handshake, as described in [connections]. 
Negotiating the stream multiplexer takes one network roundtrip.
This document defines a backwards-compatible optimization, which allows running the
multiplexer negotiation during the cryptographic handshake, thereby reducing the latency of
connection establishment by one roundtrip.


## Design

### Multiplexer Negotiation over TLS

When using TLS, the [ALPN] extension is used to negotiate the multiplexer.

The ALPN TLS extension allows the client to send a list of supported application
protocols as part of the TLS `ClientHello` message.  The server chooses
a protocol and sends the selected protocol as part of the TLS
`ServerHello` message.

For the purpose of multiplexer negotiation, the protocol IDs of the stream 
multiplexers are sent, followed by the `"libp2p"` protocol code. The multiplexer list is ordered by
the client's preference, with the most preferred multiplexer at the beginning.
The server SHOULD respect the client's preference and pick the first protocol
from the list that it supports.

Example for a node supporting both yamux and mplex, with a preference for yamux:
```json
[ "/yamux/1.0.0", "/mplex/6.7.0", "libp2p" ]
```

The `"libp2p"` protocol code MUST always be the last item in the multiplexer list.
According to [TLS], nodes that don't implement the optimization described in
this document use `"libp2p"` for their ALPN. If `"libp2p"` is the result of the
ALPN process, nodes MUST use protocol negotiation of the stream multiplexer
as described in [connections].

### Multiplexer Negotiation over Noise

The libp2p Noise Specification allows Noise handshake messages to carry
early data. [Noise-Early-Data] is carried in the second and third message of
the XX handshake pattern as illustrated in the following message sequence chart.
The second message carries early data in the form of a list of multiplexers
supported by the responder. The initiator sends its supported multiplexer list 
in the third message of the handshake process, ordered by its preference. It
MAY choose a single multiplexer from the responder's list and only send that
value.

The multiplexer to use is determined by picking the first item from the
initiator's list that both parties support.

Example: Noise handshake between two clients that both support mplex and yamux. The
client prefers yamux, whereas the server prefers mplex. 

```
XX:
-> e
<- e, ee, s, es, [ "/mplex/6.7.0", "/yamux/1.0.0" ] 
-> s, se, [ "/yamux/1.0.0", "/mplex/6.7.0" ] 
```

The result of this negotiation is `"/yamux/1.0.0"`.

If there is no overlap between the multiplexers support by client and server,
the handshake MUST fail.

The format of the early data is specified in [Noise-handshake-payload].


## Privacy

The list of multiplexers carried in the TLS ALPN extension field is part of the
unencrypted ClientHello message. Therefore, using this optimization
exposes the list of supported multiplexers to an on-path observer. This leak can
be considered insignificant, since a libp2p node reveals its list of supported
multiplexers to any node that connects to it.

However, the NoiseExtensions in the Noise handshake are sent after the peers have 
established a shared key, so an on-path observer won't be able to obtain the
list of multiplexers.


## Alternative options considered

Instead of ALPN for multiplexer selection to reduce RTT, other options such as
TLS extension and X.509 extension were considered. The pros and cons are explored
and the discussion details can be found at [#454].


[TLS]: https://github.com/libp2p/specs/blob/master/tls/tls.md
[connections]: https://github.com/libp2p/specs/tree/master/connections
[ALPN]: https://datatracker.ietf.org/doc/html/rfc7301
[Noise-Early-Data]: https://github.com/libp2p/specs/tree/master/noise#libp2p-data-in-handshake-messages
[ECH]: https://datatracker.ietf.org/doc/draft-ietf-tls-esni/
[#454]: https://github.com/libp2p/specs/issues/454
[Noise-handshake-payload]: https://github.com/libp2p/specs/tree/master/noise#the-libp2p-handshake-payload

