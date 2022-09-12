# Muxer selection in security handshake


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

- [Muxer selection in security handshake](#Muxer-selection-in-security-handshake)
    - [Table of Contents](#table-of-contents)
    - [Overview](#overview)
    - [Design])(#design)
        - [Current connection upgrade process](#current-connection-upgrade-process)
        - [Improved muxer selection](#improved-muxer-selection)
            - [Muxer selection over TLS](#muxer-selection-over-tls)
            - [Muxer selection over Noise](#muxer-selection-over-noise)
                - [Early data specification](#early-data-specification)
    - [Cross version support](#cross-version-support)
        - [TLS case](#tls-case)
        - [Noise case](#noise-case)
    - [Security](#security)
    - [Protocol coupling](#protocol-coupling)

## Overview

This document discribes an imporvement on the connection upgrade process. The
goal of the improvement is to reduce the number of RTTs that takes to select the
muxer of a connection. The solution relies on the ability of the security
protocol's handshake process to negotiate higher level protocols, which enables
the muxer selection to be carried out along with security protocol handshake.
The proposed solution saves the RTT of multistream selection for muxers.

For more context and the status of this work, please refer to [#426]


## Design

### Current connection upgrade process

The current connection upgrade process is described in detail in [connections].
As shown in this [sequence-chart], after a network connection is established,
the following will happen to upgrade the conntection to a capable connection.

1. The multistream-selection protocol is run over the connection to select the
security protocol to be used.
2. The selected security protocol performs handshaking and establishs a secure
tunnel
3. The multistream-selection protocol then will run again for muxer selection.
4. Connection then is upgraded to a capable connection by the selected muxer.


## Improved muxer selection

The security protocol's ability of supporting higher level abstract protocol
negotiation (for example, TLS's support of ALPN, and Noise's support of Early
Data) makes it possible to collapse the step 2 and step 3 in the previous
section into one step. Muxer selection can be performed as part of the security
protocol handshake, thus there is no need to perform another mutistream
-selection negotiation for muxer selection.

In order to achieve the above stated goal, each candidate muxer will be
represented by a protocol name/code, and the candidate muxers are supplied to
the security protocol's handshake process as a list of protocol names.

If the client and server agree upon the common muxer to be used, then the
result of the muxer selection is a muxer code represented by the selected
protocol name. If no agreement is reached upon by the client and server
then an empty muxer code is returned and the connection upgrade process
MUST fall back to the multistream-selection protocol to negotiate the muxer.


### Muxer selection over TLS

When the security protocol selected by the upgrader is TLS, the [ALPN]
extesion of TLS handshake is used to select the muxer.

   With ALPN, the client sends the list of supported application
   protocols as part of the TLS ClientHello message.  The server chooses
   a protocol and sends the selected protocol as part of the TLS
   ServerHello message.  The application protocol negotiation can thus
   be accomplished within the TLS handshake, without adding network
   round-trips, and allows the server to associate a different
   certificate with each application protocol, if desired.

For the purpose of muxer selection, the types of muxers are coded as protocol
names in the form of a list of strings, and inserted in the ALPN "NextProtos"
field. An example list as following:

    ["yamux/1.0.0", "mplux", "libp2p"]

The NextProtos list is ordered by preference, with the most prefered muxer at
the beginning. The "libp2p" protocol code MUST always be the last item in the
ALPN NextProtos list.

The server chooses the supported protocol by going through its prefered
protocol list and searchs if the protocol is supported by the client too. if no
mutually supported protcol is found the TLS handshake will fail.

If the selected NextProto is "libp2p" then the muxer selection process returns
an empty result, and the multistream-selection protocol MUST be run to negotiate
the muxer.


### Muxer selection over Noise

The libp2p Noise implementation allows the Noise handshake process to carry
early data. [Noise-Early-Data] is carried in the second and third message of
the handshake pattern as illustrated in the following message sequence chart.

    XX:
    -> e
    <- e, ee, s, es, _early-data_
    -> s, se, _early-data_

At the end of the handshake pattern, both the client and server have received
the peer's early data. The Noise protocol does not perform the protocol
selection as TLS does, rather it just delivers the early data to handshaking
peers.

The muxer selection logic runs out of the Noise handshake process, relying on
the early data exchanged during the handshake. The early data is delivered in
the form of a byte string in the second and third message of the XX handshake
pattern. 
 
The early data for this purpose is specified in the protobuf in the
[Early-data-specification] section. The muxers are ordered by preference, with
the most prefered muxer at the beginning.

After the Noise handshake, the client and server run the muxer selection
process with the same logic. Each side will go through the server's early
data from most prefered to lest prefered muxer, and if the muxer is in the
client's early data list, that muxer is selected. The process guarantees that
both the client and server reaches at the same conclusion of muxer slection.

If the muxer selection process does not find any mutually supported muxer, for
example, in the case that one early data string is empty, then an empty muxer
selection result is returned, and multistream-selection MUST be performed.

#### Early data specification

The early data message is encoded in the "protobuf2" syntax as shown in the
following. The protobuf definition is an extension to [handshake-payload]. The
existing byte array early data (the "data" field) will be replaced by a
structured EarlyData schema.

 (TBD: verify backward compatiblity)

```protobuf
syntax = "proto2";

message EarlyData {
    message Muxer {
        oneof Muxer {
            string name = 1;
        }
    }
    repeated Muxer muxers = 2;
}

message NoiseHandshakePayload {
	bytes identity_key = 1;
	bytes identity_sig = 2;
	EarlyData early_data = 3;
}
```


## Cross version support

The improved muxer selection approach MUST be interoperable with pervious
libp2p versions which do not support this improved approach.

### TLS case

In the current version of libp2p, the "NextProtos" field is populated with a
key "libp2p". By appending the key of "libp2p" to the end of the supported
muxer list, the TLS handshaking process is not broken when peers run different
versions of libp2p, because the minimum overlap of the peer's NextProtos sets
is always satisfied. When one peer runs the old version and the other peer runs
the version that supports this feature, the negotiated protocol is "libp2p".

In the case "libp2p" is the result of TLS ALPN, an empty result MUST be
returned to the upgrade process to indicate that no muxer was selected. And the
upgrade process MUST fall back to the multistream-selection protocol to
to negotiate the muxer to be selected.

### Noise case

The existing version of libp2p Noise handshake carries empty early data. When a
version that supports this feature talks to an older version which does not
support this feature, the muxer selection process on the new version runs
against an empty string and will return empty muxer selection result.

In the case an empty muxer selection result is returned, the upgrade process
MUST fall back to the multistream-selection protocol to select the muxer.

## Security

The muxer list carried in TLS NextProtos field is part of the ClientHello
message which is not encrypted. This feature will expose the supported muxers
in plain text, but this is not a weakening of securiy posture. In the fuure
when [ECH] is ready the muxer info can be protected too.

The early data in Noise handshake is only sent afer the peers establish a
shared key, in the second and third handshake messages in the XX pattern. So
the early data is encrypted and the muxer info carried over is protected.
These is no security weakening in this case either.


## Protocol coupling

This feature aggregates the multistream-selecion function and security
handshake function. From function separation point of view, it introduces
coupling between different functions. But the argument is that in the case of
libp2p, the muxer and security are always needed at the same time, and it is a
small price to pay to gain efficiency by ruducing one RTT.



[#426]: https://github.com/libp2p/specs/issues/426
[connections]: https://github.com/libp2p/specs/tree/master/connections
[sequence-chart]: https://github.com/libp2p/specs/tree/master/connections#upgrading-connections
[ALPN]: https://datatracker.ietf.org/doc/html/rfc7301
[Noise-Early-Data]: https://github.com/libp2p/specs/tree/master/noise#the-libp2p-handshake-payload
[ECH]: https://datatracker.ietf.org/doc/draft-ietf-tls-esni/
[handshake-payload]: https://github.com/libp2p/specs/tree/master/noise#the-libp2p-handshake-payload







