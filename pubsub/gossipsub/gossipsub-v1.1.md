# gossipsub v1.1: Security extensions to improve on attack resilience and bootstrapping

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 1A              | Draft          | Active | r1, 2020-03-20  |


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
- [Attack Considerations](#attack-considerations)
- [Protocol extensions](#protocol-extensions)
  - [Peer Exchange on PRUNE](#peer-exchange-on-prune)
    - [Protobuf](#protobuf)
  - [Flood Publishing](#flood-publishing)
  - [Adaptive Gossip Dissemination](#adaptive-gossip-dissemination)
  - [Peer Scoring](#peer-scoring)
    - [Score Thresholds](#score-thresholds)
    - [Heartbeat Maintenance](#heartbeat-maintenance)
    - [The Score Function](#the-score-function)
    - [Topic Parameter Calculation and Decay](#topic-parameter-calculation-and-decay)
      - [P₁: Time in Mesh](#p%E2%82%81-time-in-mesh)
      - [P₂: First Message Deliveries](#p%E2%82%82-first-message-deliveries)
      - [P₃ and P₃b: Mesh Message Delivery](#p%E2%82%83-and-p%E2%82%83b-mesh-message-delivery)
      - [P₄: Invalid Messages](#p%E2%82%84-invalid-messages)
      - [Parameter Decay](#parameter-decay)
    - [Guidelines for Tuning the Scoring Function](#guidelines-for-tuning-the-scoring-function)
  - [Spam Protection Measures](#spam-protection-measures)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Overview

This document specifies extensions to [gossipsub v1.0](gossipsub-v1.0.md) intended to improve
bootstrapping and protocol attack resistance. The extensions change the algorithms that
prescribe local peer behaviour and are fully backwards compatible with v1.0 of the protocol.
Peers that implement these extensions, advertise v1.1 of the protocol using `/meshsub/1.1.0`
as the protocol string.

## Protocol extensions

### Peer Exchange on PRUNE

Gossipsub relies on ambient peer discovery in order to find peers within a topic of interest.
This puts pressure to the implementation of a scalable peer discovery service that
can support the protocol. With Peer Exchange, the protocol can now bootstrap from a small
set of nodes, without relying on an external peer discovery service.

Peer Exchange (PX) kicks in when pruning a mesh because of oversubscription. Instead of simply
telling the pruned peer to go away, the pruning peer _may_ provide a set of other peers where the
pruned peer can connect to reform its mesh (see Peer Scoring below).
In addition, both the pruned and the pruning peer add a backoff period from each other, within which
they will not try to regraft. Both the pruning and the pruned peer will immediate prune a `GRAFT`
within the backoff period.
The recommended duration for the backoff period is 1 minute, while the recommended number of peers
to exchange is equal to `D` so that the pruned peer can form a full mesh.

In order to implement PX, we extend the `PRUNE` control message to include an optional set of
peers the pruned peer can connect to. This set of peers includes the Peer ID and a [_signed_ peer
record](https://github.com/libp2p/specs/pull/217) for each peer exchanged.
In order to facilitate the transition to the usage of signed peer records within the libp2p ecosystem,
the emitting peer is allowed to omit the signed peer record if it doesn't have one.
In this case, the pruned peer will have to utilize an external service to discover addresses for
the peer, eg the DHT.

#### Protobuf

The `ControlPrune` message is extended with a `peer` field as follows.

```protobuf
message ControlPrune {
	optional string topicID = 1;
	repeated PeerInfo peers = 2; // gossipsub v1.1 PX
}

message PeerInfo {
	optional bytes peerID = 1;
	optional bytes signedPeerRecord = 2;
}
```

### Flood Publishing

In gossipsub v1.0 a freshly published message is propagated through the mesh or the fanout map
if the publisher is not subscribed to the topic. In gossipsub v1.1 publishing is (optionally)
done by publishing the message to all connected peers with a score above a publish threshold
(see Peer Scoring below).

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

The parameter controlling the emission of gossip is called the gossip _factor_. When a node wants
to emit gossip during the heartbeat, first it selects all peers with a peer score above a gossip
threshold (see Peer Scoring below). From these peers, it randomly selects gossip factor peers with
a minimum of `D_lazy`, and emits gossip to the selected peers.

The recommended value for the gossip factor is `0.25`, which with the default of 3 rounds of gossip
per message ensures that each peer has at least 50% chance of receiving gossip about a message.
More specifically, for 3 rounds of gossip, the probability of a peer _not_ receiving gossip about
a fresh message is `(3/4)³=27/64=0.421875`. So each peer receives gossip about a fresh message with
a `0.578125` probability.

This behaviour is prescribed to counter sybil attacks and ensures that a message from a honest
node propagates in the network with high probability.

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

#### Heartbeat Maintenance

The score is checked explicitly during heartbeat maintenance such that:
- Peers with negative score are pruned from all meshes.
- When pruning because of oversubscription, the peer keeps the best `D_score` scoring peers and
  selects the remaining peers to keep at random. This protects the mesh from takeover attacks
  and ensures that the best scoring peers are kept in the mesh. At the same time, we do keep some
  peers as random so that the protocol is responsive to new peers joining the mesh.
- When selecting peers to graft because of undersubscription, peers with a negative score are ignored.

#### The Score Function

The score function is a weighted mix of parameters, 4 of them per topic and 2 of them globally
applicable.
```
Score(p) = Σtᵢ*(w₁(tᵢ)*P₁(tᵢ) + w₂(tᵢ)*P₂(tᵢ) + w₃(tᵢ)*P₃(tᵢ) + w₃b(tᵢ)*P₃b(tᵢ) + w₄(tᵢ)*P₄(tᵢ)) + w₅*P₅ + w₆*P₆
```
where `tᵢ` is the topic weight for each topic where per topic parameters apply.

The parameters are defined as follows:
- P₁: time in mesh for a topic. This is the time a peer has been in the mesh, capped to a small value
  and mixed with a small positive weight. This is intended to boost peers already in the mesh so that
  they are not prematurely pruned because of oversubscription.
- P₂: first message deliveries for a topic. This is the number of message first delivered by the peer
  in the topic, mixed with a positive weight. This is intended to reward peers who first forward a
  valid message.
- P₃: mesh message delivery rate for a topic. This parameter is a threshold for the expected message
  delivery rate within the mesh in the topic. If the number of deliveries is above the threshold,
  then the value is 0. If the number is below the threshold, then the value of the parameter is
  the square of the deficit.
  This is intended to penalize peers in the mesh who are not delivering the expected
  number of messages so that they can be removed from the mesh. The parameter is mixed with a negative
  weight.
- P₃b: mesh message delivery failures for a topic. This is a sticky parameter that counts the number
  of mesh message delivery failures. Whenever a peer is pruned with a negative score, the parameter
  is augmented by the rate deficit at the time of prune. This is intended to keep history of prunes
  so that a peer that was pruned because of underdelivery cannot quickly get regrafted into the
  mesh. The parameter is mixed with negative weight.
- P₄: invalid messages for a topic. This is he number of invalid messages delivered in the topic.
  This is intended to penalize peers who transmit invalid messages, according to application specific
  validation rules. It is mixed with a negative weight.
- P₅: application specific score. This is the score component assigned to the peer by the application
  itself, using application specific rules. The weight is positive, but the parameter itself has an
  arbitrary real value, so that the application can signal misbehaviour with a negative score or gate
  peers before an application specific handshake is completed.
- P₆: IP colocation factor. This parameter is a threshold for the number of peers using the same IP
  address. If the number of peers in the same IP exceeds the threshold, then the value is the square
  of the surpluss, otherwise it is 0. This is intended to make it difficult to carry out sybil attacks
  by using a small number of IPs. The parameter is mixed with a negative weight.

#### Topic Parameter Calculation and Decay

The topic parameters are implemented using counters maintained internally by the router
whenever an event of interest occurs. The counters _decay_ periodically so that their values are
not continuously increasing and ensure that a large positive or negative score isn't sticky for
the lifetime of the peer.

##### P₁: Time in Mesh

In order to compute P₁, the router records the time when the peer is GRAFTed. The time in mesh
is calculated lazily during the decay update to avoid a large number of calls to `gettimeofday`.
The parameter value is the division of the time ellapsed since the GRAFT with an application
configurable quantum.

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

In order to compute P₂, the router maintains a counter that increments whenever a message
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

In order to compute P₃, the router maintains a counter that increments whenever a first
or near-first message delivery occurs in the topic by a peer in the mesh.  A near-first message
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

In order to compute P₄, the router maintains a counter that increments whenever a message fails
validation. The counter is uncapped.

In pseudo-go:
```go
// counter updated every time a message fails validation
var invalidMessageDeliveries float64

// counter update
invalidMessageDeliveries += 1

// P₄
p4 := invalidMessageDeliveries
```

##### Parameter Decay

The counters associated with P₂, P₃, P₃b, and P₄ decay periodically by multiplying with a configurable
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

`TBD`: We are currently developing a multiple types of simulations that will inform us on how to best recommend tunning the Scoring function. We will update this section once that work is complete

### Spam Protection Measures

In order counter spam that elicits responses and consumes resources, some measures have been taken:
- `GRAFT` messages for unknown topics are ignored; in gossipsub v1.0 the router would always
  respond with a `PRUNE`, which opens up an avenue for flooding with spam `GRAFT` messages and
  consuming resources.
- `IWANT` message responses are limited in the number of retransmissions to a certain peer;
  in gossipsub v1.0 the router always responds to `IWANT` messages when the message in the cache.
  In gossipsub v1.1 the router responds a limited number of times to each peer so that `IWANT` spam
  does not cause a signficant drain of resources.
- Invalid message spam, either directly transmitted or as a response to an `IHAVE` message is
  penalized by the score function. A peer transmitting lots of spam will quickly get graylisted,
  reducing the surface of spam-induced computation (eg validation). The application can take
  further steps and blacklist the peer if the spam persists after the negative score decays.