# gossipsub v1.1: gossipsub extensions to improve bootstrapping and attack resistance

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

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

---

## Overview

This document specifies extensions to [gossipsub v1.0](gossipsub-v1.0.md) intended to improve
bootstrapping and protocol attack resistant. The extensions change the algorithms that
prescribe local peer behaviour and are fully backwards compatible with v1.0 of the protocol.
Peers that implement these extensions, advertise v1.1 of the protocol using `/meshsub/1.1.0`
as the protocol string.

## Peer Exchange

Gossipsub relies on ambient peer discovery in order to find peers within a topic of interest.
This puts pressure to the implementation of a scalable peer discovery service that
can support the protocol. With Peer Exchange, the protocol can now bootstrap from a small
set of nodes, without relying on an external peer discovery service.

Peer Exchange (PX) kicks in when pruning a mesh because of oversubscription. Instead of simply
telling the pruned peer to go away, the pruning peer provides a set of other peers where the
pruned peer can connect to reform its mesh. In addition, both the pruned and the pruning peer
add a backoff period from each other, within which they will not try to regraft. Both the pruning
and the pruned peer will immediate prune a `GRAFT` within the backoff period.
The recommended duration for the back period is 1 minute.

In order to implement PX, we extend the `PRUNE` control message to include an optional set of
peers the pruned peer can connect to. This set of includes the Peer ID and a [_signed_ peer
record](https://github.com/libp2p/specs/pull/217) for each peer exchanged.
In order to facilitate transion to the usage of signed peer records within the libp2p ecosystem,
the emitting peer is allowed to omit the signed peer record if it doesn't have one.
In this case, the pruned peer will have to utilize an external service to discover addresses for
the peer, eg the DHT.

### Protobuf Changes

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

## Flood Publishing

## Adaptive Gossip Dissemination

## Peer Scoring
