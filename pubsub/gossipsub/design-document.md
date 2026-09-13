# Gossipsub v1.4 Large Message Propagation — Design Document

| Document Type   | Design Document                                      |
| --------------- | ---------------------------------------------------- |
| Specification   | [gossipsub-v1.4.md](./gossipsub-v1.4.md)             |
| Status          | Living Document — tracks design rationale and prototype learnings |
| Author          | [@NomzzNJS](https://github.com/NomzzNJS)             |
| Created         | 2026-05-16                                           |

---

## 1. Executive Summary

This design document captures the architectural rationale, prototype analysis,
and design decisions behind the Gossipsub v1.4 specification for large message
propagation. It serves as the companion reference to the normative specification
in [gossipsub-v1.4.md](./gossipsub-v1.4.md).

The design synthesizes findings from two independent prototype implementations
(**nim-libp2p** by the Vac/Logos team and **py-libp2p**) and two peer-reviewed
research papers to define four complementary mechanisms: **Message
Fragmentation**, **Message Staggering**, **PREAMBLE**, and **IMRECEIVING**.

---

## 2. Problem Analysis

### 2.1 The Store-and-Forward Bottleneck

Standard Gossipsub uses a store-and-forward relay model: each peer must fully
receive a message before forwarding it to mesh neighbors. For a message of size
`L` bytes traversing a path of `h` hops, each with link data rate `R`:

```
Total store-and-forward delay = h × (L / R)
```

For a 1 MB message across 6 hops on a 10 Mbps link:
- Per-hop transmission time: ~0.8 seconds
- Cumulative delay: ~4.8 seconds (store-and-forward alone)

This multiplicative delay is the primary scalability bottleneck for large
messages.

### 2.2 The IDONTWANT Timing Gap

Gossipsub v1.2 introduced `IDONTWANT` — a control message sent *after* full
reception to suppress further sends. However, for large messages:

```
Timeline (without v1.4):
  t=0    Peer A starts sending 1MB to Peer B
  t=0    Peer A simultaneously starts sending 1MB to Peer C
  t=0.8s Peer B finishes receiving, sends IDONTWANT
  t=0.8s Peer C finishes receiving (REDUNDANT — too late!)
```

The fundamental issue: simultaneous sends mean `IDONTWANT` always arrives too
late. The entire message has already been transmitted redundantly.

### 2.3 Bandwidth Amplification

In a standard gossipsub mesh with degree `D` (default 6–12), a peer forwards
every message to all `D` mesh neighbors simultaneously. For a 1 MB message
with `D=8`:

- **Ideal bandwidth** (no redundancy): 1 MB per peer
- **Actual bandwidth** (with duplicates): up to 8 MB per peer outbound
- **Network-wide amplification**: O(D) redundancy factor per hop

Research measurements (arXiv:2504.10365) show this results in bandwidth
utilization that scales poorly with message size, becoming the dominant cost
above ~64 KiB.

### 2.4 Real-World Impact

| System | Payload Size | Impact |
|--------|-------------|--------|
| Ethereum blocks (post-EIP-4844) | 128 KiB – 1 MB+ (with blobs) | Block propagation latency directly affects attestation timing and chain finality |
| Distributed AI model updates | 1 MB – 100 MB | Gradient aggregation round-trip time limits training throughput |
| Waku relay messages | Variable, growing | Store-and-forward delays compound across relay hops |
| State snapshots | 10 MB+ | Sync time for new nodes joining the network |

---

## 3. Prototype Analysis

### 3.1 nim-libp2p Prototype (Vac/Logos)

**Repository**: [vacp2p/nim-libp2p](https://github.com/vacp2p/nim-libp2p)

The Vac research team developed the primary proof-of-concept implementation in
nim-libp2p, testing via the Shadow discrete-event network simulator.

#### Key Implementation Details

- **Stagger-send branches**: Experimental branches (e.g., `staggersend`)
  implemented sequential peer forwarding with configurable group sizes (1, 2, 3,
  4 parallel sends).
- **Fragment relay**: Fragments are forwarded as individual protocol messages
  without waiting for full reassembly.
- **PREAMBLE/IMRECEIVING**: Implemented as new `ControlMessage` fields, sent
  inline with the existing gossipsub RPC framing.
- **Shadow simulator testing**: Evaluated across 2,000–12,000 node networks
  with message sizes from 200 KB to 1 MB.

#### Prototype Results (Shadow Simulator)

| Configuration | Latency Reduction | Bandwidth Reduction |
|---------------|-------------------|---------------------|
| Staggering only (1 parallel) | ~20% | ~30% |
| Fragmentation only (64 KB) | ~56% | ~15% |
| Stagger + Fragment | ~64% | ~45% |
| Stagger + Fragment + PREAMBLE + IMRECEIVING | Up to 35% additional | Up to 61% total |

#### Design Lessons from nim-libp2p

1. **Stagger interval sensitivity**: Too short (~50 ms) provides insufficient
   time for IDONTWANT propagation. Too long (~500 ms) adds excessive total
   relay time. The 200 ms default was empirically determined to balance these
   tradeoffs across typical mesh topologies.

2. **Fragment size tradeoffs**: Smaller fragments (16 KB) increase protocol
   overhead (more fragment headers). Larger fragments (256 KB) reduce the
   pipeline parallelism benefit. The 64 KB default provides the best
   latency/overhead balance.

3. **Fragment forwarding is critical**: The key latency win comes from
   forwarding fragments *before* full reassembly. Without this, fragmentation
   only reduces individual transmission sizes but doesn't eliminate
   store-and-forward delay accumulation.

4. **IMRECEIVING fills the IDONTWANT gap**: In the nim-libp2p prototype,
   IMRECEIVING reduced redundant transmissions by an additional 20–30% beyond
   what IDONTWANT alone achieved, because it provides *immediate* suppression
   at the start of reception rather than after completion.

### 3.2 py-libp2p Prototype

**Repository**: [libp2p/py-libp2p](https://github.com/libp2p/py-libp2p)

The py-libp2p implementation focused on application-layer fragmentation and
reassembly patterns, demonstrating the feasibility of the approach in a
dynamically-typed, event-loop-based runtime.

#### Key Implementation Characteristics

- **asyncio-based fragment relay**: Fragments are handled as individual async
  tasks, enabling natural pipeline parallelism via Python's event loop.
- **Reassembly buffer management**: Implemented with per-peer, per-message
  dictionaries keyed by `(peer_id, message_id)` with timeout-based cleanup.
- **IDONTWANT integration**: Built on py-libp2p's existing v1.2 support,
  extending `dont_send_message_ids` to handle IMRECEIVING signals.

#### Design Lessons from py-libp2p

1. **Memory management is critical**: Without `max_pending_fragments` limits,
   a malicious peer can exhaust memory by sending fragments for many fake
   message IDs. The prototype demonstrated the need for both per-peer and
   global reassembly buffer limits.

2. **Fragment ordering is not guaranteed**: Network conditions can deliver
   fragments out of order. The reassembly buffer must handle arbitrary
   insertion order, not assume sequential delivery.

3. **Timeout tuning matters**: The 30-second `fragment_timeout` was chosen to
   accommodate high-latency network conditions while preventing indefinite
   resource consumption.

---

## 4. Design Decisions and Rationale

### 4.1 Four Mechanisms, Not One

**Decision**: Include all four mechanisms (fragmentation, staggering, PREAMBLE,
IMRECEIVING) as a unified extension rather than four separate extensions.

**Rationale**: The research demonstrates that these mechanisms are
*synergistic* — each one amplifies the effectiveness of the others:

```
                    PREAMBLE
                   (announces message)
                        │
                        ▼
              ┌─────────────────────┐
              │   Receiver learns   │
              │   message is coming │
              └─────────┬───────────┘
                        │
              ┌─────────▼───────────┐
              │   Sends IMRECEIVING │──── Immediate suppression
              │   to mesh peers     │     (no waiting for full rx)
              └─────────┬───────────┘
                        │
              ┌─────────▼───────────┐
              │   Staggered sends   │──── Gives time for IDONTWANT
              │   to remaining peers│     + IMRECEIVING to propagate
              └─────────┬───────────┘
                        │
              ┌─────────▼───────────┐
              │   Fragmented relay  │──── Pipeline parallelism
              │   across hops       │     eliminates store-and-forward
              └─────────────────────┘
```

Deploying them independently yields diminishing returns. Combined, they achieve
the full 61% bandwidth reduction and 35% latency improvement.

### 4.2 Protocol Version Bump (v1.4) vs. Extension-Only

**Decision**: Assign a new protocol version (`/meshsub/1.4.0`) rather than
registering only as a v1.3 extension.

**Rationale**:
- The scope introduces **3 new protobuf message types** and **2 new control
  message fields** — comparable to v1.2's scope (which introduced IDONTWANT).
- A version bump makes capability detection straightforward: peers can check
  the protocol ID to know if large message handling is supported.
- The v1.3 extension mechanism is still used for fine-grained advertisement
  (`largeMessageHandling = 11` in `ControlExtensions`).

### 4.3 Fragment Size: 64 KiB Default

**Decision**: Default `fragment_size` = 65536 bytes (64 KiB).

**Rationale**:

| Fragment Size | Pros | Cons |
|---------------|------|------|
| 16 KiB | Maximum parallelism | High per-fragment overhead; many small RPC messages |
| 32 KiB | Good parallelism | Moderate overhead |
| **64 KiB** | **Best latency/overhead balance (empirically validated)** | **Moderate parallelism** |
| 128 KiB | Low overhead | Reduced pipeline benefit; closer to store-and-forward |
| 256 KiB | Minimal overhead | Minimal pipeline benefit |

The 64 KiB default aligns with:
- Common network MTU multiples (avoids IP fragmentation at lower layers)
- The research paper defaults used in Shadow simulations
- Typical OS socket buffer sizes

### 4.4 Configurable Thresholds

**Decision**: All thresholds (`fragmentation_threshold`, `stagger_threshold`,
`preamble_threshold`) are configurable parameters, not hard-coded values.

**Rationale**: Different deployments have different message size distributions:
- Ethereum networks: most messages are small (transactions), with periodic
  large bursts (blocks with blobs)
- AI coordination: consistently large payloads
- General pubsub: unpredictable mix

Application operators must be able to tune when each mechanism activates.

### 4.5 IMRECEIVING as Advisory (Not Mandatory)

**Decision**: IMRECEIVING is advisory — a peer MAY still send after receiving
IMRECEIVING, and doing so MUST NOT be penalized.

**Rationale**:
- **Probabilistic nature**: IMRECEIVING signals *intent* to receive, not
  *confirmed* reception. The reception might fail (network error, timeout).
- **Preventing censorship**: If IMRECEIVING were binding, a malicious peer
  could send IMRECEIVING for messages it never intends to receive, effectively
  censoring message delivery to its neighbors.
- **Consistent with IDONTWANT**: v1.2's IDONTWANT uses the same advisory
  model. Maintaining consistency simplifies implementation.

### 4.6 Fragment Forwarding Before Validation

**Decision**: Fragments MAY be forwarded before the full message is reassembled
and validated. Forwarded fragments are *tentatively valid*.

**Rationale**: This is the single most important design decision for latency
reduction. Waiting for full reassembly before forwarding would eliminate the
pipeline parallelism benefit entirely. The tradeoff:

- **Risk**: A peer may forward fragments of a message that ultimately fails
  validation, wasting bandwidth.
- **Mitigation**: Scoring penalties (P₄ from v1.1) are applied retroactively
  to the original sender upon reassembly failure.
- **Bounded risk**: Fragment forwarding only occurs between v1.4-capable peers.
  Non-v1.4 peers always receive fully validated messages.

---

## 5. Protocol Flow Diagrams

### 5.1 Complete v1.4 Message Flow (Happy Path)

```
Publisher          Peer A             Peer B             Peer C
    │                │                  │                  │
    │  Large msg M   │                  │                  │
    │  (512 KB)      │                  │                  │
    │                │                  │                  │
    │──PREAMBLE(M)──▶│                  │                  │
    │──PREAMBLE(M)───────────────────────────────────────▶│
    │──PREAMBLE(M)──────────────────▶│                     │
    │                │                  │                  │
    │                │  ◄──IMRECEIVING(M)──(Peer B tells   │
    │                │     C it's getting M)               │
    │                │                  │──IMRECEIVING(M)─▶│
    │                │                  │                  │
    │──Frag[0]──────▶│                  │                  │
    │  (stagger      │──Frag[0]────────▶│                  │
    │   200ms wait)  │                  │──Frag[0]────────▶│
    │                │                  │                  │
    │──Frag[1]──────▶│                  │                  │
    │                │──Frag[1]────────▶│                  │
    │                │                  │──Frag[1]────────▶│
    │  ...           │  ...             │  ...             │
    │                │                  │                  │
    │──Frag[7]──────▶│                  │                  │
    │                │  IDONTWANT(M)───▶│                  │
    │                │  (A has full M)  │                  │
    │                │──Frag[7]────────▶│                  │
    │                │                  │──Frag[7]────────▶│
    │                │                  │                  │
    │                │  Reassemble M    │  Reassemble M    │
    │                │  Validate M ✓    │  Validate M ✓    │
```

### 5.2 Redundancy Suppression Flow

```
             Without v1.4                    With v1.4
    ┌──────────────────────────┐   ┌──────────────────────────┐
    │                          │   │                          │
    │   Peer X  ──1MB──▶ B    │   │   Peer X ──PREAMBLE──▶ B │
    │   Peer Y  ──1MB──▶ B    │   │   B ──IMRECEIVING──▶ Y   │
    │   Peer Z  ──1MB──▶ B    │   │   Peer Y: skip B         │
    │                          │   │   Peer Z: skip B         │
    │   B receives 3 copies    │   │   B receives 1 copy      │
    │   Bandwidth: 3 MB        │   │   Bandwidth: 1 MB        │
    │                          │   │                          │
    └──────────────────────────┘   └──────────────────────────┘
```

### 5.3 Fragment Reassembly State Machine

```
                    ┌──────────────┐
                    │    IDLE      │
                    │ (no state)   │
                    └──────┬───────┘
                           │ Receive first fragment
                           │ OR PREAMBLE
                           ▼
                    ┌──────────────┐
              ┌────▶│  RECEIVING   │◀─── Receive fragment
              │     │              │     (store in buffer)
              │     └──────┬───────┘
              │            │
              │     ┌──────┴───────┐
              │     │              │
              ▼     ▼              ▼
    ┌──────────────┐    ┌──────────────┐
    │   TIMEOUT    │    │  COMPLETE    │
    │              │    │              │
    │ Discard      │    │ Reassemble   │
    │ fragments    │    │ Validate     │
    │ Clear buffer │    │ Deliver/Fwd  │
    └──────────────┘    └──────────────┘
```

---

## 6. Wire Format Design

### 6.1 Protobuf Integration Strategy

The v1.4 messages integrate into the existing gossipsub RPC framing defined in
[extensions.proto](./extensions/extensions.proto):

```
RPC
├── subscriptions[]        (existing)
├── publish[]              (existing)
├── control                (existing ControlMessage)
│   ├── ihave[]            (v1.0)
│   ├── iwant[]            (v1.0)
│   ├── graft[]            (v1.0)
│   ├── prune[]            (v1.0)
│   ├── idontwant[]        (v1.2)
│   ├── extensions         (v1.3)
│   ├── preamble[]         (v1.4 — NEW)
│   └── imreceiving[]      (v1.4 — NEW)
├── partial                (extension)
└── largeMessageFragments[] (v1.4 — NEW)
```

**Design choice**: `LargeMessageFragment` is placed in the `RPC` message (not
`ControlMessage`) because fragments carry application data payload, not control
signaling. This follows the pattern of `publish[]` (which also carries data)
vs. `ControlMessage` (which carries routing metadata).

### 6.2 Field Number Allocation

| Message | Field | Number | Rationale |
|---------|-------|--------|-----------|
| `ControlExtensions.largeMessageHandling` | bool | 11 | Next canonical extension after `partialMessages` (10) |
| `ControlMessage.preamble` | repeated | 7 | Next after `extensions` (6) |
| `ControlMessage.imreceiving` | repeated | 8 | Sequential after `preamble` (7) |
| `RPC.largeMessageFragments` | repeated | 12 | Next available after `partial` (10), skipping 11 |

Canonical field numbers (small integers, 1-byte varint encoding) are used
because this is a formal protocol version, not an experimental extension.

### 6.3 Message Size Overhead Analysis

| Control Message | Encoded Size (typical) | When Sent |
|-----------------|------------------------|-----------|
| `ControlPreamble` | ~40 bytes (32B msgID + 8B size + topic) | Once per large message per peer |
| `ControlImReceiving` | ~34 bytes (32B msgID + overhead) | Once per large message per peer |
| `LargeMessageFragment` header | ~44 bytes (32B msgID + indices + topic) | Per fragment |

For a 512 KB message split into 8 fragments:
- Fragment header overhead: 8 × 44 = 352 bytes (0.07% of payload)
- PREAMBLE overhead: ~40 bytes per peer (negligible)
- IMRECEIVING overhead: ~34 bytes per peer (negligible)

Total protocol overhead: < 0.1% of payload size.

---

## 7. Interaction with Existing Protocol Mechanisms

### 7.1 Interaction Matrix

| Existing Mechanism | Interaction with v1.4 | Notes |
|--------------------|----------------------|-------|
| **IHAVE/IWANT** (v1.0) | Compatible. IHAVE/IWANT operate on full message IDs, not fragments. A peer that receives a PREAMBLE MAY delay IWANT responses. | |
| **Peer Scoring** (v1.1) | Extended. P₄ (Invalid Messages) applies to reassembly failures. P₇ (Behavioural Penalty) applies to PREAMBLE/IMRECEIVING abuse. | |
| **IDONTWANT** (v1.2) | Synergistic. Staggering is specifically designed to give IDONTWANT time to propagate. IMRECEIVING supplements IDONTWANT during the reception window. | |
| **Extensions** (v1.3) | Used for capability advertisement via `largeMessageHandling` in `ControlExtensions`. | |
| **Message Cache** (v1.0) | Unchanged. Only fully reassembled messages enter `mcache`. | |
| **Heartbeat** (v1.0) | Extended. Heartbeat now also prunes expired `receiving_messages` and fragment buffers. | |

### 7.2 Backwards Compatibility Matrix

| Sender | Receiver | Behavior |
|--------|----------|----------|
| v1.4 | v1.4 | Full pipeline: PREAMBLE → IMRECEIVING → staggered fragments |
| v1.4 | v1.0–v1.3 | v1.4 sender waits for full reassembly, sends complete message |
| v1.0–v1.3 | v1.4 | v1.4 receiver operates normally (no fragmentation) |
| v1.0–v1.3 | v1.0–v1.3 | No change (existing behavior) |

---

## 8. Security Analysis

### 8.1 Threat Model

| Threat | Attack Vector | Mitigation |
|--------|---------------|------------|
| **Fragment flooding** | Send many fragments for non-existent messages | `max_pending_fragments` (16 per peer), global memory limit, P₄ penalty on reassembly failure |
| **PREAMBLE spam** | Send PREAMBLEs without follow-up data | `fragment_timeout` (30s) + P₇ behavioral penalty + rate limiting |
| **IMRECEIVING abuse** | Falsely claim to be receiving messages | Advisory nature limits impact; entries pruned during heartbeat; fallback via IHAVE/IWANT gossip |
| **Fragment injection** | Inject malicious fragments into legitimate reassembly | Fragments are keyed by `(sender, messageID)` — an attacker would need to predict the message ID and impersonate the sender |
| **Memory exhaustion** | Exhaust reassembly buffer memory across many peers | Per-peer limits + global memory cap + timeout-based cleanup |

### 8.2 Resource Consumption Bounds

For an implementation with default parameters:

```
Per-peer reassembly memory (worst case):
  max_pending_fragments × fragmentation_threshold = 16 × 64 KiB = 1 MB

Per-peer with maximum message size (1 MB messages):
  16 × 1 MB = 16 MB

Global limit recommendation:
  Total peers × per-peer limit, capped at a configurable maximum
  (e.g., 256 MB for a node with 50 mesh peers)
```

---

## 9. Performance Expectations

### 9.1 Expected Improvements (from Shadow Simulations)

| Metric | Baseline (v1.2) | With v1.4 | Improvement |
|--------|-----------------|-----------|-------------|
| Bandwidth per 1 MB message (D=8) | ~8 MB/peer outbound | ~3.1 MB/peer outbound | **~61% reduction** |
| Dissemination latency (1 MB, 10K nodes) | ~12 seconds | ~7.8 seconds | **~35% reduction** |
| Redundant message copies per peer | ~4.2 | ~1.3 | **~69% reduction** |

### 9.2 Parameter Sensitivity

| Parameter | Low Value Effect | High Value Effect | Sweet Spot |
|-----------|-----------------|-------------------|------------|
| `stagger_interval` | IDONTWANT can't propagate in time | Total relay time increases | 150–250 ms |
| `fragment_size` | High header overhead | Reduced pipeline benefit | 32–128 KiB |
| `fragment_timeout` | Premature discard of slow transfers | Prolonged memory usage | 15–60 seconds |

---

## 10. Implementation Guidance

### 10.1 Recommended Implementation Order

For implementers adding v1.4 support to an existing gossipsub implementation:

1. **IDONTWANT integration check** — Ensure v1.2 IDONTWANT is fully
   implemented and the `dont_send_message_ids` infrastructure exists.
2. **PREAMBLE + IMRECEIVING** — Easiest to implement; immediate bandwidth
   benefit with minimal code changes.
3. **Message Staggering** — Modify the forwarding loop to be sequential with
   delays. Requires async/timer infrastructure.
4. **Message Fragmentation** — Most complex; requires reassembly buffers,
   timeout management, and fragment forwarding logic.

### 10.2 Testing Recommendations

- **Unit tests**: Fragment/reassemble round-trip, out-of-order delivery,
  timeout cleanup, PREAMBLE→IMRECEIVING flow.
- **Integration tests**: Mixed v1.4/v1.2 mesh, large message delivery
  confirmation, scoring penalty verification.
- **Simulation**: Shadow simulator with 1,000+ nodes, varying message sizes
  (64 KiB – 2 MB), varying mesh degrees.

---

## 11. References

- [1] M. U. Farooq, T. Cizain, D. Kaiser. "Staggering and Fragmentation for
  Improved Large Message Handling in libp2p GossipSub." arXiv:2504.10365, 2025.
- [2] M. U. Farooq, D. Kaiser. "PREAMBLE and IMRECEIVING for Improved Large
  Message Handling in libp2p GossipSub." arXiv:2505.17337, 2025.
- [3] vacp2p/nim-libp2p — https://github.com/vacp2p/nim-libp2p
- [4] libp2p/py-libp2p — https://github.com/libp2p/py-libp2p
- [5] Vac Research Blog — https://vac.dev/rlog/gossipsub-stagger-idontwant/
- [6] gossipsub v1.2 (IDONTWANT) —
  https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/gossipsub-v1.2.md
- [7] gossipsub v1.3 (Extensions) —
  https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/gossipsub-v1.3.md
- [8] dst-gossipsub-test-node (Shadow testing) —
  https://github.com/vacp2p/dst-gossipsub-test-node
