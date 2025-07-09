# gossipsub v1.3: Extensions Control Message

| Lifecycle Stage | Maturity                 | Status | Latest Revision |
| --------------- | ------------------------ | ------ | --------------- |
| 3A              | Candidate Recommendation | Active | r0, 2025-06-23  |

Authors: [@marcopolo]

Interest Group: [@cortze], [@cskiraly], [@ppopth], [@jxs]

[@marcopolo]: https://github.com/marcopolo
[@cortze]: https://github.com/cortze
[@cskiraly]: https://github.com/cskiraly
[@ppopth]: https://github.com/ppopth
[@jxs]: https://github.com/jxs

See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Overview

This version specifies a way to for gossipsub peers to describe their
characteristics to each other without requiring a new protocol ID per extension.

This spec MUST be updated upon introducing a new extension, either canonical or
experimental, to the network.

## Motivation

This version makes Gossipsub easier to extend by allowing applications to
selectively make use of the extensions it would benefit from. It removes the
need to make Gossipsub extensions follow a strict ordering. Finally, it allows
extensions to iterate independently from Gossipsub's versioning.

## The Extensions Control Message

If a peer supports any extension, the Extensions control message MUST be
included in the first message on the stream. An Extensions control message MUST
NOT be sent more than once. If a peer supports no extensions, it may omit
sending the Extensions control message.

Extensions are not negotiated; they describe characteristics of the sending peer
that can be used by the receiving peer. However, a negotiation can be implied:
each peer uses the Extensions control message to advertise a set of supported
values. The specification of an extension describes how each peer combines the
two sets to define its behavior.

Peers MUST ignore unknown extensions.

Extensions that modify or replace core protocol functionality will be difficult
to combine with other extensions that modify or replace the same functionality
unless the behavior of the combination is explicitly defined. Such extensions
SHOULD define their interaction with previously defined extensions modifying the
same protocol components.

## Protocol ID

The Gossipsub version for this specification is `v1.3.0`. The protocol ID is
`/meshsub/1.3.0`.

## Process to add a new extensions to this spec

### Canonical Extensions

A Canonical Extension is an extension that is well defined, has multiple
implementations, has shown to be useful in real networks, and has rough
consensus on becoming a canonical extension. The extension specification MUST be
defined in the `libp2p/specs` GitHub repo. After an extension meets the stated
criteria, this specification MUST be updated to include the extension in the
`ControlExtensions` protobuf with a link to the extension's specification doc in
a comment. The extension SHOULD use the next lowest available field number.

Any new messages defined by the extension MUST be added to `RPC` message
definition in this spec. Extensions SHOULD minimize the number of new messages
they introduce here. Try to introduce a single new message, and use that message
as a container for more messages similar to the strategy used by the
ControlMessage in the RPC.

All extension messages MUST be an `optional` field.

### Experimental Extensions

In contrast with a Canonical Extension, an Experimental Extension is still being
evaluated and iterated upon. Adding an experimental extension to this spec lets
others see what is being tried, and ensure there are no misinterpretations of
messages on the wire. A patch to this spec is not needed if experimenting with
an extension in a controlled environment. A patch to this spec is also not
needed if you are not using the `/meshsub/v1.3.0` protocol ID.

If the extension is being tested on a live network, a PR MUST be created that
adds the extension to the `ControlExtensions` protobuf with a link to the
extension's specification. Experimental extensions MUST use a large field number
randomly generated to be at least 4 bytes long when varint encoded. The
extension author MUST ensure this field number does not conflict with any
existing field.

New messages defined by this extension should follow the same guidelines as new
messages for canonical extensions. Field numbers MUST be randomly generated and
be at least 4 bytes long when varint encoded.

Maintainers MUST check that the extension is well specified, in the experimental
range, and that the extension will be tested on a live network. If so,
maintainers SHOULD merge the change.

## Protobuf

```protobuf
syntax = "proto2";

message ControlExtensions {
  // Initially empty. Future extensions will be added here along with a
  // reference to their specification.

  // Experimental extensions must use field numbers larger than 0x200000 to be
  // encoded with at least 4 bytes
}

message ControlMessage {
	repeated ControlIHave ihave = 1;
	repeated ControlIWant iwant = 2;
	repeated ControlGraft graft = 3;
	repeated ControlPrune prune = 4;
	repeated ControlIDontWant idontwant = 5;
	optional ControlExtensions extensions = 6;
}

message RPC {
	repeated SubOpts subscriptions = 1;
	repeated Message publish = 2;
	optional ControlMessage control = 3;


	// Canonical Extensions should register their messages here.

	// Experimental Extensions should register their messages here. They
	// must use field numbers larger than 0x200000 to be encoded with at least 4
	// bytes
}
```
