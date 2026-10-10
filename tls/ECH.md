# ECH

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r0, 2026-07-01  |

Authors: [@marcopolo]

Interest Group: [@sukunrt], `todo`

[@marcopolo]: https://github.com/marcopolo
[@sukunrt]: https://github.com/sukunrt

## Overview

This document specifies minor changes to the [libp2p TLS Handshake](./tls.md) to
enable support for [RFC 9849]: TLS Encrypted Client Hello. The primary benefit
is to make identifying libp2p connections harder to passive network observers by
hiding the "libp2p" ALPN in the encrypted ClientHelloInner.

## Changes to the libp2p TLS Handshake

### Outer Handshake

The outer handshake MUST NOT be a libp2p TLS handshake.

#### ALPN

Unless an ALPN is explicitly specified by the application for the connection,
client implementations SHOULD set it to `http/1.1` for TCP connections and `h3`
for QUIC connections. The ALPN MUST NOT include `libp2p` or the muxer protocol
IDs used by [inlined muxer negotiation].

#### Authenticated Rejection

In RFC 9849, clients can only use the server provided `retry_configs` if the
outer handshake authenticates successfully with the given
ECHConfig.contents.public_name. This means that if servers wish to support the
`retry_configs` fallback they MUST use a valid domain name and hold the
corresponding Server Certificate. This is the retry mechanism in RFC 9849;
there is nothing libp2p specific about this.

If the server does not have a valid public_name and certificate, the client can
only fail the connection.

### Inner Handshake

The encrypted ClientHelloInner performs the standard libp2p TLS Handshake. The
ALPN MUST conform to the libp2p TLS Handshake.

## Server Key Rotation

Servers SHOULD rotate their keys once a month, and keep the prior ECH Config
keys around for 1 week to assist stale clients.

## Client ECH Config Caching

Clients SHOULD cache the ECHConfigList for no more than 48 hours. Note that a
server can provide an updated ECHConfigList upon connection via an identify
message.

## `/ech` in the multiaddr

The `/ech` component SHOULD appear after the `/tls` or `/quic-v1` component.
Servers use this multiaddr to advertise ECH support and their ECHConfigList.

## Caller Provided ECHConfigList

Implementations SHOULD allow users to supply an ECHConfigList when dialing.

<!-- References -->

[RFC 9849]: https://www.rfc-editor.org/info/rfc9849/
[inlined muxer negotiation]: ../connections/inlined-muxer-negotiation.md
