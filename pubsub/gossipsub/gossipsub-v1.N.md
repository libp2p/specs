I'm proposing that we solve the "routing loops" issue, an issue where messages linger in the network indefinitely (or at least for long periods of time), by repurposing the `seqno` fields of messages as a message timestamp. All messages would expire 2 minutes (likely configurable on a per-topic basis) after they're sent.

## Context

By default, pubsub messages have no timestamp and/or expiration. Instead, they're usually identified by the author + an incrementing sequence number, or by the hash of the message.

Routing loops are "prevented" by remembering messages (well, the IDs of messages) seen in the last 2 minutes. There are two policies here:

1. Remember each message for 2 minutes since the message was first seen. This is the default behavior.
2. Remember each message for 2 minutes since the message was **last** seen. This isn't the default behavior for historical reasons, but is generally the "better" approach as it's less sensitive to large message propagation times.

## Problem

Unfortunately, we've found this to be insufficient in practice because message validation can take quite a bit of time. Even if the network latencies involved aren't an issue, when the network is under load:

1. Messages will build up in inbound queues, often blocked on validation. There are limits to these queues, but they still exist.
2. Validation can take a while, especially if the node is under a lot of load. Given the above queues, messages can be delayed by the validation time times the queue length.

This means messages can get stuck in the network for quite a while, especially if the network is heterogeneous and has some slower nodes.

Furthermore, the fact that this is "normal behavior" makes it impossible to penalize participants for spamming old messages.

## Proposal

The proposal is to simply repurpose the message seqno as a timestamp (unix nanoseconds). We assume that all participants have a clock drift less than, say, 30s.

1. Messages with timestamps older than 2 minutes will be dropped.
2. When we receive a message older than 2 minutes plus some propagation delay plus some allowance for clock drift, the immediate sender will be penalized for spamming.
3. When we receive a message from the future (allowing for some clock drift), the message will be dropped.

To handle small clock adjustments and/or message bursts, the last-used seqno plus 1 will be used if the current time is less than or equal to the last-used seqno.

### Messages without sequence numbers

So far, this proposal has assumed that messages have sequence numbers (now timestamps). For messages without explicit sequence numbers/timestamps, a per-topic configurable "message timestamp" function (similar to the "message ID" function) could be added. The default function would preserve the current behavior by always returning the current time.

### Upgrade path

Existing networks can seamlessly upgrade without forcing a network-wide simultaneous upgrade in three stages:

1. First, they can start choosing their message sequence numbers to follow the rules defined in this proposal without rejecting messages based on the rules in this proposal.
2. After some upgrade period, nodes can start enforcing the rules in this proposal (dropping messages) without penalizing suspected spammers.
3. After an additional upgrade period, nodes can start penalizing spammers who fail to follow these rules.

This avoids the need for complex time-synchronized upgrades. Furthermore, it should be fairly straight-forward for networks to determine if they're ready for stage 2 based on the sequence numbers observed in the network.

## Alternatives & Decisions

### Expiration v. Timestamp

Instead of including a timestamp, we could include a message expiration (forbidding both expired messages and messages that expire too far into the future), either replacing the sequence number or in addition to the sequence number. This is mostly equivalent to the message timestamp approach however, it allows the sender to specify messages with _shorter_ timestamps; e.g., in cases where the message is only relevant until some specific point in time. However, this makes it difficult to also use these timestamps as unique IDs (given the need to reason about differing expiration) so it would likely require a new field.

Unfortunately, adding a new field complicates the upgrade path. We'd have to have a stage where all nodes accept & propagate this additional expiration field without actually using it. Any node that uses it will have their message signatures broken when a node that's not expecting the field deserializes and reserializes their message.

While I believe that including a message expiration is strictly "better" in terms of flexibility, I think the benefit is marginal as decentralized pubsub network is not well-suited for realtime communication anyways. Having an easy upgrade path is more important. On the other hand, I won't object strongly to having a separate expiration field instead of repurposing the seqno field.

### TTL

The usual method here would be to add a TTL counter to each message, decrementing that for each hop. However, this method is designed as a fail-safe for high-throughput networks built out of cooperating (trusting) nodes and isn't generally suitable for decentralized systems.

1. It allows messages to loop for the TTL. This works when loops are abnormal, throughput is high, and memory is expensive. In our case, loops are the norm (there are no "routes") and throughput is usually pretty low (compared to the internet).
2. An attacker can just set the TTL to whatever they want and there's no way to distinguish between "spam" and "slow node".
