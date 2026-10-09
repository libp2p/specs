# Identify v1.0.0

> The identify protocol is used to exchange basic information with other peers
> in the network, including addresses, public keys, and capabilities.

| Lifecycle Stage | Maturity Level | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 3A              | Recommendation | Active | r2, 2026-04-08  |

Authors: [@vyzo]

Interest Group: [@yusefnapora], [@tomaka], [@richardschneider], [@Stebalien], [@bigs]

[@vyzo]: https://github.com/vyzo
[@yusefnapora]: https://github.com/yusefnapora
[@tomaka]: https://github.com/tomaka
[@richardschneider]: https://github.com/richardschneider
[@Stebalien]: https://github.com/Stebalien
[@bigs]: https://github.com/bigs
[@achingbrain]: https://github.com/achingbrain

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
    - [signedPeerRecord](#signedpeerrecord)
  - [Implementation notes](#implementation-notes)
    - [Message sizes and message splitting](#message-sizes-and-message-splitting)
    - [Receiving multiple messages](#receiving-multiple-messages)


## Overview

There are two variations of the identify protocol, `identify` and `identify/push`.

### `identify`

The `identify` protocol has the protocol id `/ipfs/id/1.0.0`, and it is used
to query remote peers for their information.

The protocol works by opening a stream to the remote peer you want to query,
using `/ipfs/id/1.0.0` as the protocol id string. The peer being identified
responds by returning one or more `Identify` messages and closes the stream.

### `identify/push`

The `identify/push` protocol has the protocol id `/ipfs/id/push/1.0.0`, and it is used
to inform known peers about changes that occur at runtime.

When a peer's basic information changes, for example, because they've obtained a new
public listen address, they can use `identify/push` to inform others about the new
information.

The push variant works by opening a stream to each remote peer you want to
update, using `/ipfs/id/push/1.0.0` as the protocol id string. When the remote
peer accepts the stream, the local peer will send one or more `Identify`
messages and close the stream.

Upon receiving the pushed `Identify` message(s), the remote peer should update
their local metadata repository with the information from the message. Note that
missing fields should be ignored, as peers may choose to send partial updates
containing only the fields whose values have changed.

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
  optional bytes signedPeerRecord = 8;
}
```

### protocolVersion

The protocol version identifies the family of protocols used by the peer. The
field is optional but recommended for debugging and statistic purposes.

Previous versions of this specification required connections to be closed on
version mismatch. This requirement is revoked to allow interoperability between
protocol families / networks.

Example value: `/my-network/0.1.0`.

### agentVersion

This is a free-form string, identifying the implementation of the peer.
The usual format is `agent-name/version`, where `agent-name` is
the name of the program or library and `version` is its semantic version.

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

A node should only advertise a protocol if it's willing to receive inbound
streams on that protocol. This is relevant for asymmetrical protocols. For
example assume an asymmetrical request-response style protocol `foo` where some
clients only support initiating requests while some servers (only) support
responding to requests. To prevent clients from initiating requests to other
clients, which given them being clients they fail to respond, clients should not
advertise `foo` in their `protocols` list.

### signedPeerRecord

This field contains a serialized [SignedEnvelope](../RFC/0002-signed-envelopes.md)
containing a [PeerRecord](../RFC/0003-routing-records.md) signed by the sending
node.

It normally contains the same addresses as the `listenAddrs` field, but in a
form that lets us share authenticated addresses with other peers.

When present the fields from a `PeerRecord` MUST be preferred over those in the
main body of the `Identify` message.

## Implementation notes

### Message sizes and message splitting

Early implementations of the Identify protocol limited the incoming message size
to 2KB and would reject any messages larger than this. Others have since
increased this limit to 4KB or 8KB.

With the addition of signed peer records, Circuit Relay addresses, multiaddrs
that contain certificate hashes, etc, it is now much more likely that this
threshold will be exceeded.

If a modern implementation's Identify message would exceed this limit, it
should break it up into smaller chunks.

For optimum backwards compatibility the first message SHOULD NOT exceed 2KB.
Subsequent messages SHOULD NOT exceed 4KB.

Listen addresses SHOULD be ordered such that addresses that have a higher
likelihood of being dialed successfully (e.g. public, non-NAT or Circuit Relay)
are sent in the first Identify message and the `signedPeerRecord`, if used.

### Receiving multiple messages

When multiple messages are received, all fields SHOULD be respected, with later
updates for fields with a cardinality of one taking priority.

Where repeated fields encountered in subsequent messages, they SHOULD be
appended to the earlier occurrences of the field and deduplicated as necessary.

A maximum of 10 Identify messages SHOULD be accepted.
