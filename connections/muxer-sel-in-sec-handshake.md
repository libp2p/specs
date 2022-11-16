# Stream multiplexer negotiation in security handshake


| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r1, 2022-09-07  |

Authors: [@julian88110], [@marten-seemann]

Interest Group: [@marcopolo], [@mxinden]

[@marten-seemann]: https://github.com/marten-seemann
[@marcopolo]: https://github.com/marcopolo
[@mxinden]: https://github.com/mxinden
[@julian88110]: https://github.com/julian88110

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Table of Contents

- [multiplexer negotiation in security handshake](#multiplexer-negotiation-in-security-handshake)
    - [Table of Contents](#table-of-contents)
    - [Overview](#overview)
    - [Design](#design)
        - [Current connection upgrade process](#current-connection-upgrade-process)
        - [Improved multiplexer negotiation](#improved-multiplexer-negotiation)
            - [Multiplexer negotiation over TLS](#multiplexer-negotiation-over-tls)
            - [Multiplexer negotiation over Noise](#multiplexer-negotiation-over-noise)
    - [Security](#security)
    - [Alternative options considered](#alternative-options-considered)

## Overview

Transports that don't support native stream multiplexing (e.g. TCP, WebSocket) negotiate
a stream multiplexer after completion of the cryptographic handshake, as described in [connections]. 
Negotiating the stream multiplexer takes one network roundtrip.
This document defines a backwards-compatible optimization, which allows running the
multiplexer negotiation during the cryptographic handshake, thereby reducing the latency of
connection establishment by one roundtrip.


## Design

### Current connection upgrade process

The current connection upgrade process is described in detail in [connections].
As shown in this [sequence-chart], after a network connection is established,
the following will happen to upgrade the connection to a secured and stream-
multiplexed connection.

1. The multistream-selection protocol is run over the connection to select the
security protocol to be used.
2. The selected security protocol performs handshaking and establishes a secure
tunnel
3. The multistream-selection protocol then will run again for stream multiplexer
negotiation.
4. The selected stream multiplexer is then used on the secured connection.

### Improved multiplexer negotiation 

The security protocol's ability of supporting higher level abstract protocol
negotiation (for example, TLS's support of ALPN, and Noise's support of Early
Data) makes it possible to collapse the step 2 and step 3 in the previous
section into one step. Multiplexer negotiation can be performed as part of the
security protocol handshake, thus there is no need to perform another
multistream-selection negotiation for multiplexer negotiation.

If the client and server agree upon the common multiplexer to be used, then the
result of the multiplexer negotiation is used as the selected stream
multiplexer. If no agreement is reached upon by the client and server then the
connection upgrade process MUST fall back to the multistream-selection protocol
to negotiate the multiplexer.

### Multiplexer negotiation over TLS

When the security protocol selected by the upgrader is TLS, the [ALPN]
extension of TLS handshake is used to select the multiplexer.

The ALPN TLS extension allows the client to send a list of supported application
protocols as part of the TLS ClientHello message.  The server chooses
a protocol and sends the selected protocol as part of the TLS
ServerHello message.

For the purpose of multiplexer negotiation, the protocol IDs of the stream 
multiplexers are sent, followed by "libp2p".
    An example list:

    [ "/yamux", "/mplex", "libp2p" ]

The multiplexer list is ordered by the client's preference, with the most preferred
multiplexer at the beginning. The server SHOULD pick the first protocol from the
list that it supports.

The "libp2p" protocol code MUST always be the last item in the multiplexer list.
According to [tls], nodes that don't implement the optimization described in this document
use "libp2p" for their ALPN. If "libp2p" is the result of the ALPN process, nodes MUST use
multistream negotiation of the stream multiplexer as described in [connections].

### Multiplexer negotiation over Noise

The libp2p Noise Specification allows the Noise handshake messages to carry
early data. [Noise-Early-Data] is carried in the second and third message of
the XX handshake pattern as illustrated in the following message sequence chart.
The second message carries early data in the form of a list of multiplexers
supported by the responder, ordered by preference. The initiator sends its
supported multiplexer list in the third message of the handshake process. It
MAY choose a single multiplexer from the responder's list and only send that
value.

The multiplexer to use is determined by picking the first item from the
initiator's list that both parties support.

Example: Noise handshake between peers that have a mutually supported
multiplexer.
    Initiator supports: [ "/yamux", "/mplex" ]
    Responder supports: [ "/mplex", "/yamux" ]

    XX:
    -> e
    <- e, ee, s, es, [ "/mplex", "/yamux" ] 
    -> s, se, [ "/yamux", "/mplex" ] 

    Negotiated: "/yamux"

Example: Noise handshake between peers that don't have mutually supported
multiplexers.
    Responder supports: [ "/mplex" ]
    Initiator supports: [ "yamux" ]

    XX:
    -> e
    <- e, ee, s, es, [ "/mplex" ]
    -> s, se, [ "yamux" ]
    
    After handshaking is done, early data processing will find no mutually
    supported multiplexer, and falls back to multistream-selection protocol.

The multiplexer selection logic SHOULD run after the Noise handshake has
finished mutual authentication of the peers to enhance security.

The format of the early data is specified in [Noise-handshake-payload]


## Privacy

The list of multiplexers carried in the TLS ALPN extension field is part of the
ClientHello message which is not encrypted. Using this optimiziation therefore
exposes the list of supported multiplexers to an on-path observer. This leak can
be considered insignificant, since a libp2p node reveals its list of supported
multiplexers to any node that connects to it.

The NoiseExtensions sent in the Noise handshake is sent after the peers have 
established a shared key, so an on-path observer won't be able to obtain the
list of multiplexers.


## Alternative options considered

Instead of ALPN for multiplexer selection to reduce RTT, other options such as
TLS extension and X.509 extension are considered. The pros and cons are explored
and the discussion details can be found at [#454].



[#426]: https://github.com/libp2p/specs/issues/426
[connections]: https://github.com/libp2p/specs/tree/master/connections
[sequence-chart]: https://github.com/libp2p/specs/tree/master/connections#upgrading-connections
[ALPN]: https://datatracker.ietf.org/doc/html/rfc7301
[Noise-Early-Data]: https://github.com/libp2p/specs/tree/master/noise#the-libp2p-handshake-payload
[ECH]: https://datatracker.ietf.org/doc/draft-ietf-tls-esni/
[handshake-payload]: https://github.com/libp2p/specs/tree/master/noise#the-libp2p-handshake-payload
[#454]: https://github.com/libp2p/specs/issues/454
[Noise-handshake-payload]: https://github.com/libp2p/specs/blob/b0818fa956f9940a7cdee18198e0daf1645d8276/noise/README.md#libp2p-data-in-handshake-messages

