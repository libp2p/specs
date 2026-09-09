# gossipsub v1.4: Large Message Propagation

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r0, 2026-05-11  |

Authors: [@NomzzNJS]

Interest Group: TBD

[@NomzzNJS]: https://github.com/NomzzNJS

See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

---

## Overview

This document specifies extensions to [gossipsub v1.2](gossipsub-v1.2.md) and
the [v1.3 Extensions framework](gossipsub-v1.3.md) to support efficient
propagation of large messages in gossipsub mesh networks.

Current gossipsub implementations are optimized for relatively small messages.
However, the store-and-forward nature of the protocol introduces compounding
latency and excessive bandwidth usage when messages grow large (e.g. >256 KiB).
At each hop, a peer must fully receive a message before relaying it, and the
`IDONTWANT` control message (v1.2) can only be sent *after* full reception,
leaving a window for redundant duplicate transmissions.

This specification introduces four complementary mechanisms to address these
problems:

1. **Message Fragmentation** — splitting large messages into smaller fragments
   that can be relayed independently, enabling pipeline-parallel propagation.
2. **Message Staggering** — forwarding messages to mesh peers sequentially
   rather than simultaneously, giving `IDONTWANT` messages time to propagate.
3. **`PREAMBLE` control message** — announcing a message ID and size before
   transmission begins, enabling receivers to prepare and coordinate.
4. **`IMRECEIVING` control message** — signaling that a message is currently
   being received, allowing neighbors to suppress redundant sends immediately
   (without waiting for full reception).

These extensions are backwards-compatible. Peers that do not support v1.4 will
continue to function normally, receiving full messages from v1.4 peers.

## Motivation

Emerging decentralized systems increasingly require reliable dissemination of
large payloads, including:

- Large Ethereum blocks and blobs (EIP-4844 and beyond)
- Distributed AI model updates and gradient aggregations
- Large event logs and telemetry streams
- State snapshots in decentralized coordination systems
- Agent communication payloads in multi-agent systems

Research conducted using the Shadow network simulator demonstrates that the
combination of fragmentation, staggering, and early-notification control
messages reduces bandwidth utilization by up to 61% and message dissemination
time by up to 35% for large messages [1][2].

### Relationship to Existing Specifications

- **v1.2 (`IDONTWANT`)**: v1.4 builds on `IDONTWANT` — staggering is designed
  specifically to give `IDONTWANT` messages more time to propagate before
  redundant sends occur.
- **v1.3 (Extensions)**: v1.4 capabilities are advertised using the v1.3
  Extensions Control Message framework.
- **Partial Messages Extension**: The Partial Messages extension addresses an
  *application-layer* concern (transmitting only missing parts of structured
  data). v1.4 fragmentation addresses a *transport-layer* concern (breaking
  monolithic messages for efficient relay). They are complementary.

## Protocol ID

Nodes that support this extension SHOULD advertise the version number `1.4.0`.
Gossipsub nodes can advertise their own protocol-id prefix; by default this is
`meshsub`, giving the default protocol id:

- `/meshsub/1.4.0`

## Parameters

| Parameter            | Description                                                                        | Reasonable Default |
| -------------------- | ---------------------------------------------------------------------------------- | ------------------ |
| `fragment_size`      | Maximum size of each message fragment in bytes                                     | 65536 (64 KiB)    |
| `fragmentation_threshold` | Minimum message size before fragmentation is applied                          | 65536 (64 KiB)    |
| `stagger_interval`   | Delay between forwarding a message to successive mesh peers                       | 200 ms             |
| `stagger_threshold`  | Minimum message size before staggering is applied                                 | 65536 (64 KiB)    |
| `preamble_threshold` | Minimum message size before a `PREAMBLE` is sent                                  | 65536 (64 KiB)    |
| `fragment_timeout`   | Maximum time to wait for all fragments of a message before discarding             | 30 seconds         |
| `max_pending_fragments` | Maximum number of messages being reassembled concurrently per peer             | 16                 |

## Message Fragmentation

### Overview

When a message exceeds `fragmentation_threshold` bytes, the sender MUST split it
into fragments of at most `fragment_size` bytes before transmission. Fragments
are transmitted as `LargeMessageFragment` messages within the RPC.

Fragmentation enables **pipeline-parallel relay**: an intermediate peer can begin
forwarding early fragments to its own mesh peers before it has received the
complete message. This eliminates the multiplicative store-and-forward delay
that accumulates at each hop in the mesh.

### Fragmentation Algorithm

Given a message `M` of size `S`:

```
if S <= fragmentation_threshold:
    transmit M as a normal gossipsub message
    return

num_fragments = ceil(S / fragment_size)
message_id = compute_message_id(M)

for i in 0..num_fragments:
    fragment = M[i * fragment_size : min((i+1) * fragment_size, S)]
    send LargeMessageFragment {
        messageID: message_id,
        fragmentIndex: i,
        totalFragments: num_fragments,
        fragmentData: fragment,
        topicID: M.topic
    }
```

