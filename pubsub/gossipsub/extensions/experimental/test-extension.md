# Test Extension

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r0, 2025-06-23  |

Authors: [@marcopolo]

Interest Group: @jxs

[@marcopolo]: https://github.com/marcopolo
[@jxs]: https://github.com/jxs

See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Overview

This introduces a minimal extension to Gossipsub. The only motivation is to
test the interoperability of Gossipsub Extensions Control Message across
implementations. One way for example, is to connect different implementations
together and assert that both peers send the TestExtension message.

## The Protocol

If both Peers support the Test Extension, each peer MUST send a TestExtension
Message.

## Protobuf

```protobuf
syntax = "proto2";

message TestExtension {}
```
