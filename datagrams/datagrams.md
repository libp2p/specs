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
- [Encoding Datagrams](#encoding-datagrams)
- [Datagrams on top of a multiplexed stream on top of TCP](#datagrams-on-top-of-a-multiplexed-stream-on-top-of-tcp)
- [Datagrams with WebRTC](#datagrams-with-webrtc)

## Introduction

This specification defines the datagrams on libp2p, which enable the
transmission of MTU-sized, unreliable, and low latency messages between peers.

TODO write more about the tradeoffs here as well as the kinds of applications that would benefit from using datagrams.

## Native support at the transport level

Some libp2p transports natively support datagrams, such as QUIC and WebTransport. libp2p implementations MUST use the native datagram support to send datagrams.

QUIC has an Unreliable Datagram Extension [RFC 9221]
WebTransport supports Datagrams though HTTP Datagrams [WebTransport draft RFC](https://www.ietf.org/archive/id/draft-ietf-webtrans-http3-12.html#name-datagrams)

## Encoding Datagrams

The libp2p datagram encoding introduces minimal framing overhead to application payloads. Each datagram MUST be encoded with the following structure to ensure proper protocol identification and version compatibility.

The datagram frame consists of the following components:

| Field Name         | Data Type        | Length (bits) | Description                                          |
| ------------------ | ---------------- | ------------- | ---------------------------------------------------- |
| version            | unsigned integer | 8             | Protocol version identifier                          |
| protocol id length | [uvarint]        | 8..72         | Length of the protocol identifier field              |
| protocol id        | byte sequence    | variable      | Protocol identifier as defined by protocol id length |
| application data   | byte sequence    | variable      | Application payload                                  |

The complete datagram frame is constructed as follows:

```
version || protocol id length || protocol id || application data
```

Where "||" denotes byte concatenation.

The version field provides extensibility for future encoding modifications while maintaining backward compatibility. Implementations MUST verify the version field before processing the remainder of the datagram.

## Datagrams on top of a multiplexed stream on top of TCP

This is currently not specified.

## Datagrams with WebRTC

This is currently not specified.

[uvarint]: https://github.com/multiformats/unsigned-varint
[RFC 9221]: https://www.rfc-editor.org/rfc/rfc9221