### Reassembly

Upon receiving fragments, a peer:

1. Allocates a reassembly buffer keyed by `(sender, messageID)`.
2. Stores each fragment by its `fragmentIndex`.
3. When all `totalFragments` fragments have been received, reconstructs the
   original message and delivers it to the application validator.
4. If `fragment_timeout` elapses before all fragments arrive, the reassembly
   buffer MUST be discarded.

Peers MUST limit the number of concurrent reassembly buffers per peer to
`max_pending_fragments` to prevent resource exhaustion.

### Fragment Forwarding

A peer that supports fragmentation SHOULD forward individual fragments to its
mesh peers as they arrive, without waiting for full reassembly. This is the key
mechanism that reduces store-and-forward latency.

When forwarding fragments to a peer that does not support v1.4, the forwarding
peer MUST wait for full reassembly and send the complete message.

### Interaction with Message Validation

Application-level validation can only occur after full reassembly. Prior to
validation, forwarded fragments are considered *tentatively valid*. If the
reassembled message fails validation, the peer SHOULD apply scoring penalties
to the original sender as defined in v1.1.

### Interaction with Message Cache

Fragments do not replace the message cache (`mcache`). The fully reassembled
message is placed in the `mcache` after successful reassembly. Fragment-level
caching is an implementation detail outside the scope of this specification.

## Message Staggering

### Overview

Instead of forwarding a message (or its fragments) to all mesh peers
simultaneously, a staggering peer forwards to one peer at a time, with a
`stagger_interval` delay between each.

This provides time for `IDONTWANT` messages from earlier recipients to propagate
back before later recipients receive their copy, significantly reducing
redundant transmissions.

### Algorithm

```
if message_size < stagger_threshold:
    forward to all mesh peers simultaneously (standard behavior)
    return

peers = mesh[topic]
sort peers by some heuristic (e.g., score, latency, random)

for peer in peers:
    if messageID not in peer.dont_send_message_ids:
        forward message (or fragments) to peer
        wait stagger_interval
```

### Interaction with IDONTWANT

Staggering amplifies the effectiveness of `IDONTWANT` (v1.2). When a peer
receives a message from the first staggered send, it immediately broadcasts
`IDONTWANT` to its mesh peers. Because subsequent staggered sends are delayed,
there is a high probability that the `IDONTWANT` arrives before the next
staggered send, preventing the redundant transmission entirely.

Without staggering, simultaneous sends mean that `IDONTWANT` messages arrive
too late to prevent any duplicates.

## PREAMBLE Control Message

### Overview

The `PREAMBLE` is a lightweight control message sent by a peer *before* it begins
transmitting a large message (or its fragments). It announces the `messageID`,
the total message size, and the topic.

### Sender Behavior

When a peer is about to relay a message with size exceeding `preamble_threshold`:

1. Send a `ControlPreamble { messageID, messageSize, topicID }` to each mesh
   peer in the topic.
2. Proceed with message/fragment transmission (potentially staggered).

The `PREAMBLE` SHOULD be sent immediately, even when staggering is in effect.

### Receiver Behavior

Upon receiving a `PREAMBLE`, a peer:

1. Records that a message with the given `messageID` is incoming.
2. MAY use the `messageSize` to pre-allocate buffers.
3. MAY delay responding to `IHAVE` messages for this `messageID`, as the full
   message is expected to arrive shortly.
4. If the peer already has the message, it MAY immediately respond with
   `IDONTWANT` to suppress the transmission.

## IMRECEIVING Control Message

### Overview

`IMRECEIVING` is sent by a peer that is *currently in the process* of receiving
a large message (i.e., it has received the `PREAMBLE` or the first fragment,
but not the complete message yet). It notifies mesh neighbors that they should
suppress sending this message.

This fills the gap left by `IDONTWANT`, which can only be sent after full
reception: `IMRECEIVING` provides immediate suppression during the (potentially
long) reception window of a large message.

### Sender Behavior

When a peer begins receiving a large message (triggered by receiving a
`PREAMBLE` or the first `LargeMessageFragment`):

1. Immediately send `ControlImReceiving { messageID }` to all mesh peers in
   the topic.

### Receiver Behavior

Upon receiving `IMRECEIVING` from a peer:

1. Add the `messageID` to the peer's `dont_send_message_ids` set (same set
   used by `IDONTWANT`).
2. When later relaying this `messageID`, skip this peer.

`IMRECEIVING` is advisory, like `IDONTWANT`. A sender MAY still transmit the
message after receiving `IMRECEIVING`; doing so MUST NOT be penalized.

### Comparison with IDONTWANT

| Property             | IDONTWANT (v1.2)         | IMRECEIVING (v1.4)                   |
| -------------------- | ------------------------ | ------------------------------------ |
| When sent            | After full reception     | At start of reception                |
| Suppression window   | Future sends only        | Immediate (during reception)         |
| Certainty            | Definitive (has message) | Probabilistic (reception in progress)|
| Message size benefit | All sizes                | Primarily large messages             |

