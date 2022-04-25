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

The protocol should only be used when the initiator knows the responder
understands the stream-migration protocol to avoid wasting 1 round trip.

The protocol works as a prefix before another protocol. If we are creating a
stream for some user protocol `P`, we coordinate the stream-migration protocol
first, and then negotiate protocol `P` later. The stream-migration protocol
assigns an ID for the stream with the `Label` or `Migrate` message so that both
sides can know the ID for the stream. This way when a peer decides to migrate
the stream later on, it can reference which stream it wants to migrate and both
peers know which stream is being referenced.

![stream-migration](./stream-migration/stream-migration.svg)

<details>
  <summary>Instructions to reproduce diagram</summary>

``` plantuml
@startuml stream-migration
skinparam sequenceMessageAlign center
entity Initiator
entity Responder

note over Initiator, Responder: Assume both sides understand stream-migration

Initiator -> Responder: Open connection
Initiator -> Responder: Open multiplexed stream

Initiator -> Responder: Negotiate stream-migration protocol with ""<stream-migration protocol id>""

Initiator -> Responder: Send ""StreamMigration(type=Label(id=1))"" message

Initiator -> Responder: <i> continue negotiating underlying protocol </i>
... <i>Nodes use the stream as normal<i> ...

== Stream Migration ==

note over Initiator, Responder: Migrate <b>Stream 1</b> to <b>Stream 2</b>

Initiator -> Responder: Open new stream
Initiator -> Responder: Negotiate stream-migration protocol with ""<stream-migration protocol id>""

Initiator -> Responder: <b>Stream 2:</b> Send ""StreamMigration(type=Migrate(id=2, from=1))"" message

Initiator <- Responder: <b>Stream 2:</b> Send AckMigrate message

note over Responder
    Treat any ""EOF"" on <b>stream 1</b> as a signal
    that it should continue reading on <b>stream 2</b>
end note


note over Initiator
    Close <b>stream 1</b> for writing.
    Will only write to <b>stream 2</b> from now on.
end note

Initiator -> Responder: <b>Stream 2:</b> ""EOF""

note over Responder
    When <i>Responder</i> reads ""EOF"" on <b>stream 1</b>
    it will close <b>stream 1</b> for writing.
    It will only write to <b>stream 2</b> from now on.
end note

Initiator <- Responder: <b>Stream 2:</b> ""EOF""

note over Initiator
    Treat any ""EOF"" on <b>stream 1</b> as a signal
    that it should continue reading on <b>stream 2</b>
end note

note over Initiator, Responder
    At this point <b>stream 1</b> is closed for writing on
    both sides, and both sides have read up to ""EOF"".
    <b>stream 1</b> has been fully migrated to <b>stream 2</b>
end note

@enduml
```

To generate:
```bash
plantuml stream-migration.md -o stream-migration -tsvg
```
</details>

Note: some of these steps may be pipelined.


### Stream IDs

Stream IDs are identified by a uint64 defined by the initiator and conveyed to
the responder in the `StreamMigration` message.

### Stream Migration Protocol ID

The protocol id should be `/libp2p/stream-migration`.

### Stream Migration Messages

Messages for stream migration are Protobuf messages defined in
[./stream-migration/streammigration.proto](./stream-migration/streammigration.proto).

### Resets

If either stream is "reset" before both ends are closed, both streams must be
reset and the stream as a whole should be considered "aborted" (reset).

### Half closed streams

The final migrated stream should look the same as the initial stream. If the
initial stream `1` was half closed, then the final migrated stream `2` should
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

Initiator <- Responder: <b>Stream 1:</b> ""EOF""
note over Responder: <b>Stream 1</b> is closed for writing

== Stream Migration ==

note over Initiator, Responder: Migrate <b>Stream 1</b> to <b>Stream 2</b>

Initiator -> Responder: Open new stream on <b>Connection 2</b>. Call this <b>Stream 2</b>

Initiator -> Responder: <b>Stream 2:</b> Negotiate stream-migration protocol with ""<stream-migration protocol id>""
Initiator -> Responder: <b>Stream 2:</b> Send ""StreamMigration(type=Migrate(id=2, from=1))"" message

Initiator <- Responder: <b>Stream 2:</b> Ack Migrate

note over Initiator
    Close <b>stream 1</b> for writing.
    Will only write to <b>stream 2</b> from now on.
end note

note over Initiator
    We have already seen the ""EOF"" on
    <b>Stream 1</b> from <i>Responder</i>
    So we continue reading on <b>stream 2</b>
end note

Initiator -> Responder: <b>Stream 1:</b> ""EOF""

note over Responder
    Treat ""EOF"" on <b>stream 1</b> as a signal to close <b>stream 1</b> for
    writing and continue writing on <b>stream 2</b>. However stream 1 was
    already closed (before migration), so we close <b>stream 2</b> as well here.
end note
Initiator <- Responder: <b>Stream 2:</b> ""EOF""

note over Initiator, Responder: Stream 1 is now migrated to Stream 2

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

- In simultaneous open how do we pick who's the initiator? I think we can rely
  on the `/libp2p/simultaneous-connect` to do the correct thing here.
- Multiple connections with different initiators. (?) which connection to keep?