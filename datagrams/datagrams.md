# Datagrams in libp2p

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r0, 2025-05-23  |

Authors: [@marcopolo]

Interest Group: [@sukunrt], [@jxs], [@raulk]

[@marcopolo]: https://github.com/marcopolo
[@sukunrt]: https://github.com/sukunrt
[@jxs]: https://github.com/jxs
[@raulk]: https://github.com/raulk

See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Table of Contents

- [Introduction](#introduction)
- [Native support at the transport level](#native-support-at-the-transport-level)
- [Datagrams on QUIC](#datagrams-on-quic)
  - [Encoding](#encoding)
- [Datagrams on WebTransport](#datagrams-on-webtransport)
- [Datagrams on top of a multiplexed stream on top of TCP](#datagrams-on-top-of-a-multiplexed-stream-on-top-of-tcp)
- [Datagrams with WebRTC](#datagrams-with-webrtc)

## Introduction

This specification defines libp2p datagrams, which enable the transmission of
MTU-sized, unreliable, and low latency messages between peers.

TODO write more about the tradeoffs here as well as the kinds of applications that would benefit from using datagrams.

## Native support at the transport level

Some libp2p transports natively support datagrams, such as QUIC and
WebTransport. libp2p implementations MUST use the native datagram support to
send datagrams.

- QUIC has an Unreliable Datagram Extension [RFC 9221].
- WebTransport supports Datagrams though HTTP Datagrams [WebTransport draft RFC](https://www.ietf.org/archive/id/draft-ietf-webtrans-http3-12.html#name-datagrams)

## Datagrams on QUIC

Each datagram flow MUST be associated with a control stream. A datagram flow is
defined as a logical flow of datagrams for a specific application protocol. A
control stream is a QUIC bidirectional stream that has negotiated the application
protocol ID. The control stream MUST stay open for the duration of the datagram
flow. Implementation MAY create the control stream and start sending datagrams
at once.

There is currently no other use for the control stream besides negotiating the
application protocol ID.

Receipt of a QUIC DATAGRAM frame whose payload is too short to allow parsing the
Control Stream ID field MUST be treated as a connection error of type
PROTOCOL_VIOLATION (0x1003).

libp2p datagrams MUST NOT be sent unless the control stream's send side is
open. If a datagram is received after the corresponding stream's receive side is
closed, the received datagrams MUST be silently dropped.

If a libp2p datagram is received and its Control Stream ID field maps to a
stream that has not yet been created, the receiver SHALL either drop that
datagram silently or buffer it temporarily (on the order of a round trip) while
awaiting the creation of the corresponding stream.

If a libp2p datagram is received and its Control Stream ID field maps to a
stream that cannot be created due to client-initiated bidirectional stream
limits, it MUST be treated as a connection error of type PROTOCOL_VIOLATION
(0x1003).

### Encoding

Each libp2p datagram SHALL be encoded with the following structure.

| Field Name       | Data Type     | Length (bits) | Description                                                           |
| ---------------- | ------------- | ------------- | --------------------------------------------------------------------- |
| Control StreamID | [QUIC varint] | 8..64         | The stream ID of the associated control stream for this datagram flow |
| Application Data | byte sequence | variable      | Application payload                                                   |

## Datagrams on WebTransport

libp2p datagrams on WebTransport behave the same as libp2p datagrams on QUIC.
However, the application data may be further limited by the overhead of HTTP
Datagram's Quarter Stream ID field.

In the future, a separate spec may be able to remove this overhead.

## Datagrams on top of a multiplexed stream on top of TCP

This is currently not specified.

## Datagrams with WebRTC

This is currently not specified.

[RFC 9221]: https://www.rfc-editor.org/rfc/rfc9221
[QUIC varint]: https://www.rfc-editor.org/rfc/rfc9000.html#name-variable-length-integer-enc