## Router State Changes

### New Per-Peer State

In addition to the existing per-peer state, v1.4 peers maintain:

- `receiving_messages`: a set of `messageID`s currently being received
  (populated by `PREAMBLE` / first fragment, cleared on reassembly completion
  or timeout).
- `fragment_buffers`: a map of `messageID → fragment[]` for reassembly.

### Modified Message Processing

When processing incoming messages, the router additionally:

1. On receiving `ControlPreamble`: records the incoming message, optionally
   sends `IDONTWANT` (if already have) or `IMRECEIVING` (if receiving from
   another peer).
2. On receiving `ControlImReceiving`: adds `messageID` to the sender's
   `dont_send_message_ids`.
3. On receiving `LargeMessageFragment`: stores in fragment buffer, forwards
   fragment to mesh peers (if forwarding fragments), and sends `IMRECEIVING`
   if this is the first fragment for this message.

## Heartbeat Changes

During heartbeat processing:

- Expired entries in `receiving_messages` (older than `fragment_timeout`)
  SHOULD be cleaned up, and corresponding fragment buffers discarded.
- Expired entries in `dont_send_message_ids` populated by `IMRECEIVING`
  SHOULD be pruned (same pruning strategy as `IDONTWANT` entries).

## Scoring Implications

- A peer that sends an excessive number of `PREAMBLE` messages without
  following up with actual message data SHOULD be penalized through P₇
  (Behavioural Penalty) as defined in v1.1.
- Fragment flooding (sending many fragments for non-existent messages) SHOULD
  trigger P₄ (Invalid Messages) penalties upon reassembly failure.
- A peer that consistently sends `IMRECEIVING` without subsequently delivering
  or forwarding the message MAY be penalized through P₇.

## Security Considerations

### Fragment Flooding

An attacker could send a large number of fragments for fake messages to exhaust
memory. The `max_pending_fragments` parameter limits per-peer reassembly state.
Implementations SHOULD also apply a global limit on total reassembly buffers.

### PREAMBLE Abuse

Sending `PREAMBLE` messages for messages that never arrive wastes receiver
resources (pre-allocated buffers). The `fragment_timeout` and behavioural
penalties (P₇) mitigate this. Implementations MAY rate-limit `PREAMBLE`
messages from a single peer.

### IMRECEIVING Abuse

A malicious peer could send `IMRECEIVING` for messages it never intends to
receive, causing neighbors to skip sending to it and degrading its mesh
participation. Since `IMRECEIVING` entries are pruned during heartbeat and
the message will still be available via `IHAVE`/`IWANT` gossip, the impact is
limited.

### Fragment Reassembly Resource Exhaustion

Implementations MUST bound the total memory used for fragment reassembly.
Recommended strategy: track total bytes across all reassembly buffers and
reject new fragments when a configurable limit is exceeded.

## Backwards Compatibility

All extensions in this specification are backwards-compatible with gossipsub
v1.0, v1.1, v1.2, and v1.3:

- Peers that do not support v1.4 will ignore unknown control messages
  (`PREAMBLE`, `IMRECEIVING`) and unknown RPC fields (`LargeMessageFragment`)
  per standard protobuf behavior.
- A v1.4 peer MUST detect whether its mesh peers support v1.4 (via the v1.3
  Extensions Control Message). For peers that do not support v1.4, the peer
  MUST send complete, unfragmented messages.
- Staggering is a local behavior change and does not affect interoperability.

## Protobuf

The protobuf messages are defined in the
[extensions.proto](./extensions/extensions.proto) file. The following new
messages are introduced:

```protobuf
message ControlPreamble {
  optional bytes messageID = 1;
  optional uint64 messageSize = 2;
  optional string topicID = 3;
}

message ControlImReceiving {
  optional bytes messageID = 1;
}

message LargeMessageFragment {
  optional bytes messageID = 1;
  optional uint32 fragmentIndex = 2;
  optional uint32 totalFragments = 3;
  optional bytes fragmentData = 4;
  optional string topicID = 5;
}
```

These are integrated into the existing `ControlMessage` and `RPC` messages.
See `extensions.proto` for the complete definition.

## References

- [1] M. U. Farooq, T. Cizain, D. Kaiser. "Staggering and Fragmentation for
  Improved Large Message Handling in libp2p GossipSub." arXiv:2504.10365, 2025.
- [2] M. U. Farooq, D. Kaiser. "PREAMBLE and IMRECEIVING for Improved Large
  Message Handling in libp2p GossipSub." arXiv:2505.17337, 2025.
- [3] gossipsub v1.2: IDONTWANT. https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/gossipsub-v1.2.md
- [4] gossipsub v1.3: Extensions Control Message. https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/gossipsub-v1.3.md
