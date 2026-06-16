# Optimistic Protocol Negotiation <!-- omit in toc -->

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r0, 2026-05-22  |

Authors: [@Devguru-codes]

Interest Group: [@marcopolo], [@marten-seemann]

[@Devguru-codes]: https://github.com/Devguru-codes
[@marcopolo]: https://github.com/MarcoPolo
[@marten-seemann]: https://github.com/marten-seemann

See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Table of Contents <!-- omit in toc -->

- [Overview](#overview)
- [Applicability](#applicability)
- [Wire Format](#wire-format)
  - [Standard Multistream-Select](#standard-multistream-select)
  - [Optimistic Multistream-Select](#optimistic-multistream-select)
- [Prerequisites](#prerequisites)
- [Requirements](#requirements)
  - [Dialer (Initiator) Requirements](#dialer-initiator-requirements)
  - [Listener (Responder) Requirements](#listener-responder-requirements)
- [Known Limitations](#known-limitations)
  - [Protocol Confusion on Negotiation Failure](#protocol-confusion-on-negotiation-failure)
- [Interaction with Inlined Muxer Negotiation](#interaction-with-inlined-muxer-negotiation)
- [Implementation References](#implementation-references)

## Overview

Also known as "lazy multistream-select" or "lazy negotiation".

In standard [multistream-select][mss] negotiation, the dialer (initiator) sends
its protocol proposal and **waits** for the listener (responder) to echo the
protocol ID back before sending any application data. This costs one round
trip before application data can flow.

Optimistic protocol negotiation eliminates this round trip by allowing the dialer
to send the multistream-select header, the protocol proposal, **and** the initial
application data all at once, without waiting for the listener's echo response.
The listener's echo response arrives asynchronously while the dialer is already
sending application data.

This optimization is critical for latency-sensitive use cases such as
[Kademlia DHT][kad-dht] operations, which use a "one stream per RPC" pattern
and would otherwise pay the full round-trip cost on every request.

## Applicability

Optimistic protocol negotiation can be applied in two contexts:

1. **Stream-level negotiation** (primary use case): When opening a new stream
   over an existing connection, the dialer can optimistically propose a protocol
   and begin sending application data immediately. This is the most common use
   case and provides the greatest latency benefit for protocols that use
   short-lived streams (e.g., DHT RPCs, Bitswap requests).

2. **Connection upgrade negotiation**: When negotiating security or stream
   multiplexing protocols during [connection establishment][connections]. This
   use case is less common because [inlined muxer negotiation][inlined-muxer]
   already reduces the round-trip cost of the connection upgrade process.

## Wire Format

The wire format for individual messages is unchanged from standard
[multistream-select][mss].

### Standard Multistream-Select

In the standard (non-optimistic) flow, the dialer waits for the listener's echo
before sending application data:

```
Dialer                                  Listener
  |                                        |
  |--- /multistream/1.0.0 ---------------->|
  |--- /my-protocol/1.0.0 ---------------->|
  |                                        |
  |<-- /multistream/1.0.0 -----------------|
  |<-- /my-protocol/1.0.0 ---- (echo) ----|  <- Dialer waits for echo
  |                                        |
  |--- [application data] --------------->|  <- Only then sends data
  |                                        |
```

**Cost**: 1 round trip before application data flows.

### Optimistic Multistream-Select

In the optimistic flow, the dialer sends the multistream header, protocol
proposal, and application data without waiting:

```
Dialer                                  Listener
  |                                        |
  |--- /multistream/1.0.0 ---------------->|
  |--- /my-protocol/1.0.0 ---------------->|
  |--- [application data] ---------------->|  <- Sent immediately
  |                                        |
  |<-- /multistream/1.0.0 -----------------|  <- Echo arrives later
  |<-- /my-protocol/1.0.0 -----------------|
  |                                        |
```

**Cost**: 0 round trips. Application data is delivered to the listener
alongside the protocol proposal. The listener processes the negotiation and then
delivers the application data to the protocol handler.

## Prerequisites

Optimistic protocol negotiation is inherently optimistic. The dialer sends
application data before receiving confirmation that the listener supports the
requested protocol. If the listener does not support the protocol, the
negotiation will fail, and the application data sent optimistically will be
wasted.

To minimize the risk of failed negotiations, dialers typically use the
[identify protocol][identify] to learn which protocols a peer supports before
using optimistic negotiation. The `protocols` field of the identify message
(see [identify spec][identify]) contains the list of protocols the remote peer
supports.

However, it is important to note that this is still *optimistic* — a peer's
supported protocols can change dynamically at any time (e.g., via
[identify/push][identify-push] updates, or due to configuration changes).
In practice, protocol support is stable enough that optimistic negotiation
succeeds in the vast majority of cases.

Implementations MAY skip optimistic negotiation when no prior protocol
knowledge is available.

## Requirements

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be
interpreted as described in [RFC 2119].

### Dialer (Initiator) Requirements

1. **Ordering**: Implementations MUST send the multistream protocol ID
   (`/multistream/1.0.0`) and the application protocol ID before any
   application data on the stream, without waiting for responses between
   them.

2. **Handshake completion on close**: Implementations SHOULD finish reading the
   handshake response before closing the stream. If the dialer writes
   application data and then closes the stream before the listener has echoed
   back the protocol ID, the listener's echo write may fail on a closed stream,
   potentially causing the listener to reset the stream and discard data that
   was already received.

   If the application does not need to read any data from the stream (i.e., it
   is a pure write/fire-and-forget pattern), the implementation MAY skip reading
   the handshake response.

3. **Prior knowledge**: Implementations MAY use optimistic negotiation without
   prior knowledge that the peer supports the requested protocol. However,
   using optimistic negotiation without prior knowledge (e.g., via a preceding
   [identify][identify] exchange) risks triggering the protocol confusion issue
   described in [Known Limitations](#known-limitations).

### Listener (Responder) Requirements

1. **Tolerating echo write failures**: Implementations SHOULD ignore write
   errors when echoing back the protocol ID during negotiation. With optimistic
   negotiation, the dialer may have already closed its write side of the stream
   after sending application data. The echo write failing does not indicate a
   negotiation failure — the negotiated protocol has already been identified.

2. **Stream delivery**: Implementations MUST still deliver the stream to the
   application protocol handler even if the echo write fails. The handler can
   then `Read()` any application data the dialer already sent.

## Known Limitations

### Protocol Confusion on Negotiation Failure

There is a known soundness issue with optimistic multistream-select that arises
when the negotiation **fails** — i.e., the listener does not support the
proposed protocol.

Consider the following scenario:

- Peer A supports `protocolA`
- Peer B supports `protocolB` (but **not** `protocolA`)

Peer A sends optimistically:

```
<len>/multistream/1.0.0\n <len>/protocolA/1.0.0\n
```

Then immediately sends application data that happens to look like a valid
multistream-select protocol proposal:

```
<len>/protocolB/1.0.0\n [other data]
```

Peer B does not support `protocolA`, so it responds with `"na"` and reads the
next message. It sees `/protocolB/1.0.0` — which it **does** support — and
interprets it as a new protocol proposal. It echoes back `/protocolB/1.0.0` and
starts interpreting `[other data]` as `protocolB` traffic.

**Result**: Peer B is now speaking `protocolB` with data that was actually
`protocolA` application data. This is a protocol confusion vulnerability.

This issue is extensively documented in [go-multistream#20]. As stated by the
original author:

> "I don't know of a good fix that won't break everything (without upping
> the version and adding a mandatory round trip)."

**Mitigations**:

- The prerequisite of having prior protocol knowledge (via identify) makes this
  scenario unlikely in practice, since the dialer would not propose a protocol
  the listener does not support.
- Application protocol designers SHOULD ensure that their wire format cannot be
  confused with multistream-select messages (i.e., application data should not
  begin with a valid varint-prefixed, newline-terminated protocol path).
- Implementations SHOULD log or track negotiation failures to detect potential
  protocol confusion.

## Interaction with Inlined Muxer Negotiation

For connection upgrades, [inlined muxer negotiation][inlined-muxer] is
preferred as it already eliminates the extra round trip for muxer selection
during the security handshake.

## Implementation References

The following implementation artifacts motivated and informed this specification:

| Reference | Description |
|-----------|-------------|
| [go-multistream#115] | Fix: finish reading handshake on `lazyConn` close |
| [go-multistream#87] | Fix: ignore error if can't write back echoed protocol |
| [go-multistream#20] | Issue: lazy negotiation soundness problem (protocol confusion) |
| [go-libp2p#3038] | Bug: WebTransport `StopSending` error caused by incomplete lazy handshake |

[mss]: https://github.com/multiformats/multistream-select
[uvarint]: https://github.com/multiformats/unsigned-varint
[connections]: https://github.com/libp2p/specs/tree/master/connections
[inlined-muxer]: ./inlined-muxer-negotiation.md
[identify]: ../identify/README.md
[identify-push]: ../identify/README.md#identifypush
[kad-dht]: ../kad-dht/README.md
[noise]: ../noise/README.md
[tls]: ../tls/tls.md
[go-libp2p]: https://github.com/libp2p/go-libp2p
[rust-libp2p]: https://github.com/libp2p/rust-libp2p
[go-multistream#115]: https://github.com/multiformats/go-multistream/pull/115
[go-multistream#87]: https://github.com/multiformats/go-multistream/pull/87
[go-multistream#20]: https://github.com/multiformats/go-multistream/issues/20
[go-libp2p#3038]: https://github.com/libp2p/go-libp2p/issues/3038
[RFC 2119]: https://www.ietf.org/rfc/rfc2119.txt
