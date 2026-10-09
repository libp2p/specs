# GossipSub Metrics Specification

> Standardized optional metrics for GossipSub implementations to enable consistent and comparable performance monitoring

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r0, 2025-08-28  |

Authors: [@dennis-tra]

Interest Group: TBD

[@dennis-tra]: https://github.com/dennis-tra

See the [lifecycle document][lifecycle-spec] for context about the maturity level and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md


## Table of Contents

- [GossipSub Metrics Specification](#gossipsub-metrics-specification)
  - [Table of Contents](#table-of-contents)
  - [Motivation](#motivation)
  - [Metric Definitions](#metric-definitions)
    - [Metric Update Semantics](#metric-update-semantics)
  - [Prometheus Export Format](#prometheus-export-format)
    - [Example Prometheus Output](#example-prometheus-output)
  - [Security Considerations](#security-considerations)


## Motivation

GossipSub implementations across different programming languages currently expose varying sets of metrics for observability and performance monitoring. This inconsistency makes it challenging for, e.g., node operators to deploy unified monitoring dashboards across heterogeneous deployments, compare performance characteristics between different implementations, diagnose network health issues using standardized indicators, and create portable alerting rules and runbooks.

This specification defines a standardized set of **optional Prometheus-style metrics** that GossipSub implementations MAY support to enable consistent observability.  The goals of this specification are to define standardized metric names, types, and labels as well as the semantic specifications for when metrics should be updated.

## Metric Definitions

All metrics follow Prometheus naming conventions and use the `gossipsub_` prefix. The following table defines the complete set of standardized metrics:

| Metric Name | Type | Labels | Description |
|-------------|------|--------|--------------|
| **Peer Management** |
| `gossipsub_peers_total` | Gauge | `topic` (optional) | Current number of known peers, optionally segmented by topic |
| `gossipsub_mesh_peers_total` | Gauge | `topic` (required) | Current number of peers in the mesh for each topic |
| `gossipsub_peer_graft_total` | Counter | `topic` (required) | Total number of GRAFT messages sent, by topic |
| `gossipsub_peer_prune_total` | Counter | `topic` (required), `reason` (optional) | Total number of PRUNE messages sent, by topic and optional reason |
| `gossipsub_peer_score` | Histogram | `topic` (optional) | Distribution of peer scores |
| **Message Flow** |
| `gossipsub_message_received_total` | Counter | `topic` (required), `validation_result` (optional) | Total messages received for processing, optionally by validation result |
| `gossipsub_message_delivered_total` | Counter | `topic` (required) | Total messages successfully delivered to local subscribers |
| `gossipsub_message_rejected_total` | Counter | `topic` (required), `reason` (optional) | Total messages rejected during validation, optionally by reason |
| `gossipsub_message_duplicate_total` | Counter | `topic` (required) | Total duplicate messages detected and discarded |
| `gossipsub_message_published_total` | Counter | `topic` (required) | Total messages published by local node |
| `gossipsub_message_latency_seconds` | Histogram | `topic` (optional) | End-to-end message delivery latency in seconds |
| **Protocol Control** |
| `gossipsub_rpc_received_total` | Counter | `message_type` (required) | Total RPC messages received by type (publish, subscribe, unsubscribe, graft, prune, ihave, iwant, idontwant) |
| `gossipsub_rpc_sent_total` | Counter | `message_type` (required) | Total RPC messages sent by type |
| `gossipsub_ihave_sent_total` | Counter | `topic` (required) | Total IHAVE control messages sent per topic |
| `gossipsub_iwant_sent_total` | Counter | `topic` (required) | Total IWANT control messages sent per topic |
| `gossipsub_idontwant_sent_total` | Counter | `topic` (required) | Total IDONTWANT control messages sent per topic |
| **Performance & Health** |
| `gossipsub_heartbeat_duration_seconds` | Histogram | None | Time spent processing each heartbeat operation |
| `gossipsub_peer_throttled_total` | Counter | `reason` (optional) | Total number of times peers have been throttled |
| `gossipsub_backoff_violations_total` | Counter | None | Total attempts to reconnect before backoff period completion |
| `gossipsub_score_penalty_total` | Counter | `penalty_type` (required), `topic` (optional) | Total peer scoring penalties applied by type |

### Metric Update Semantics

**Counters** are incremented when:
- `*_total` metrics: Each time the corresponding event occurs (message sent/received, peer action, etc.)
- Events are counted at the protocol level, not application level

**Gauges** are updated when:
- `*_peers_total`: Peers are added/removed from peer tracking or topic meshes
- Values reflect current state at time of observation

**Histograms** are updated when:
- `gossipsub_peer_score`: During peer scoring operations (recommended buckets: `[-100, -10, -1, 0, 1, 10, 100, +Inf]`)
- `*_latency_seconds`: When latency measurements are available (recommended buckets: `[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, +Inf]`)
- `*_duration_seconds`: When timing operations complete (recommended buckets: `[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, +Inf]`)

## Prometheus Export Format

Implementations MUST export metrics in Prometheus format.

### Example Prometheus Output

```
# HELP gossipsub_mesh_peers_total Current number of peers in the mesh for each topic
# TYPE gossipsub_mesh_peers_total gauge
gossipsub_mesh_peers_total{topic="ipfs-dht"} 8
gossipsub_mesh_peers_total{topic="libp2p-announce"} 12

# HELP gossipsub_message_received_total Total messages received for processing
# TYPE gossipsub_message_received_total counter
gossipsub_message_received_total{topic="ipfs-dht",validation_result="accept"} 1543
gossipsub_message_received_total{topic="ipfs-dht",validation_result="reject"} 23

# HELP gossipsub_heartbeat_duration_seconds Time spent processing each heartbeat operation
# TYPE gossipsub_heartbeat_duration_seconds histogram
gossipsub_heartbeat_duration_seconds_bucket{le="0.001"} 45
gossipsub_heartbeat_duration_seconds_bucket{le="0.005"} 123
gossipsub_heartbeat_duration_seconds_bucket{le="+Inf"} 150
gossipsub_heartbeat_duration_seconds_sum 0.456
gossipsub_heartbeat_duration_seconds_count 150
```

## Security Considerations

TODO: Cardinality Attack: Malicious peers could potentially cause high cardinality by creating many topics or using diverse peer IDs
TODO: Information Disclosure: Topic names in metrics may reveal sensitive information about network usage patterns