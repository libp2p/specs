# gossipsub v1.1: Security extensions to improve on attack resilience and bootstrapping

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 1A              | Draft          | Active | r6, 2020-05-21  |


Authors: [@vyzo]

Interest Group: [@yusefnapora], [@raulk], [@whyrusleeping], [@Stebalien], [@daviddias]

[@whyrusleeping]: https://github.com/whyrusleeping
[@yusefnapora]: https://github.com/yusefnapora
[@raulk]: https://github.com/raulk
[@vyzo]: https://github.com/vyzo
[@Stebalien]: https://github.com/Stebalien
[@daviddias]: https://github.com/daviddias

See the [lifecycle document][lifecycle-spec] for context about maturity level and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

---

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->


- [Overview](#overview)
- [Protocol extensions](#protocol-extensions)
  - [Explicit Peering Agreements](#explicit-peering-agreements)
  - [PRUNE Backoff and Peer Exchange](#prune-backoff-and-peer-exchange)
    - [Protobuf](#protobuf)
  - [Flood Publishing](#flood-publishing)
  - [Adaptive Gossip Dissemination](#adaptive-gossip-dissemination)
  - [Outbound Mesh Quotas](#outbound-mesh-quotas)
  - [Peer Scoring](#peer-scoring)
    - [Score Thresholds](#score-thresholds)
    - [Heartbeat Maintenance](#heartbeat-maintenance)
    - [Opportunistic Grafting](#opportunistic-grafting)
    - [The Score Function](#the-score-function)
    - [Topic Parameter Calculation and Decay](#topic-parameter-calculation-and-decay)
      - [P₁: Time in Mesh](#p%E2%82%81-time-in-mesh)
      - [P₂: First Message Deliveries](#p%E2%82%82-first-message-deliveries)
      - [P₃ and P₃b: Mesh Message Delivery](#p%E2%82%83-and-p%E2%82%83b-mesh-message-delivery)
      - [P₄: Invalid Messages](#p%E2%82%84-invalid-messages)
      - [Parameter Decay](#parameter-decay)
    - [Guidelines for Tuning the Scoring Function](#guidelines-for-tuning-the-scoring-function)
    - [Extended Validators](#extended-validators)
  - [Overview of New Parameters](#overview-of-new-parameters)
  - [Spam Protection Measures](#spam-protection-measures)
  - [Recommendations for Network Operators](#recommendations-for-network-operators)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Overview

This document specifies extensions to [gossipsub v1.0](gossipsub-v1.0.md) intended to improve
bootstrapping and protocol attack resistance. The extensions change the algorithms that
prescribe local peer behaviour and are fully backwards compatible with v1.0 of the protocol.
Peers that implement these extensions, advertise v1.1 of the protocol using `/meshsub/1.1.0`
as the protocol string.

## Protocol extensions

### Explicit Peering Agreements

The protocol now supports explict peering agreements between node operators. With explicit peering,
the application can specify a list of peers to remain connected to and unconditionally forward
messages to each other outside of the vagaries of the peer scoring system and other defensive
measures.

For every explicit peer, the router must establish and maintain a connection. The connections
are initially established when the router boots, and are periodically checked for connectivity
and reconnect if the connectivity is lost. The recommended period for connectivity checks is 5 minutes.

Peering agreements are established out of band and reciprocal.
explicit peers exist outside the mesh: every new valid incoming message is forwarded to the direct
peers, and incoming RPCs are always accepted from them. It is an error to GRAFT on a explicit peer,
and such an attempt should be logged and rejected with a PRUNE.

### PRUNE Backoff and Peer Exchange

Gossipsub relies on ambient peer discovery in order to find peers within a topic of interest.
This puts pressure to the implementation of a scalable peer discovery service that
can support the protocol. With Peer Exchange, the protocol can now bootstrap from a small
set of nodes, without relying on an external peer discovery service.

Peer Exchange (PX) kicks in when pruning a mesh because of oversubscription. Instead of simply
telling the pruned peer to go away, the pruning peer _may_ provide a set of other peers where the
pruned peer can connect to reform its mesh (see [Peer Scoring](#peer-scoring) below).

In addition, both the pruned and the pruning peer add a backoff period from each other, within which
they will not try to regraft. Both the pruning and the pruned peer will immediately prune a `GRAFT`
within the backoff period and extend it.
When a peer tries to regraft too early, the pruning peer may apply a behavioural penalty
for the action, and penalize the peer through P₇ (see [Peer Scoring](#peer-scoring) below).

The recommended duration for the backoff period is 1 minute, while the recommended number of peers
to exchange is larger than `D_hi` so that the pruned peer can reliably form a full mesh.
In order to correctly synchronize the two peers, the pruning peer should include the backoff period
in the PRUNE message. The peer has to wait the full backoff period before attempting to graft again,
otherwise it risks getting its graft rejected and being penalized in its score if it attempts to
graft too early.

In order to implement PX, we extend the `PRUNE` control message to include an optional set of
peers the pruned peer can connect to. This set of peers includes the Peer ID and a [_signed_ peer
record](https://github.com/libp2p/specs/pull/217) for each peer exchanged.
In order to facilitate the transition to the usage of signed peer records within the libp2p ecosystem,
the emitting peer is allowed to omit the signed peer record if it doesn't have one.
In this case, the pruned peer will have to utilize an external service to discover addresses for
the peer, eg the DHT.

#### Protobuf

The `ControlPrune` message is extended with a `peers` field as follows.

```protobuf
message ControlPrune {
	optional string topicID = 1;
	repeated PeerInfo peers = 2; // gossipsub v1.1 PX
	optional uint64 backoff = 3; // gossipsub v1.1 backoff time (in seconds)
}

message PeerInfo {
	optional bytes peerID = 1;
	optional bytes signedPeerRecord = 2;
}
```

### Flood Publishing

In gossipsub v1.0, peers publish new messages to the members of their mesh if they are subscribed to
the topic to which they're publishing. A peer can also publish to topics they are not subscribed
to, in which case they will select peers from their fanout map.

In gossipsub v1.1 publishing is (optionally) done by publishing the message to all connected peers
with a score above a publish threshold (see [Peer Scoring](#peer-scoring) below). This applies
regardless of whether the publisher is subscribed to the topic. With flood publishing enabled, the
mesh is used when propagating messages from other peers, but a peer's own messages will always be
published to all known peers in the topic.

This behaviour is prescribed to counter eclipse attacks and ensure that a newly published message
from a honest node will reach all connected honest nodes and get out to the network at large.
When flood publishing is in use there is no point in utilizing a fanout map or emitting gossip when
the peer is a pure publisher not subscribed in the topic.

This behaviour also reduces message propagation latency as the message is injected to more points
in the network.

### Adaptive Gossip Dissemination

In gossipsub v1.0 gossip is emitted to a fixed number of peers, as specified by the `D_lazy`
parameter. In gossipsub v1.1 the disemmination of gossip is adaptive; instead of emitting gossip
to a fixed number of peers, we emit gossip to a percentage of our peers with a minimum of `D_lazy`
peers.

The parameter controlling the emission of gossip is called the gossip _factor_. When a node wants to
emit gossip during the heartbeat, first it selects all peers with a peer score above a gossip
threshold (see [Peer Scoring](#peer-scoring) below). From these peers, it randomly selects gossip
factor peers with a minimum of `D_lazy`, and emits gossip to the selected peers.

The recommended value for the gossip factor is `0.25`, which with the default of 3 rounds of gossip
per message ensures that each peer has at least 50% chance of receiving gossip about a message.
More specifically, for 3 rounds of gossip, the probability of a peer _not_ receiving gossip about
a fresh message is `(3/4)³=27/64=0.421875`. So each peer receives gossip about a fresh message with
a `0.578125` probability.

This behaviour is prescribed to counter sybil attacks and ensures that a message from a honest
node propagates in the network with high probability.

### Outbound Mesh Quotas

In gossipsub v1.0 mesh peers are randomly selected, without any weight given to the direction
of the conneciton. In contrast, gossipsub v1.1 implements oubout connection quotas, so that
a peer tries to always maintain a number of outbound connections in the mesh.

Specifically, we define a new overlay parameter `D_out`, which must be set below `D_lo` and
at most `D/2`, such that:
- When the peer prunes because of oversubscription, it selects survivor peers under the constraint
  that at least `D_out` peers are outbound connections;  see also [Peer Scoring](#peer-scoring) below.
- When the peer receives a GRAFT while oversubscribed (with mesh degree at `D_hi` or higher), it only
  accepts the new peer in the mesh if it is an outbound connection.
- During heartbeat maintainance, if the peer already has at least `D_lo` peers in the mesh but not
  enough outbound connections, then it selects as many needed peers to fill the quota and grafts them
  in the mesh.

This behaviour is presrcibed to counter sybil attacks and ensures that a coordinated inbound attack can
never fully take over the mesh of a target peer.

### Peer Scoring

In gossipsub v1.1 we introduce a peer scoring component: each individual peer maintains a score
for other peers. The score is locally computed by each individual peer based on observed behaviour
and is not shared. The score is a real value, computed as weighted mix of parameters,
with pluggable application specific scoring. The score is computed across all (configured) topics
with a weighted mix, such that faulty behaviour in one topic percolates to other topics.
Furthermore, the score is retained for some period of time when a peer disconnects, so that malicious
peers cannot easily reset their score when it drops to negative and well behaving
peers don't lose their status because of a disconnection.

The intention is to detect malicious or faulty behaviour and penalize the misbehaving peers
with a negative score.

#### Score Thresholds

The score is plugged into various gossipsub algorithms such that peers with negative scores are
removed from the mesh. Peers with heavily negative score are further penalized or even ignored
if the score drops too low.

More specifically, the following thresholds apply:
- `0`: the baseline threshold; peers with a score below this threshold are pruned from the mesh
  during the heartbeat and ignored when looking for peers to graft. Furthermore, no PX information
  is emitted towards those peers and PX is ignored from them. In addition, when performing PX only
  peers with non-negative scores are exchanged.
- `gossipThreshold`: when a peer's score drops below this threshold, no gossip is emitted towards
  that peer and gossip from that peer is ignored. This threshold should be negative, such that
  some information can be propagated to/from mildly negatively scoring peers.
- `publishThreshold`: when a peer's score drops below this threshold, self published messages are
  not propagated towards this peer when (flood) publishing. This threshold should be negative, and
  less than or equal to the gossip threshold.
- `graylistThreshold`: when a peer's score drops below this threshold, the peer is graylisted and
  its RPCs are ignored. This threshold must be negative, and less than the gossip/publish threshold.
- `acceptPXThreshold`: when a peer sends us PX information with a prune, we only accept it and connect
  to the supplied peers if the originating peer's score exceeds this threshold. This threshold should
  be non-negative and for increased security a large positive score attainable only by bootstrappers
  and other trusted well-connected peers.
- `opportunisticGraftThreshold`: when the median peer score in the mesh drops below this value, the
  router may select more peers with score above the median to opportunistically graft on the mesh
  (see Opportunistic Grafting below). This threshold should be positive, with a relatively small value
  compared to scores achievable through topic contributions.

#### Heartbeat Maintenance

The score is checked explicitly during heartbeat maintenance such that:
- Peers with negative score are pruned from all meshes.
- When pruning because of oversubscription, the peer keeps the best `D_score` scoring peers and
  selects the remaining peers to keep at random. This protects the mesh from takeover attacks
  and ensures that the best scoring peers are kept in the mesh. At the same time, we do keep some
  peers as random so that the protocol is responsive to new peers joining the mesh.
  The selection is done under the constraint that `D_out` peers are outbound connections; if the
  scoring plus random selection does not result in enough outbound connections, then we replace
  the random and lower scoring peers in the selection with outboud connection peers.
- When selecting peers to graft because of undersubscription, peers with a negative score are ignored.

#### Opportunistic Grafting

It may be possible that the router gets stuck with a mesh of poorly performing peers, either due to
churn of good peers or because of a successful large scale cold boot or covert flash attack.
When this happens, the router will normally react through mesh failure penalties (see The Score
Function below), but this reaction time may be slow: the peers selected to replace the negative
scoring peers are selected at random among the non-negative scoring peers, which may result in multiple
rounds of selections amongst a sybil poisoned pool. Furthermore, the population of sybils may be so
large that the sticky mesh failure penalties completely decay before any good peers are selected, thus
making sybils re-eligible for grafting.

In order to recover from such disaster scenarios and generally adaptively optimize the mesh over time,
gossipsub v1.1 introduces an opportunistic grafting mechanism.
Periodically, the router checks the median score of peers in the mesh against the `opportunisticGrafThreshold`.
If the median score is below the threshold, the the router opportunistically grafts (at least) two peers
with score above the median in the mesh.
This improves an underperforming mesh by introducing good scoring peers that may have been gossiping
at us.
This also allows the router to get out of sticky disaster situations by replacing sybils attempting
an eclipse with peers which have actually forwarded messages through gossip recently.

The recommended period for opportunistic grafting is 1 minute, while the router should graft 2 peers
(with the default parameters) so that it has the opportunity to become a conduit between them and
establish a score in the mesh. Nonetheless, the number of peers that are opportunistically grafted is
controlled by the application. It may be desirable to graft more peers if the application has
configured a larger mesh than the default parameters.

#### The Score Function

The score function is a weighted mix of parameters, 4 of them per topic and 3 of them globally
applicable.
```
Score(p) = TopicCap(Σtᵢ*(w₁(tᵢ)*P₁(tᵢ) + w₂(tᵢ)*P₂(tᵢ) + w₃(tᵢ)*P₃(tᵢ) + w₃b(tᵢ)*P₃b(tᵢ) + w₄(tᵢ)*P₄(tᵢ))) + w₅*P₅ + w₆*P₆ + w₇*P₇
```
where `tᵢ` is the topic weight for each topic where per topic parameters apply.

The parameters are defined as follows:
- `P₁`: **Time in Mesh** for a topic. This is the time a peer has been in the mesh, capped to a small value
  and mixed with a small positive weight. This is intended to boost peers already in the mesh so that
  they are not prematurely pruned because of oversubscription.
- `P₂`: **First Message Deliveries** for a topic. This is the number of message first delivered by the peer
  in the topic, mixed with a positive weight. This is intended to reward peers who first forward a
  valid message.
- `P₃`: **Mesh Message Delivery Rate** for a topic. This parameter is a threshold for the expected message
  delivery rate within the mesh in the topic. If the number of deliveries is above the threshold,
  then the value is 0. If the number is below the threshold, then the value of the parameter is
  the square of the deficit.
  This is intended to penalize peers in the mesh who are not delivering the expected
  number of messages so that they can be removed from the mesh. The parameter is mixed with a negative
  weight.
- `P₃b`: **Mesh Message Delivery Failures** for a topic. This is a sticky parameter that counts the number
  of mesh message delivery failures. Whenever a peer is pruned with a negative score, the parameter
  is augmented by the rate deficit at the time of prune. This is intended to keep history of prunes
  so that a peer that was pruned because of underdelivery cannot quickly get regrafted into the
  mesh. The parameter is mixed with negative weight.
- `P₄`: **Invalid Messages** for a topic. This is the number of invalid messages delivered in the topic.
  This is intended to penalize peers who transmit invalid messages, according to application specific
  validation rules. It is mixed with a negative weight.
- `P₅`: **Application Specific** score. This is the score component assigned to the peer by the application
  itself, using application specific rules. The weight is positive, but the parameter itself has an
  arbitrary real value, so that the application can signal misbehaviour with a negative score or gate
  peers before an application specific handshake is completed.
- `P₆`: **IP Colocation Factor**. This parameter is a threshold for the number of peers using the same IP
  address. If the number of peers in the same IP exceeds the threshold, then the value is the square
  of the surplus, otherwise it is 0. This is intended to make it difficult to carry out sybil attacks
  by using a small number of IPs. The parameter is mixed with a negative weight.
- `P₇`: **Behavioural Penalty**. This parameter captures penalties applied for misbehaviour. The
  parameter has an associated (decaying) counter, which is explicitly incremented by the router on
  specific events. The value of the parameter is the square of the counter and is mixed with a negative
  weight.

The `TopicCap` function allows the application to specify an optional cap to the contribution to the
score across all topics.

#### Topic Parameter Calculation and Decay

The topic parameters are implemented using counters maintained internally by the router
whenever an event of interest occurs. The counters _decay_ periodically so that their values are
not continuously increasing and ensure that a large positive or negative score isn't sticky for
the lifetime of the peer.

The decay interval is configurable by the application, with shorter intervals resulting in faster
decay.

Each decaying parameter can have it's own decay _factor_, which is a configurable parameter that
controls how much the parameter will decay each decay period.

The decay factor is a float in the range of (0.0, 1.0) that will be multiplied with the current
parameter value at each decay interval update. For example, suppose the value for `P₂` (First
Message Deliveries) is `120`, with a decay factor `FirstMessageDeliveriesDecay = 0.97`. At the decay
interval, the value will be updated to `120 * 0.97 == 110.4`.

The decay factor and interval together determine the absolute rate of decay for each parameter. With
a decay interval of 1 second and a decay factor of `0.97`, a parameter will decrease by 3% every
second, while `0.90` would cause it lose 10%/sec, etc.


##### P₁: Time in Mesh

In order to compute `P₁`, the router records the time when the peer is GRAFTed. The time in mesh
is calculated lazily during the decay update to avoid a large number of calls to `gettimeofday`.
The parameter value is the division of the time elapsed since the GRAFT with an application
configurable quantum.

For example, with a quantum of one second, a peer's `P₁` value will be equal to the number of
seconds elapsed since they were GRAFTed onto the mesh. With a quantum of 5 minutes, the `P₁` value
will be the number of 5 minute intervals elapsed since GRAFTing. The `P₁` value will be capped to an
application configurable maximum.

In pseudo-go:
```go
// topic configuration parameters
var TimeInMeshQuantum time.Duration
var TimeInMeshCap     float64

// lazily updated time in mesh
var meshTime time.Duration

// P₁
p1 := float64(meshTime / TimeInMeshQuantum)
if p1 > TimeInMeshCap {
  p1 = TimeInMeshCap
}
```

##### P₂: First Message Deliveries

In order to compute `P₂`, the router maintains a counter that increments whenever a message
is first delivered in the topic by the peer. The parameter has a cap that applies at the time
of increment.

In pseudo-go:
```go
// topic configuration parameters
var FirstMessageDeliveriesCap float64

// couner updated every time a first message delivery occurs
var firstMessageDeliveries float64

// counter update
firstMessageDeliveries += 1
if firstMessageDeliveries > FirstMessageDeliveriesCap {
  firstMessageDeliveries = FirstMessageDeliveriesCap
}

// P₂
p2 := firstMessageDeliveries
```

##### P₃ and P₃b: Mesh Message Delivery

In order to compute `P₃`, the router maintains a counter that increments whenever a first
or _near-first_ message delivery occurs in the topic by a peer in the mesh.  A near-first message
delivery is a message delivery that occurs while a message has been first received and is being
validated or it has been received within a configurable window of validation of first message
delivery. The window is configurable but should be small (in the order of milliseconds) to avoid
allowing a mesh peer to build score by simply replaying back the messages received by the current
router. The parameter has a cap that applies at the time of increment.

In order to avoid triggering the penalty too early, the parameter has an activation window.
This is a configurable value that is the time that the peer must have been in the mesh before
the parameter applies.

In pseudo-go:
```go
// topic configuration parameters
var MeshMessageDeliveriesCap, MeshMessageDeliveriesThreshold     float64
var MeshMessageDeliveriesWindow, MeshMessageDeliveriesActivation time.Duration

// time in mesh, lazily updated
var meshTime time.Duration

// counter updated every time a first or near-first message delivery occurs by a mesh peer
var meshMessageDeliveries float64

// counter update
meshMessageDeliveries += 1
if meshMessageDeliveries > MeshMessageDeliveriesCap {
  meshMessageDeliveries = MeshMessageDeliveriesCap
}

// calculation of P₃
var deficit float64
if meshTime > MeshMessageDeliveriesActivation && meshMessageDeliveries < MeshMessageDeliveriesThreshold {
  deficit = MeshMessageDeliveriesThreshold - meshMessageDeliveries
}

p3 := deficit * deficit
```

In order to calculate P₃b, the router maintains a counter that is updated whenever the peer is pruned
with an active deficit in message delivery. The parameter is uncapped.

In pseudo-go:
```go
// counter updated at prune time
var meshFailurePenalty float64

// counter update
if meshTime > MeshMessageDeliveriesActivation && meshMessageDeliveries < MeshMessageDeliveriesThreshold {
  deficit = MeshMessageDeliveriesThreshold - meshMessageDeliveries
  meshFailurePenalty += deficit * deficit
}

// P₃b
p3b := meshFailurePenalty
```

##### P₄: Invalid Messages

In order to compute `P₄`, the router maintains a counter that increments whenever a message fails
validation. The value of the parameter is the square of the counter, which is uncapped.

In pseudo-go:
```go
// counter updated every time a message fails validation
var invalidMessageDeliveries float64

// counter update
invalidMessageDeliveries += 1

// P₄
p4 := invalidMessageDeliveries * invalidMessageDeliveries
```

##### Parameter Decay

The counters associated with `P₂`, `P₃`, `P₃b`, and `P₄` decay periodically by multiplying with a configurable
decay factor. When the value drops below a threshold it is considered zero.

In pseudo-go:
```go
// decay factors
var FirstMessageDeliveriesDecay, MeshMessageDeliveriesDecay, MeshFailurePenaltyDecay, InvalidMessageDeliveriesDecay float64

// 0-threshold
var DecayToZero float64

// periodic decay of counters
firstMessageDeliveries *= FirstMessageDeliveriesDecay
if firstMessageDeliveries < DecayToZero {
  firstMessageDeliveries = 0
}

meshMessageDeliveries *= MeshMessageDeliveriesDecay
if meshMessageDeliveries < DecayToZero {
  meshMessageDeliveries = 0
}

meshFailurePenalty *= MeshFailurePenaltyDecay
if meshFailurePenalty < DecayToZero {
  meshFailurePenalty = 0
}

invalidMessageDeliveries *= InvalidMessageDeliveriesDecay
if invalidMessageDeliveries < DecayToZero {
  invalidMessageDeliveries = 0
}
```

#### Guidelines for Tuning the Scoring Function

`TBD`: We are currently developing multiple types of simulations that will inform us on how to best recommend tunning the Scoring function. We will update this section once that work is complete

#### Extended Validators

The pubsub subsystem incorporates application-specific message validators so that the application can
signal invalid message delivery, and trigger the P₄ penalty.
However, it is possible to have circumstances where a message should not be delivered to the application
or forwarded to the network, but without triggering the P₄ penalty.
A known use-case where this need exists is in the case of duplicate beacon messages or while an application is syncing its blockchain, in which case it would be unable to ascertain the validity of new messages.

In order to address this situation, all gossipsub v1.1 implementations _must_ support extended validators with an enumerated decision interface.
The outcome of extended validation can be at a minimum one of three things:
- Accept message; in this case the message is considered valid, and it should be delivered and forwarded to the network.
- Reject message; in this case the message is considered invalid, and it should be rejected and trigger the P₄ penalty.
- Ignore message; in this case the message is neither delivered nor forwarded to the network, but the router does not trigger the P₄ penalty.

### Overview of New Parameters

The extensions that make up gossipsub v1.1 introduce several new application configurable
parameters. This section summarizes all the new parameters along with a brief description.

The following parameters apply globally:

| Parameter      | Type             | Description                                                            | Reasonable Default |
|----------------|------------------|------------------------------------------------------------------------|--------------------|
| `PruneBackoff` | Duration         | Time after pruning a mesh peer before we consider grafting them again. | `1 minute`         |
| `FloodPublish` | Boolean          | Whether to enable flood publishing                                     | `true`             |
| `GossipFactor` | Float [0.0, 1.0] | % of peers to send gossip to, if we have more than `D_lazy` available  | `0.25`             |
| `D_score`      | Integer          | Number of peers to retain by score when pruning because of oversubscription | 4 or 5 for a `D` of 6. |
| `D_out`        | Integer          | Number of outbound connections to keep in the mesh. Must be less than `D_lo` and at most `D/2`  | 2 for a `D` of 6        |

The remaining parameters apply to [Peer Scoring](#peer-scoring). Because many parameters are
inter-related and may be application-specific, reasonable defaults are not shown here. See
[Guidelines for Tuning the Scoring Function](#guidelines-for-tuning-the-scoring-function) to
understand how tune the parameters to the needs of an application.

The following peer scoring parameters apply globally to all peers and topics:

| Parameter           | Type     | Description                                                             | Constraints                  |
|---------------------|----------|-------------------------------------------------------------------------|------------------------------|
| `GossipThreshold`   | Float    | No gossip emitted to peers below threshold; incoming gossip is ignored. | Must be < 0                  |
| `PublishThreshold`  | Float    | No self-published messages are sent to peers below threshold.           | Must be < `GossipThreshold`  |
| `GraylistThreshold` | Float    | All RPC messages are ignored from peers below threshold.                | Must be < `PublishThreshold` |
| `AcceptPXThreshold` | Float    | PX information by peers below this threshold is ignored.                | Must be >= 0                 |
| `OpportunisticGraftThreshold` | Float | If the median score in the mesh drops below this threshold, then the router may opportunistically graft better scoring peers. | Must be >= 0 |
| `DecayInterval`     | Duration | Interval at which parameter decay is calculated.                        |                              |
| `DecayToZero`       | Float    | Limit below which we consider a decayed param to be "zero".             | Should be close to 0.0       |
| `RetainScore`       | Duration | Time to remember peer scores after a peer disconnects.                  |                              |

The remaining peer score parameters affect how scores are computed for each peer based on their
observed behavior.

Parameters with type `Weight` are floats that determine
how much a score parameter contributes to the overall score for a peer. See [The Score
Function](#the-score-function) for details.

There are some parameters that apply to the peer "as a whole", regardless of
which topics they are subscribed to:

| Parameter                     | Type   | Description                                           | Constraints                                                   |
|-------------------------------|--------|-------------------------------------------------------|---------------------------------------------------------------|
| `AppSpecificWeight`           | Weight | Weight of `P₅`, the application-specific score.       | Must be positive, however score values may be negative.       |
| `IPColocationFactorWeight`    | Weight | Weight of `P₆`, the IP colocation score.              | Must be negative, to penalize peers with multiple IPs.        |
| `IPColocationFactorThreshold` | Float  | Number of IPs a peer may have before being penalized. | Must be at least 1. Values above threshold will be penalized. |
| `BehaviourPenaltyWeight`      | Weight | Weight of `P₇`, the behaviour penalty.                | Must be negative to penalize peers for misbehaviour. |
| `BehaviourPenaltyDecay`       | Float  | Decay factor for `P₇`.                                | Must be between 0 and 1. |

The remaining parameters are applied to a peer's behavior within a single topic. Implementations
should be able to accept configurations for multiple topics, keyed by topic ID string. Each topic
may be configured with the following params. If a topic is not configured, a peer's behavior in that
topic will not contribute to their score. If a peer is in multiple configured topics, each topic
will contribute to their total score according to the `TopicWeight` parameter.

| Parameter                         | Type     | Description                                                           | Constraints                                                           |
|-----------------------------------|----------|-----------------------------------------------------------------------|-----------------------------------------------------------------------|
| `TopicWeight`                     | Weight   | How much does behavior in this topic contribute to the overall score? |                                                                       |
| **`P₁`**                          |          | **Time in Mesh**                                                      |                                                                       |
| `TimeInMeshWeight`                | Weight   | Weight of `P₁`.                                                       | Should be a small positive value.                                     |
| `TimeInMeshQuantum`               | Duration | Time a peer must be in mesh to accrue one "point" for `P₁`.           |                                                                       |
| `TimeInMeshCap`                   | Float    | Maximum value for `P₁`.                                               | Should be a small positive value.                                     |
| **``P₂``**                        |          | **First Message Deliveries**                                          |                                                                       |
| `FirstMessageDeliveriesWeight`    | Weight   | Weight of `P₂`.                                                       | Should be positive, to reward fast peers.                             |
| `FirstMessageDeliveriesDecay`     | Float    | Decay factor for `P₂`.                                                |                                                                       |
| `FirstMessageDeliveriesCap`       | Float    | Maximum value for `P₂`.                                               |                                                                       |
| **`P₃`**                          |          | **Mesh Message Delivery Rate**                                        |                                                                       |
| `MeshMessageDeliveriesWeight`     | Weight   | Weight of `P₃`.                                                       | Should be negative, to penalize peers below threshold.                |
| `MeshMessageDeliveriesDecay`      | Float    | Decay factor  for `P₃`.                                               |                                                                       |
| `MeshMessageDeliveriesThreshold`  | Float    | Value for `P₃` below which we start penalizing peers.                 | Should be positive. Value depends on expected message rate for topic. |
| `MeshMessageDeliveriesCap`        | Float    | Maximum value for `P₃`.                                               | Must be >= `MeshMessageDeliveriesThreshold`.                          |
| `MeshMessageDeliveriesActivation` | Duration | Time a peer must be in the mesh before we start applying `P₃` score.  |                                                                       |
| `MeshMessageDeliveryWindow`       | Duration | Time after first delivery that is considered "near-first".            | Should be small, e.g. 1-5 ms.                                         |
| **`P₃b`**                         |          | **Mesh Message Delivery Failures**                                    |                                                                       |
| `MeshFailurePenaltyWeight`        | Weight   | Weight of `P₃b`.                                                      | Should be negative, to penalize failed deliveries.                    |
| `MeshFailurePenaltyDecay`         | Float    | Decay factor for `P₃b`.                                               |                                                                       |
| **`P₄`**                          |          | **Invalid Messages**                                                  |                                                                       |
| `InvalidMessageDeliveriesWeight`  | Weight   | Weight of`P₄`.                                                        | Should be negative, to penalize invalid messages.                     |
| `InvalidMessageDeliveriesDecay`   | Float    | Decay factor for `P₄`.                                                |                                                                       |

### Spam Protection Measures

In order counter spam that elicits responses and consumes resources, some measures have been taken:
- `GRAFT` messages for unknown topics are ignored; in gossipsub v1.0 the router would always
  respond with a `PRUNE`, which opens up an avenue for flooding with spam `GRAFT` messages and
  consuming resources.
- `IWANT` message responses are limited in the number of retransmissions to a certain peer;
  in gossipsub v1.0 the router always responds to `IWANT` messages when the message in the cache.
  In gossipsub v1.1 the router responds a limited number of times to each peer so that `IWANT` spam
  does not cause a signficant drain of resources.
- `IHAVE` messages are capped to a certain number of `IHAVE` messages and aggregate number of message
  IDs advertised per heartbeat, in order to reduce the exposure to floods. If more `IHAVE` advertisements
  are received than the limit (or more messages are advertised than the limit), then additional `IHAVE`
  messages are ignored.
- In flight `IWANT` requests, sent as a response to an `IHAVE` advertisement, are probabilistically tracked.
  For each `IHAVE` advertisement which elicits an `IWANT` request, the router tracks a random message ID
  within the advertised set. If the message is not received (from any peer) within a period of time, then
  a behavioural penalty is applied to the advertising peer through `P₇`.
  This measure helps protect against spam `IHAVE` floods by quickly flagging and graylisting peers
  who advertise bogus message IDs and/or do not follow up to the `IWANT` requests.
- Invalid message spam, either directly transmitted or as a response to an `IHAVE` message is
  penalized by the score function. A peer transmitting lots of spam will quickly get graylisted,
  reducing the surface of spam-induced computation (eg validation). The application can take
  further steps and blacklist the peer if the spam persists after the negative score decays.

### Recommendations for Network Operators

An important issue to consider when deploying gossipsub is the peer discovery mechanism,
which must provide a secure way of discovering new peers.
Prior to gossipsub v1.1, operators were required to utilize an external peer discovery
mechanism to locate peers meshing in particular topics; with gossipsub v1.1 this is now entirely optional and the network can bootstrap
purely through a small set of network entry points (bootstrappers) by utilizing Peer Exchange. In other words, gossipsub 1.1 is now self-sufficient in this regard, as long as the node manages to find at least one peer meshing in the topic of interest.

In order to successfully bootstrap the network without a discovery service, network operators
should
- Create and operate a set of stable bootstrapper nodes, whose addresses are known ahead of time by the application.
- The bootstrappers should be configured without a mesh (ie set `D=Dlo=Dhi=Dout=0`)
  and with Peer Exchange enabled, utilizing Signed Peer Records.
- The application should assign a high application-specific score to the bootstrappers and
  set `AcceptPXThreshold` to a high enough value attainable only by the bootstrappers.

In this manner, the bootstrappers act purely as gossip and peer exchange nodes that facilitate
the formation and maintenance of the network.
Note that the score function is still present in the bootstrappers, which ensures that invalid
messages, colocation, and behavioural penalties apply to misbehaving nodes such that they do
not receive PX or are advertised to the rest of the network.
In addition, network operators may configure the application specific scoring function such
that the bootstrappers enforce further constraints into accepting new nodes (eg protocol
handshakes, staked participation, and so on).
