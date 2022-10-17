# Stream multiplexer negotiation in security handshake


| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r1, 2022-09-07  |

Authors: [@julian88110]

Interest Group: [@marten-seemann], [@marcopolo], [@mxinden]

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
                - [Early data specification](#early-data-specification)
    - [Cross version support](#cross-version-support)
        - [TLS case](#tls-case)
        - [Noise case](#noise-case)
    - [Security](#security)
    - [Protocol coupling](#protocol-coupling)
    - [Alternative options considered](#alternative-options-considered)

## Overview

This document describes an improvement on the stream multiplexer negotiation
process. The goal of the improvement is to reduce the number of RTTs that takes
to negotiate the stream multiplexer for a transport that does not natively
support stream multiplexing. The solution relies on the ability of the security
protocol's handshake process to negotiate higher level protocols, which enables
the multiplexer negotiation to be carried out along with the security protocol
handshake. With this improvement, the negotiation of the stream multiplexer
doesn't consume any additional roundtrips.

This feature aggregates the multiplexer negotiation function and security
handshake function. It introduces coupling between those two functions.

The improved multiplexer negotiation approach MUST be interoperable with
pervious libp2p versions which do not support this improvement.


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

## Improved multiplexer negotiation 

The security protocol's ability of supporting higher level abstract protocol
negotiation (for example, TLS's support of ALPN, and Noise's support of Early
Data) makes it possible to collapse the step 2 and step 3 in the previous
section into one step. Multiplexer negotiation can be performed as part of the
security protocol handshake, thus there is no need to perform another mutistream
-selection negotiation for multiplexer negotiation.

In order to achieve the above stated goal, each candidate multiplexer will be
represented by a protocol name/code, and the candidate multiplexers are supplied
to the security protocol's handshake process as a list of protocol names.

If the client and server agree upon the common multiplexer to be used, then the
result of the multiplexer negotiation is used as the selected stream
multiplexer. If no agreement is reached upon by the client and server then the
connection upgrade process MUST fall back to the multistream-selection protocol
to negotiate the multiplexer.


### Multiplexer negotiation over TLS

When the security protocol selected by the upgrader is TLS, the [ALPN]
extension of TLS handshake is used to select the multiplexer.

   With ALPN, the client sends the list of supported application
   protocols as part of the TLS ClientHello message.  The server chooses
   a protocol and sends the selected protocol as part of the TLS
   ServerHello message.  The application protocol negotiation can thus
   be accomplished within the TLS handshake, without adding network
   round-trips, and allows the server to associate a different
   certificate with each application protocol, if desired.

For the purpose of multiplexer negotiation, the types of multiplexers are coded
as protocol names in the form of a list of strings, and inserted in the ALPN
extension field.
    An example list:

    ["/yamux/1.0.0", "/mplex/6.7.0", "libp2p"]

The multiplexer list is ordered by preference, with the most preferred
multiplexer at the beginning. The "libp2p" protocol code MUST always be the
last item in the multiplexer list . See [#tls-case] for details on the special
"libp2p" protocol code.

The server SHOULD choose the supported protocol by going through its preferred
protocol list and search if the protocol is supported by the client too. If no
mutually supported protocol is found the TLS handshake will fail.

If the selected item from the multiplexer list is "libp2p" then the multiplexer
negotiation process returns an empty result, and the multistream-selection
protocol MUST be run to negotiate the multiplexer.


### Multiplexer negotiation over Noise

The libp2p Noise Specification allows the Noise handshake process to carry
early data. [Noise-Early-Data] is carried in the second and third message of
the XX handshake pattern as illustrated in the following message sequence chart.
The second message carries early data in the form of a list of multiplexers
supported by the responder, ordered by preference. The initiator sends its
supported multiplexer list in the third message to the responder.

For security reasons the early data is not processed until the Noise handshake
is finished. After the Noise handshake process is fully done, the initiator and
responder will both process the received early data and select the multiplexer
to be used. They both iterate through
the responder's preferred multiplexer list in order, and if the multiplexer is
also supported by the initiator, that multiplexer is selected. If no mutually
supported multiplexer is found, the multiplexer negotiation process MUST fall
back to multistream-selection protocol.

Example: Noise handshake between peers that have a mutually supported
multiplexer.
    Initiator supports: ["/yamux/1.0.0", "/mplex/6.7.0"]
    Responder supports: ["/mplex/6.7.0", "/yamux/1.0.0"]

    XX:
    -> e
    <- e, ee, s, es, ["/mplex/6.7.0", "/yamux/1.0.0"] 
    -> s, se, ["/yamux/1.0.0", "/mplex/6.7.0"] 

    After handshake is done, both parties can arrive on the same conclusion
    and select "/mplex/6.7.0" as the multiplexer to use.

Example: Noise handshake between peers that don't have mutually supported
multiplexers.
    Responder supports: ["/mplex/6.7.0"]
    Initiator supports: ["yamux/1.0.0"]

    XX:
    -> e
    <- e, ee, s, es, ["/mplex/6.7.0"]
    -> s, se, ["yamux/1.0.0"]
    
    After handshaking is done, early data processing will find no mutually
    supported multiplexer, and falls back to multistream-selection protocol.

The multiplexer selection logic is run after the Noise handshake has finished
mutual authentication of the peers. The format of he early data is specified in
the protobuf definition found in the [Early-data-specification] section.

The details of the early data message format can be find in
[Noise-handshake-payload]

### TLS case

In the current version of libp2p, the ALPN extension field is populated with a
key "libp2p". By appending the key of "libp2p" to the end of the supported
multiplexer list, the TLS handshaking process is not broken when peers run
different versions of libp2p, because the minimum overlap of the peer's
supported multiplexer sets is always satisfied. When one peer runs the old
version and the other peer runs the version that supports this feature, the
negotiated protocol is "libp2p".

In the case "libp2p" is the result of TLS ALPN, an empty result MUST be
returned to the upgrade process to indicate that no multiplexer was selected.
And the upgrade process MUST fall back to the multistream-selection protocol to
to negotiate the multiplexer to be selected. This fallback behavior ensures
backward compatibility with previous versions that do not support the feature
specified by this document.

### Noise case

The existing version of libp2p Noise handshake carries empty early data. When a
version that supports this feature talks to an older version which does not
support this feature, the multiplexer selection process on the new version runs
against an empty string and will return empty multiplexer selection result.

In the case an empty multiplexer selection result is returned, the upgrade process
MUST fall back to the multistream-selection protocol to select the multiplexer.
This fallback behavior ensures backward compatibility with previous versions that
do not support this sepcification.

## Security

The multiplexer list carried in TLS ALPN extension field is part of the
ClientHello message which is not encrypted. This feature will expose the
supported multiplexers in plain text, but this is not a weakening of security
posture. In the future when [ECH] is ready the multiplexer info can be
protected too.

The early data in Noise handshake is only sent after the peers establish a
shared key, in the second and third handshake messages in the XX pattern. So
the early data is encrypted and the multiplexer info carried over is protected.
These is no security weakening in this case either.


## Protocol coupling

This feature aggregates the multistream-selecion function and security
handshake function. From function separation point of view, it introduces
coupling between different functions. But the argument is that in the case of
libp2p, the multiplexer and security are always needed at the same time, and
it is a small price to pay to gain efficiency by reducing one RTT.


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







