# Identify v1.0.0

> The identify protocol is used to exchange basic information with other peers
> in the network, including addresses, public keys, and capabilities.

| Lifecycle Stage | Maturity Level | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 3A              | Recommendation | Active | r2, 2025-09-12  |

Authors: [@vyzo]

Interest Group: [@yusefnapora], [@tomaka], [@richardschneider], [@Stebalien], [@bigs], [@lidel]

[@vyzo]: https://github.com/vyzo
[@yusefnapora]: https://github.com/yusefnapora
[@tomaka]: https://github.com/tomaka
[@richardschneider]: https://github.com/richardschneider
[@Stebalien]: https://github.com/Stebalien
[@bigs]: https://github.com/bigs
[@lidel]: https://github.com/lidel

See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Table of Contents

- [Identify v1.0.0](#identify-v100)
    - [Table of Contents](#table-of-contents)
    - [Overview](#overview)
        - [`identify`](#identify)
        - [`identify/push`](#identifypush)
    - [The Identify Message](#the-identify-message)
        - [protocolVersion](#protocolversion)
        - [agentVersion](#agentversion)
        - [publicKey](#publickey)
        - [listenAddrs](#listenaddrs)
        - [observedAddr](#observedaddr)
        - [protocols](#protocols)


## Overview

There are two variations of the identify protocol, `identify` and `identify/push`.

### `identify`

The `identify` protocol has the protocol id `/ipfs/id/1.0.0`, and it is used
to query remote peers for their information.

The protocol works by opening a stream to the remote peer you want to query, using
`/ipfs/id/1.0.0` as the protocol id string. The peer being identified responds by returning
an `Identify` message and closes the stream.

### `identify/push`

The `identify/push` protocol has the protocol id `/ipfs/id/push/1.0.0`, and it is used
to inform known peers about changes that occur at runtime.

When a peer's basic information changes, for example, because they've obtained a new
public listen address, they can use `identify/push` to inform others about the new
information.

The push variant works by opening a stream to each remote peer you want to update, using
`/ipfs/id/push/1.0.0` as the protocol id string. When the remote peer accepts the stream,
the local peer will send an `Identify` message and close the stream.

Upon receiving the pushed `Identify` message, the remote peer should update their local
metadata repository with the information from the message. Note that missing fields
should be ignored, as peers may choose to send partial updates containing only the fields
whose values have changed.

## The Identify Message

```protobuf
syntax = "proto2";
message Identify {
  optional string protocolVersion = 5;
  optional string agentVersion = 6;
  optional bytes publicKey = 1;
  repeated bytes listenAddrs = 2;
  optional bytes observedAddr = 4;
  repeated string protocols = 3;
}
```

### protocolVersion

The protocol version identifies the family of protocols used by the peer. The
field is optional but recommended for debugging and statistic purposes.

Previous versions of this specification required connections to be closed on
version mismatch. This requirement is revoked to allow interoperability between
protocol families / networks.

Example value: `/my-network/0.1.0`.

Implementations SHOULD limit the string to 128 runes (Unicode code points) when
displaying or processing this field. When displaying in terminals, logs, or user
interfaces, implementations SHOULD sanitize the string as described in the
[Unicode Sanitization](#unicode-sanitization) section below.

### agentVersion

This is a free-form string, identifying the implementation of the peer.
The usual format is `agent-name/version`, where `agent-name` is
the name of the program or library and `version` is its semantic version.

Implementations SHOULD limit the string to 128 runes (Unicode code points) when
displaying or processing this field. When displaying in terminals, logs, or user
interfaces, implementations SHOULD sanitize the string as described in the
[Unicode Sanitization](#unicode-sanitization) section below.

### publicKey

This is the public key of the peer, marshalled in binary form as specicfied
in [peer-ids](../peer-ids).


### listenAddrs

These are the addresses on which the peer is listening as multi-addresses.

### observedAddr

This is the connection source address of the stream-initiating peer as observed by the peer
being identified; it is a multi-address. The initiator can use this address to infer
the existence of a NAT and its public address.

For example, in the case of a TCP/IP transport the observed addresses will be of the form
`/ip4/x.x.x.x/tcp/xx`. In the case of a circuit relay connection, the observed address will
be of the form `/p2p/QmRelay/p2p-circuit`. In the case of onion transport, there is no
observable source address.

### protocols

This is a list of protocols supported by the peer.

Implementations SHOULD limit each string to 128 runes (Unicode code points) when
displaying or processing these values. When displaying in terminals, logs, or user
interfaces, implementations SHOULD sanitize the strings as described in the
[Unicode Sanitization](#unicode-sanitization) section below.

A node should only advertise a protocol if it's willing to receive inbound
streams on that protocol. This is relevant for asymmetrical protocols. For
example assume an asymmetrical request-response style protocol `foo` where some
clients only support initiating requests while some servers (only) support
responding to requests. To prevent clients from initiating requests to other
clients, which given them being clients they fail to respond, clients should not
advertise `foo` in their `protocols` list.

## Unicode Sanitization

When displaying identify protocol string fields (`protocolVersion`, `agentVersion`,
and `protocols`) in terminals, logs, or user interfaces, implementations SHOULD
sanitize untrusted input from remote peers to prevent display issues and potential
security vulnerabilities.

The following sanitization steps use Unicode General Category values as defined in
[Unicode Standard Annex #44](https://www.unicode.org/reports/tr44/#General_Category_Values)
and follow guidance from [RFC 9839](https://www.rfc-editor.org/rfc/rfc9839.html) on
handling Unicode strings.

Recommended sanitization steps:

1. **Replace control characters** (Unicode category `Cc`: Other, Control) with `U+FFFD` (�) -
   These can cause terminal escape sequences, carriage returns, line feeds, and other
   display disruptions.

2. **Replace format characters** (Unicode category `Cf`: Other, Format) with `U+FFFD` (�) -
   These include RTL/LTR overrides, zero-width characters, and other formatting marks.

3. **Replace surrogate characters** (Unicode category `Cs`: Other, Surrogate) with `U+FFFD` (�) -
   These are invalid in UTF-8 and can cause parsing errors.

4. **Preserve legitimate Unicode** - Keep all other Unicode characters including:
   - Letters, numbers, and symbols from all languages
   - Emojis and other valid Unicode symbols
   - Combining marks and diacritics
   - Private use characters (Unicode category `Co`)

5. **Enforce length limits** - Limit to 128 runes (Unicode code points, not bytes)
   to prevent excessive resource consumption.

Note: These sanitization steps are recommended for display purposes only. The
protocol itself does not restrict the use of Unicode in these fields, allowing
for international support while protecting against display-related security issues.
Per RFC 9839, replacing problematic code points with `U+FFFD` is preferred over
silently deleting them, as deletion is a known security risk.
