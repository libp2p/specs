# Identify v2.0.0

| Lifecycle Stage | Maturity Level | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 1A              | Draft          | Active | r0, 2021-07-16  |

Authors: [@thomaseizinger]

Interest Group: [@yusefnapora], [@tomaka], [@richardschneider], [@Stebalien], [@bigs], [@vyzo]

[@thomaseizinger]: https://github.com/bigs
[@vyzo]: https://github.com/vyzo
[@yusefnapora]: https://github.com/yusefnapora
[@tomaka]: https://github.com/tomaka
[@richardschneider]: https://github.com/richardschneider
[@Stebalien]: https://github.com/Stebalien
[@bigs]: https://github.com/bigs

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Table of Contents

- [Identify v2.0.0](#identify-v200)
    - [Table of Contents](#table-of-contents)
    - [Overview](#overview)
        - [`identify`](#identify)
        - [`identify/push`](#identifypush)
    - [The Identify Message](#the-identify-message)
        - [Differences to `/ipfs/id/1.0.0`](#differences-to-ipfsid100)
        - [signedPeerRecords](#signedpeerrecords)
        - [observedAddr](#observedaddr)
        - [protocols](#protocols)
        - [protocolVersion](#protocolversion)
        - [agentVersion](#agentversion)

## Overview

Version v2.0.0 of the identify protocol brings two minor changes.

1. The use of a new protocol identifier in the spirit of decoupling libp2p protocols from ipfs.
2. Suppport for signed peer records instead of plain addresses.

Same as for v1.0.0, there are two variations of the identify protocol, `identify` and `identify/push`.
The behaviour is equivalent to v1.0.0.

### `identify`

The `identify` protocol has the protocol id `/p2p/id/2.0.0`, and it is used
to query remote peers for their information.

### `identify/push`

The `identify/push` protocol has the protocol id `/p2p/id/push/2.0.0`, and it is used
to inform known peers about changes that occur at runtime.

## The Identify Message

```protobuf
message Identify {
  optional string protocolVersion = 4;
  optional string agentVersion = 5;
  repeated bytes signedPeerRecord = 1;
  optional bytes observedAddr = 3;
  repeated string protocols = 2;
}
```

### Differences to `/ipfs/id/1.0.0`

- `listenAddrs` is replaced with `signedPeerRecord`
- `publicKey` is removed because it is embedded within `signedPeerRecord`

### signedPeerRecord

A signed peer record that certifies the addresses a peer is listening on.

### protocols

Unchanged from `/ipfs/id/1.0.0`.

### observedAddr

Unchanged from `/ipfs/id/1.0.0`.

### protocolVersion

Unchanged from `/ipfs/id/1.0.0`.

### agentVersion

Unchanged from `/ipfs/id/1.0.0`.

## Behaviour

The public key embedded in the signed peer record MUST match the public key of
the connected peer as defined through the security protocol (e.g. noise).
