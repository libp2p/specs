# Waggle: Next-generation pubsub protocol for libp2p
| Lifecycle Stage | Maturity | Status | Latest Revision |
|---|---|---|---|
| 1A | Working Draft | Active | r1, YYYY-MM-DD |

Authors: [@dknopik](@dknopik), [@jxs](@jxs), [@sukunrt](@sukunrt),

Interest Group: [...]

See the [lifecycle document][lifecycle-spec] for context about maturity level and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Overview
This work presents a publish-subscribe protocol for the dissemination of incrementally reconstructed objects, incorporating lessons learned from years of Gossipsub development.   
Nodes advertise support for the protocol using `/waggle/1.0` as the protocol string.

**Contents**

- [Overview](#overview)
- [Motivations and Prior Work](#motivations-and-prior-work)
- [Topic Membership](#topic-membership)
- [Publishing and Dissemination](#publishing-and-dissemination)
- [Object Cache](#object-cache)
- [Peer Discovery](#peer-discovery)
- [Peer Scoring and Abuse Mitigation](#peer-scoring-and-abuse-mitigation)
- [Opaque Protocol Fields](#opaque-protocol-fields)
- [Wire Format](#wire-format)

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY",
and "OPTIONAL" in this document are to be interpreted as described in
[RFC 2119](https://tools.ietf.org/html/rfc2119) and
[RFC 8174](https://tools.ietf.org/html/rfc8174).

## Motivations and Prior Work

The libp2p pubsub protocols have been evolving to meet the demands of their users. However, an increasingly common pattern across many applications remains poorly supported: the dissemination of incrementally reconstructed objects. Whether a large payload is deliberately split into smaller pieces for transmission or different nodes initially possess different pieces of the same application-defined object, each node begins with only partial information, and the goal is for all nodes to exchange pieces until they converge on the complete content.

Previous work on partial messages attempted to retrofit chunking onto Gossipsub through its extension system. However, integrating chunk dissemination with Gossipsub's mesh dynamics, including IHAVE/IWANT exchanges, heartbeat-driven maintenance, and message validation, proved increasingly complex. These mechanisms were designed around complete-message propagation, making incremental reconstruction a poor match for Gossipsub's underlying abstractions and requiring protocol logic to work against the architecture.

This complexity is compounded by years of accumulated legacy. Extensions must coexist with features that are either application-specific or of limited practical use, while core mechanisms such as scoring tightly couple application-level trust decisions with the network layer. More recent efforts to address limitations, such as head-of-line blocking through topic streams, further increase the amount of protocol machinery that new extensions must accommodate.

Rather than continuing to layer functionality onto a protocol whose abstractions are fundamentally message-centric, we argue that a broad class of dissemination problems is better served by a model that treats partial views as first-class objects. Instead of assuming that peers exchange complete messages, this model views communication as the progressive exchange of constituent pieces that allow nodes to converge on an application-defined object. These pieces need not correspond to literal fragments of the original object; they may represent independently transferable information that contributes to reconstruction. In file distribution, these pieces may be chunks of the original file or erasure-coded shards generated to improve dissemination efficiency; in attestation propagation, they are validator attestations that collectively form the attestation set for a slot. By treating partial views as first-class objects, routing, scheduling, validation, and flow control can operate directly on incremental reconstruction and exchange of metadata, instead of emulating it through complete-message semantics. This approach is necessarily incompatible with Gossipsub's message-centric model, but supports a broader class of peer-to-peer dissemination problems.
Peer scoring is an application-defined concern. The broadcast protocol should surface relevant information to the application and let it decide how to score and penalize peers, rather than baking scoring semantics into the network layer.
There is limited utility in maintaining a stable mesh through GRAFT and PRUNE messages. Publishing to a random subset of connected peers potentially selected using latency or other application-defined criteria provides the same robustness and coverage with significantly reduced implementation complexity.

## Topic Membership

Topics define independent dissemination scopes within the network. To subscribe to a topic, a peer opens a new dedicated outbound stream with its connected peers and MUST include the topic it wishes to participate in. Each topic is carried on its own dedicated stream. A peer subscribing to multiple topics opens a separate stream for each topic.
Peers maintain the subscription state of their connected peers. Once subscribed, the peer becomes eligible to participate in the dissemination of objects associated with that topic. 
To unsubscribe from a topic, a peer closes the corresponding stream, indicating that it no longer wishes to participate in dissemination for that topic. Upon closure, connected peers update their subscription state by removing the association between that peer and the topic.
The protocol does not prescribe how topics are created, named, or authorized. Topic management and access control are application-defined.

## Publishing and dissemination

 Objects are disseminated through incremental publication of their constituent pieces. A publisher may divide an object into multiple pieces and publish those pieces independently, including through repeated publication attempts. Pieces do not need to originate from a single publisher; any peer possessing a piece may participate in its propagation. Each published piece belongs to a topic and MUST be disseminated through the corresponding topic stream.

To publish a piece, a node selects a random subset of its connected peers and transmits it to them. Upon receiving a previously unknown piece, a peer updates its local object view and begins propagating the piece through its own connected peers.

The receiving peer uses the metadata it maintains about remote peers to identify peers that are known to be missing the received piece. The peer then transmits the piece to those peers, allowing dissemination to leverage existing knowledge of incomplete views. In addition, the peer advertises its updated metadata to peers that maintain a view of its state, allowing them to track the newly available piece.

To discover additional dissemination opportunities, a peer also selects a random subset of connected peers for which it has no current metadata view and advertises its current object metadata to them. These exchanges allow peers to progressively discover missing pieces and establish additional synchronization relationships throughout the network.

The number of peers selected for initial publication, piece forwarding, and metadata dissemination SHOULD be configurable by implementations and tuned according to application and deployment requirements, with consideration for dissemination amplification needs, bandwidth constraints, and network overhead.

## Opaque Protocol Fields

Topic identifiers, object identifiers, and piece metadata are opaque protocol fields whose semantics are defined by applications. The protocol does not prescribe how these fields are generated, assigned, encoded, or interpreted.

Applications SHOULD use stable identifiers that allow peers to consistently refer to the same topic or object across independent connections and dissemination attempts. Applications MAY use content-derived identifiers, such as cryptographic hashes, when content addressing is appropriate.

Applications are responsible for defining the representation and interpretation of piece metadata, including how pieces are tracked and how objects are reconstructed.

## Object Cache

The lifetime of cached object and piece state SHOULD be configurable by implementations and tunable by applications according to their resource constraints and dissemination requirements.

## Peer discovery

Peer discovery is outside the scope of this protocol. The protocol assumes that peers have an existing set of connected peers with which they can exchange subscriptions, metadata, and object pieces.
Applications and deployments SHOULD use dedicated peer discovery mechanisms, such as Distributed Hash Tables (DHTs) or other discovery protocols, to identify and establish connections with peers.

## Peer scoring and abuse mitigation

This protocol does not define a peer scoring system or prescribe how peers should be ranked, trusted, or penalized. Peer reputation, trust models, and application-specific scoring policies are considered application-layer concerns.
Implementations SHOULD expose dissemination-related events and peer behavior information to applications, allowing them to implement their own scoring mechanisms. Such information MAY include successful piece exchanges, failed requests, invalid pieces, protocol violations, subscription behavior, and resource consumption.
Applications MAY use this information to determine whether a peer should continue participating in dissemination, be deprioritized, or be disconnected. The protocol does not mandate how application-level decisions affect peer interactions.
At the protocol layer, implementations SHOULD provide basic protections against resource exhaustion and malformed behavior. These protections MAY include limiting concurrent streams, bounding metadata size, rate limiting requests and advertisements, validating piece identifiers and object metadata, and preventing peers from causing unbounded memory or bandwidth consumption.

## Wire Format

The protocol uses Protocol Buffers (protobuf) as its wire format. Messages are encoded using the following schema:

```protobuf
message TopicSubscription {
  required bytes topicID = 1;
}

message ObjectPieces {
  required bytes objectID = 2;
  optional bytes piecesMetadata = 3;
  optional bytes pieces = 4;
}
```
