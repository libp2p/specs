# gossipsub v1.3: Choke extensions to improve network efficiency

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r0, 2025-05-23  |

Authors: [@marcopolo]

Interest Group: TODO

[@marcopolo]: https://github.com/marcopolo

See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Overview

This version specifes two protocol changes to gossipsub v1.2:

- Two new control messages: Choke/Unchoke.
- Mesh peers MAY send IHAVEs in lieu of pushing a message. This is typically
  done in response to being Choked.

The two new control messages, `Choke` and `Unchoke`, control whether mesh peers
will eagerly or lazily push messages. A peer is considered choked from the
perspective of another peer if it has received a `Choke` message from that peer.
A choked peer is unchoked if it has received an `Unchoke` message from that
peer, or if it leaves that peer's mesh. Peers are initially unchoked when
grafted to a mesh. Choked status is not automatically symmetric. For peers A and
B, A may choke B, while B may have A unchoked.

If there are no choked peers in the mesh, this version of gossipsub behaves
identically to the previous version of gossipsub. A mesh with only choked peers
behaves identically to a mesh with no chocked peers with an additional
network round trip of latency when fetching the message payload. Latency may
increase further if the peer limits the number of concurrent IWANTs.

When choking is used well, messages arrive without extra delay and without
excessive duplicates. The graph of unchoked peers naturally evolves to utilize
better network paths.

## Terms and Definitions

Eager Push: A message is sent to a peer immediately, without receiving a prior
`IWANT` request.

Lazy Push: A message ID is sent to a peer in an `IHAVE` rather than sending the
message itself. A peer will only receive the message after explicitly requesting
it.

Choked peer: A peer that is currently choked and should lazy push rather than
eager push.

Unchoked peer: A peer that is unchoked and will eagerly push messages.

Choking peer: From the perspective of a node, this is the peer that has choked
it.

## State Diagram

```
      ┌─────────────┐
      │   GRAFTED   │
      │  (Initial)  │
      └──────┬──────┘
             │
             ▼
      ┌─────────────┐
┌─────│  UNCHOKED   │◀────┐
│     │  (Default)  │     │
│     └──────┬──────┘     │
│            │            │
│            │ Choke      │ Unchoke
│            │ message    │ message
│            ▼            │
│     ┌─────────────┐     │
│     │   CHOKED    │─────┘
│     │             │
│     └─────────────┘
│
│ Leave mesh
│
└────────────┐
             │
             ▼
      ┌─────────────┐
      │   PRUNED    │
      │  (Removed)  │
      └─────────────┘
```

## Choked and Unchoked behavior

A choked peer SHOULD NOT eager push messages to the the peer that choked it. It
MAY still eager push a message if it is reasonably sure that it will be the
first delivery of the message to the choking peer. For example, if the choked
peer is publishing a new message, it SHOULD eager push the message to a peer,
even if choked.

A unchoked peer MAY decide to lazy push a message if it is reasonably sure that
it will not be the first delivery of the message.

An implementation SHOULD NOT send a Choke message to another peer that is not
part of its mesh. Note that this can not be a MUST as a peer may leave the mesh
at the same time as a node sends a choke message to it.

Receiving a choke message while choked has no effect. Likewise, receiving an
unchoke message while unchoked has no effect. Implementations SHOULD penalize
excessive duplicate messages.

Because of network delays, it is possible for a peer to eagerly push a message
around the same time it receives a Choke message. Implementations SHOULD NOT
penalize peers for this behavior.

## Prior work

