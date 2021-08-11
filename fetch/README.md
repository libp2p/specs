# Fetch v0.0.1

> The Fetch protocol is used for performing a direct peer-to-peer key-value lookup 

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 1A              | Working Draft  | Active | r1, 2019-08-13  |

Authors: [@aschmahmann]

Interest Group: [Insert Your Name Here]

[@aschmahmann]: https://github.com/aschmahmann

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Implementations

- [go-libp2p-pubsub-router](https://github.com/libp2p/go-libp2p-pubsub-router/pull/33)

## Table of Contents

- [Overview](#overview)
- [Spec Proposal Info](#spec-proposal-info)
- [Wire protocol](#wire-protocol)

## Overview

The fetch protocol is a means for a libp2p node to get data from another based on a given key. It generally fulfills
the contract:

`Fetch(key) (value, statusCode)`

## Spec Proposal Info
### Context

Currently there is no standard protocol for doing simple data retrieval. Sometimes a small data retrieval protocol is all
that's needed to get the job done. This is especially true when it comes to augmenting or layering protocols together.

### Motivation

This specification is helpful because the protocol is already part of a proposal to add a persistence layer on top of
[PubSub](../pubsub).

There have been numerous discussion revolving around how to allow PubSub to be persistent, some of which go back multiple
years (more background information is available [here](https://github.com/libp2p/go-libp2p/issues/698)).
Initial suggestions included modifying or leveraging the existing PubSub spec and implementations.
However, it was decided that PubSub should remain agnostic to any sort of persistence,
and that persistence should be layered on top of PubSub as a separate protocol.

There is currently an [IPNS-over-PubSub spec PR](https://github.com/ipfs/specs/pull/218) that describes how the Fetch
protocol can be used to create a persistence layer on top of PubSub and therefore greatly improve IPNS performance.

### Scope

This is one small protocol that as of right now is only being used to improve the
[go-libp2p-pubsub-router](https://github.com/libp2p/go-libp2p-pubsub-router). This protocol should not require any one
who doesn't want to use it to change anything about their current use.

### Potential Effects

1. A persistent pubsub protocol easily built on top of Fetch
2. A reusable fetch protocol that can be used to augment various other protocols
(e.g. add the ability to directly ask peers for data to a DHT)
3. Might be abused/overused given the simple nature of the protocol

### Expected Feature Set and Tentative Technical Directions
 
Should support: `Fetch(key) (value, statusCode)`

However, the level of specificity in the types of the above variables has wiggle room if people are interested.
The `go-libp2p-pubsub-router` implementation requires:
 
 `key`: At least as generic as a UTF-8 string
 
 `value`: At least as generic as a byte array
 
 `statusCode`: Supports at least `OK`, `NOT_FOUND`, and `ERROR`

## Wire protocol

The libp2p protocol ID for this protocol is `/libp2p/fetch/0.0.1`

### Message Format
The messages in the Fetch protocol use on of the following protobufs (proto3 syntax):

```
message FetchRequest {
	string identifier = 1;
}

message FetchResponse {
	StatusCode status = 1;
	enum StatusCode {
		OK = 0;
		NOT_FOUND = 1;
		ERROR = 2;
	}
	bytes data = 2;
}
```

### Protocol

**Setup:**
- Peers involved, `A`, `B`
- `A` wants to fetch data from `B` corresponding to the key `k`

**Assumptions:**
- `A` has connection to `B`

**Events:**
- `A` sends a `RequestLatest{Identifier : k}` message to `B`
- `B` does some internal lookup and responds with a `RespondLatest` message
  - If `B` finds (and elects to send) some data `v` to `A` it sends `RespondLatest{status: SUCCESS, data: v}`
  - If `B` has no data to send it responds with `RespondLatest{status: NOT_FOUND, data: null}`
    - `A` ignores any information in the `data` field if the status is `NOT_FOUND` 

Note: If at any time `A` or `B` break from the protocol in some way, either by disconnecting/closing streams or by sending
invalid data there is no guarantee on the behavior from the other party.

## Future work

Would love this protocol to work over a packet instead of a stream oriented transport since it's very short lived and will
have cases where the payloads are tiny.

It could also be useful to have an aggregate version of this protocol where instead of fetching key-value pairs we fetch
sets of key-value pairs. This will be more efficient, much more when using a stream oriented transport, than running fetch
multiple times.