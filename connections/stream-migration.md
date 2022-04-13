# Stream migration

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r0, 2022-04-13  |

Authors: [@marcopolo]

Interest Group: TODO
## Introduction

A peer may have many connections open for another peer and may be transmitting
data on less optimal connections. For example a peer could be connected to
another peer both directly and via a relay. In that case we'd like to move any
streams from the relay over to the the better direct connection. A similar
argument can be made with QUIC and TCP.

This protocol attempts to solve the problem of how to seamlessly move a stream
from one connection to another. This protocol also enables the peer to prune
excess connections since they will no longer be used.

## Requirements

1. Transport agnostic. Really, this means migrating at the stream level.
1. Minimal overhead. Overhead should be at most a small per-stream cost (no additional framing, etc.)
1. No interruption. Reading/writing should be continuous.
1. Transparent. Applications using migratable streams shouldn't notice anything.
1. Correct. There can't be any ambiguity (one side believing the migration happened, the other side disagreeing, etc.).

## The Protocol
The goal of the protocol is to move traffic from one stream to another
seamlessly. The final state of the new stream should be the same as the initial
state of the old stream.

![stream-migration](./stream-migration/stream-migration.svg)

<details>
  <summary>Instructions to reproduce diagram</summary>

``` plantuml
@startuml stream-migration
skinparam sequenceMessageAlign center
entity Initiator
entity Responder

note over Initiator, Responder: Assume at least 2 connections.

Initiator <-> Responder: <b>Connection 1; stream A</b>
Initiator <-> Responder: <b>Connection 2</b>

== Stream Migration ==

note over Initiator, Responder: Migrate <b>Stream A</b> to <b>Stream B</b>

Initiator -> Responder: <b>Stream A:</b> Start stream migration, this stream is <b>id=A</b>

Initiator -> Responder: Open new stream on <b>Connection 2</b>. Call this <b>Stream B</b>

Initiator -> Responder: <b>Stream B:</b> Migrate stream with <b>id=A</b> to this stream
Initiator <- Responder: <b>Stream B:</b> Ack Migrate

note over Responder
    Treat any ""EOF"" on <b>stream A</b> as a signal
    that it should continue reading on <b>stream B</b>
end note


note over Initiator
    Close <b>stream A</b> for writing.
    Will only write to <b>stream B</b> from now on.
end note

Initiator -> Responder: <b>Stream A:</b> ""EOF""

note over Responder
    When <i>Responder</i> reads ""EOF"" on <b>stream A</b>
    it will close <b>stream A</b> for writing.
    It will only write to <b>stream B</b> from now on.
end note

Initiator <- Responder: <b>Stream A:</b> ""EOF""

note over Initiator
    Treat any ""EOF"" on <b>stream A</b> as a signal
    that it should continue reading on <b>stream B</b>
end note

note over Initiator, Responder
    At this point <b>stream A</b> is closed for writing on
    both sides, and both sides have read up to ""EOF"".
    <b>stream A</b> has been fully migrated to <b>stream B</b>
end note

@enduml
```

To generate:
```bash
plantuml stream-migration.md -o stream-migration -tsvg
```
</details>

Note: some of these steps may be pipelined.

### Resets

If either stream is "reset" before both ends are closed, both streams must be
reset and the stream as a whole should be considered "aborted" (reset).

### Half closed streams

The final migrated stream should loook the same as the initial stream. If the
initial stream `A` was half closed, then the final migrated stream `B` should
also be half closed. Note this may involve an extra step by one of the nodes.
If a node, when trying to close writes to its old stream, notices that it was
already closed, it should also close the new stream for writing. Specifically
imagine the following case.


![stream-migration-half-closed](./stream-migration/stream-migration-half-closed.svg)

<details>
  <summary>Instructions to reproduce diagram</summary>
``` plantuml
@startuml stream-migration-half-closed
skinparam sequenceMessageAlign center
entity Initiator
entity Responder

note over Responder: <b>Stream A</b> is closed for writing

== Stream Migration ==

note over Initiator, Responder: Migrate <b>Stream A</b> to <b>Stream B</b>

Initiator -> Responder: <b>Stream A:</b> Start stream migration, this stream is <b>id=A</b>

Initiator -> Responder: Open new stream on <b>Connection 2</b>. Call this <b>Stream B</b>

Initiator -> Responder: <b>Stream B:</b> Migrate stream with <b>id=A</b> to this stream
Initiator <- Responder: <b>Stream B:</b> Ack Migrate

note over Initiator
    Close <b>stream A</b> for writing.
    Will only write to <b>stream B</b> from now on.
end note


note over Initiator
    We have already seen the ""EOF"" on
    <b>Stream A</b> from <i>Responder</i>
    So we continue reading on <b>stream B</b>
end note

Initiator -> Responder: <b>Stream A:</b> ""EOF""

note over Responder
    Treat ""EOF"" on <b>stream A</b> as a signal to close <b>stream A</b> for
    writing and continue writing on <b>stream B</b>. However stream A was
    already closed (before migration), so we close <b>stream B</b> as well here.
end note
Initiator <- Responder: <b>Stream B:</b> ""EOF""


note over Initiator, Responder: Stream A is now migrated to Stream B
@enduml
```
To generate:
```bash
plantuml stream-migration.md -o stream-migration -tsvg
```
</details>

The reverse case where the Initiator's stream is closed for writing is the same
as above, but mirrored.

## Picking the best connection

Moving streams from one connection to another involves picking which connection
we should move the streams to. Here are some recommended heuristics the
initiator may use in determining which connection is best.

1. If we have both relayed and direct connections, keep the direct connections
   and drop the relay connections.
2. Check for simultaneous connect: If we have both inbound and outbound
   connections, keep the ones initiated by the peer with the lowest peer ID. Open
   Question: Some protocols behave differently depending on whether they are the
   dialer or listener. Can we really consolidate these?
3. Prefer the connection with the most streams.
4. Break ties in the remaining connections by selecting the newest conn, to
   match the swarm's behavior in best connection selection.

Note that it's not required that all implementations (and all versions) follow
the same heuristics since the initiator is driving the migration and specifies
where to migrate to.

## Appendix

[Specs Issue](https://github.com/libp2p/specs/issues/328)

### Related Issues:

- <https://github.com/libp2p/go-libp2p/issues/634>

## Open Questions

Some questions that will probably be resolved when a PoC is implemented.

- How many streams are there total? 2 or 3? There is the old stream and new
  stream, but is there a migration protocol specific stream? Or can the
  migration be started from the old stream? If yes, how do we prevent
  application data from looking like a migration without framing?
- In simultaneous open how do we pick who's the initiator? I think we can rely
  on the `/libp2p/simultaneous-connect` to do the correct thing here.
- Do we need a new connection that we migrate towards? Or can we re-use an
  existing connection?
- Can we migrate multiplexed streams to another multiplexed stream destination?