- [Plumtree](https://www.dpss.inesc-id.pt/~ler/reports/srds07.pdf)
- [Episub](https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/episub.md)
- [Gossipsub extension for epidemic meshes](https://github.com/libp2p/specs/pull/413/files)

## Protobuf

```protobuf
syntax = "proto2";

message ControlChoke {
    required string topicID = 1;
}

 message ControlUnchoke {
    required string topicID = 1;
}

message ControlMessage {
	repeated ControlIHave ihave = 1;
	repeated ControlIWant iwant = 2;
	repeated ControlGraft graft = 3;
	repeated ControlPrune prune = 4;
	repeated ControlIDontWant idontwant = 5;
	repeated ControlChoke choke = 6;
	repeated ControlUnchoke unchoke = 7;
}
```

## Security Considerations

In the worst case, this introduces an extra round trip to disseminate a message
at each hop. If an attacker could force the whole network to choke honest peers,
the time to disseminate a message to all honest peers would increase by
$average_round_trip_between_honest_peers \times hops_to_reach_all_nodes$. Where
`hops_to_reach_all_nodes` is related to the network size and the mesh degree
$\log_{D}(\text{network_size})$. This attack requires significant setup, and
would only work once per setup as a peer will unchoke the honest node after
receiving the new message.

A common optimization is limiting the number of concurrent IWANTs for a given
message ID. When using this optimization an attacker could further delay
message. To mitigate this, implementations SHOULD use timeouts to request the
messages from other peers and increase the the number of concurrent IWANTs for
missing message IDs.

## Recommendations to implementations

Note: More recommendations will come as we gain more experience. The following
is not an exhaustive list.

### General Recommendations

Choke and Unchoke messages should be piggybacked. They are small and not time
sensitive. Implementations SHOULD avoid excessive broadcasting of choke and
unchoke messages. Implementations SHOULD downscore excessively noisy peers.

Implementations SHOULD limit choking to topics that disseminate large messages.
For very small messages (1 packet or less) the control overhead may outweigh the
benefits.

### Limiting Concurrent IWANTs

Implementation SHOULD limit the number of concurrent `IWANTs` both across all
messages per peer and per message ID across peers. Implementations SHOULD NOT
allow a set of malicious nodes to indefinitely block an `IWANT` to an honest
node.

Per message, implementations SHOULD limit the number of concurrent `IWANTs`. To
protect from malicious or misbehaving nodes, implementations SHOULD set timeouts
which, once hit, increase the limit for the missing message and request the
message from more peers. It is recommended to scale this limit exponentially
with an upper bound per timeout per message, and reduce timeout intervals linearly.

### IDONTWANT Information

`IDONTWANT` carries a hint of what messages a peer knows about and is about to
send (assuming the message is valid). Implementations may use this to delay a
`IWANT` request to a choked peer if it thinks an `unchoked` peer is about to
send the message.

For example, a node A has peers B and C, and C is choked. If A received
`IDONTWANT` for message ID `foo` at roughly the same time from B and C, and then
received a `IHAVE` from C for `foo`, A may delay the `IWANT` request to C
believing that B will provide the message. If B fails to deliver the message, A
will still receive the message with a delay penalty. If B delivers the message A
successfully avoided a duplicate message.

Implementations MUST be careful on what information they glean from `IDONTWANT`
as the referenced messages have not been validated.

### Scoring function changes

$P_{3}$: Treat `IHAVE` from a choked peer the same as receiving a message for
scoring purposes.

$P_{7}$: If mesh peers fail to respond to an `IWANT` following an `IHAVE`
penalize them twice as much as a non-mesh peer. They are using a slot in your
mesh and not fulfilling their role.

A behavior penalty is applied through $P_{7}$ If a mesh peer sends a large
number of Choke/Unchoke messages within a heartbeat.

### Performance Metrics

Implementations should track the following metrics to help tune performance and
flag issues.

| Metric                | Rationale                                       |
| --------------------- | ----------------------------------------------- |
| DuplicatesPerMessage  | Evaluate how effective the choking strategy is. |
| ChokeUnchokesPerTopic | Highlight undesired choke churn.                |

### Choke strategies

Currently only one choke strategy is outlined. More choke strategies may be
added here as we gain experience.

#### Choke on duplicate; Unchoke on faster messages

This strategy chokes peers that deliver late duplicates. It will unchoke peers
when they deliver messages sooner than any unchoked peer. This strategy has two
parameters:

`chokeThreshold`, a duration. The strategy chokes peers who deliver a message
after `chokeThreshold` from the first delivery of the message.

`unchokeThreshold`, a duration. The strategy unchokes peers who, in response to
an `IWANT`, deliver a message before any unchoked peer by at least
`unchokeThreshold`. Note that this is the time the choked peer delivers a
message, not the time the choked peer delivered the `IHAVE`.

If two or more peers deliver the first two copies at the same time, we will not
choke any of them. The tie may be broken in future message deliveries.

If two or more choked peers, in response to an `IWANT`, deliver a message before
any unchoked peers, all of the choked peers should be unchoked.

Implementations SHOULD keep at least 1 peer unchoked.

##### Setting Threshold Parameters

The threshold parameters should be set such that peers do not continuously
oscillate between choked and unchoked states. The optimal values depend on
network properties. Implementations should track choke and unchoke rates
when tuning these parameters.

Conservative values for these parameters are:

| Parameter          | Conservative Value                             |
| ------------------ | ---------------------------------------------- |
| `chokeThreshold`   | `200 ms` (todo evaluate and add justification) |
| `unchokeThreshold` | `100 ms` (todo evaluate and add justification) |

The `unchokeThreshold` should generally be lower than the `chokeThreshold` since
a choked peer already has a 1 RTT latency penalty in delivering the message (due
to the `IHAVE`/`IWANT` request)

#### Dynamically adjusting threshold parameters

TODO

We can set these parameters dynamically if we target a certain number of
unchoked peers. This would reduce the parameters from 2 machine dependent
parameters to a single application dependent parameter.
