# multiselect 2.0 design proposal

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 1A              | Working Draft  | Active | r1, 2019-08-15  |

Authors: [@marten-seemann], [@raulk]

Interest Group: [Insert Your Name Here]

**This document is not the multistream 2.0 protocol spec.** It is a design doc to serve as a prelude to a subsequent spec.

We aim to lay out the problem domain first by providing context, pointing out issues, and setting the requirements and possible design directions. 

Given the complexity and criticality of this component, it is indispensable to lock consensus about the problems and challenges to solve, before jumping into addressing them via a concrete implementation spec.

## Context

**multistream-select 1.0** is a simple protocol selection that participates in two processes in the libp2p stack:

* [Connection establishment](https://github.com/libp2p/specs/blob/master/connections/README.md#connection-establishment-in-libp2p) is the process of setting up a _capable_ libp2p connection, out of a _raw_ transport connection (socket):

  * Depending on the transport, this implies negotiating and activating (1) a secure channel and (2) a stream multiplexer, in a process frequently nicknamed "upgrading".

  * libp2p stacks support several strategies for each (e.g. SecIO, TLS 1.3, Noise, etc. for secure channels; yamux, mplex, spdystream, etc. for stream multiplexing). We reach agreement dynamically via multistream-select 1.0 protocol negotiation.
  
  * Natively capable transports (e.g. QUIC) don't require an upgrade.

* [Stream protocol negotiation](https://github.com/libp2p/specs/blob/master/connections/README.md#multistream-select) is the process of agreeing on an application protocol for a stream.


### multistream-select 1.0 primer

multistream-select 1.0 is a simple, interactive, round-trip liberal, protocol negotiation mechanism. It was devised at the time as the simplest solution to fit the bill, without a focus on efficiency. It has now outgrown its purpose, and a more efficient, feature-rich mechanism is needed.

The mechanics of multistream-select 1.0 are very simple. They can be summarised as follows:

0. we preamble with a `/multistream/1.0.0` two-way announcement.
1. the initiator sends a length-prefixed protocol proposal.
2. if the responder agrees with the proposed protocol, it echoes the length-prefixed protocol name. Negotiation succeeds.
3. otherwise it replies with `na`. We go back to 1.
4. if all options are exhausted without agreement, the initiator closes the connection.

Without going into too much detail, given two peers `P1` (initiator) and `P2` (responder), supporting protocol sets `/foo/{A, B, C}` and `/foo/{D, B, E}`, respectively, the negotiation would go as follows, from the viewpoint of `P1`:

```
>>> /multistream/1.0.0    (1)
<<< /multistream/1.0.0    (2)
>>> /foo/A                (3)
<<< na                    (4)
>>> /foo/B                (5)
<<< /foo/B                (6)

## /foo/B agreed; traffic for that protocol begins
```

**Important:** What above appears to be 3 roundtrips on paper, in practice is 2. Implementations optimise by pipelining proposals. For example, most implementations would pipeline (1) and (3) by concatenating the protocol IDs and flushing them to the wire at once. This is possible thanks to length-prefixing, and because `P1` only supports `/multistream/1.0.0`. If `P2` didn't support `/multistream/1.0.0`, `P1` would read `na` back and close the connection. From here on, we use `++` to indicate pipelining.

### multistream-select 1.0-based connection establishment

This flow outlines wire-level exchanges for end-to-end connection establishment, and the first application stream negotiation, under the following protocol configuration:

|Peer            |Secure channels                               |Stream multiplexers             |App protocols                 |
|----------------|----------------------------------------------|--------------------------------|------------------------------|
|A (initiator)   | `/secio/1.0.0`, `/tls/1.0.0`, `/noise/1.0.0` | `/yamux/1.0.0`, `/mplex/1.0.0` | `/app/A`, `/app/B`, `/app/C` |
|B (responder)   | `/tls/1.0.0`, `/noise/1.0.0`                 | `/yamux/1.0.0`                 | `/app/B`                     |


From the perspective of `A`, applying optimistic protocol pipelining:

```
## this is cleartext
## we initiate secure channel negotiation

>>> /multistream/1.0.0 ++ /secio/1.0.0
<<< /multistream/1.0.0 ++ na
>>> /tls/1.0.0
<<< /tls/1.0.0

## ··· tls handshake happens ···
## connection is now encrypted

>>> /multistream/1.0.0 ++ /yamux/1.0.0
<<< /multistream/1.0.0 ++ /yamux/1.0.0

## both parties overlay yamux
## all subsequent i/o happens over streams

[[ stream 0 ]]
>>> /multistream/1.0.0 ++ /app/A
<<< /multistream/1.0.0 ++ na
>>> /app/B
<<< /app/B

## stream 0 is contextualised to protocol /app/B
```

Some implementations (e.g. go-libp2p and rust-libp2p) can also optimistically pipeline push data. This is only feasible when the initiator only supports ONE protocol for the particular negotiation. The opening message in this case is:

```
>>> /multistream/1.0.0 ++ /app/A ++ first message
```

If the responder supports `/app/A`, this will be a sound exchange. If the peer does not support `/app/A`, it will send `na` and confuse `first message` with a second protocol proposal, which might be well formed or not:

* If badly formed, the responder will error and reset the connection or stream.
* If well-formed, the initiator will reset the connection or stream when it reads the responder's `na`.

## Requirements: Connection establishment

### General requirements

0. The solution needs to play well with TCP simultaneous open (or equivalent states in other protocols), by disambiguating initiator and responder roles if necessary.

### Cryptographic handshake

1. Current libp2p traffic can be blocked by using deep packet inspection. Handshakes should be indistinguishable from ordinary HTTP/2 (in the case of TCP) and HTTP/3 (in the case of QUIC) traffic, or other popular Internet applications.
2. Peers might support multiple handshake protocols (SecIO, TLS, Noise). An attacker (e.g. MITM) should not be able to control which protocol peers agree on, nor acquire any metadata.
3. Handshakes supporting early data (0-RTT or above) should enable us to leverage it for preemptive follow-up negotiations (e.g. agreeing on supported multiplexers).

Requirements 1 & 2 above suggest to abandon dynamic secure channel protocol negotiation for our handshake, because of two fundamental flaws:

1. It needs to happen in the clear (the peers don’t have any shared secret that could be used to encrypt anything) and would thus be detectable via deep packet inspection.
2. A naïve cleartext negotiation is vulnerable to downgrade attacks by a MITM. In one possible attack, a MITM could strip out any proposed handshake protocols from the unencrypted message, and thus force the peers to use a (potentially weaker) handshake protocol. 
    * This is an attack faced by every protocol that establishes a channel between two peers that don’t share a secret. TLS solves this by verifying a hash of all handshake messages exchanged at the end of the handshake, SecIO by signing the cleartext message in the Exchange step.
    * We might be able to authenticate the list of handshake protocols after completion of the handshake, e.g. by exchanging the list (or a hash of the list) as the first message sent under crypto cover, but it would be nice to avoid that additional complexity.

The approach that has garnered support in discussions is to extend multiaddrs so they can inline the secure channels the peer supports.

That way, peers advertise their supported encryption protocols upfront and we remove the need for dynamic cleartext negotiation.

Multiaddrs can be secured via self-certification, inside the payload of the peer routing records used in the discovery layer (in a manner similar to [Ethereum Node Records](https://eips.ethereum.org/EIPS/eip-778)). This thwarts the ability for intermediaries to tamper with the ordered enumeration of secure channels a node advertises for itself.

### Stream multiplexer negotiation

1. Negotiation should be bypassed for transports supporting native multiplexing (e.g. QUIC).
2. Different implementations support different sets of stream multiplexers (e.g. yamux, SPDY, mplex). Supported multiplexers and versions will evolve over time.
3. Desirable property: Negotiating a stream multiplexer shouldn’t cost any roundtrips, leveraging _early data_ mechanisms in handshakes. Where this is unfeasible, it should cost at most one round trip. Unfeasible situations are:
    * when the underlying handshake mechanism doesn't support it (e.g. SecIO).
    * when the underlying handshake mechanism does support _early data_, but the language of the libp2p implementation doesn't (e.g. current state of TLS 1.3 in Go).
    * when the initiator requires privacy guarantees that would otherwise not apply to early data.
5. Some applications may not need to hold parallel conversations (e.g. resource-constrained). They may be deliberately _monoplexed_ – thus precluding the need for stream muxing. 
    * We need to find a solution to run those protocols on top of QUIC. Conceptually, this is trivial (just use a single bidirectional stream), although we might have to do some work to wrap this into a nice API.
    * Supporting this use case would presuppose concomitant constraints, such as not running identify or other libp2p infrastructural protocols that require dedicated streams.
6. *Tentative*: For handshake protocols that don't support early data, we may make it possible to service that request via an _embryonic stream_, while a fully-fledged multiplexer is negotiated in parallel. This would benefit applications that open connections to peers with a specific immediate purpose, e.g. a DHT request, and RPC invocation. 

## Requirements: Stream protocol negotiation

1. Peers might want to support a lot (O(1000)) protocols at the same time.
2. It has to be possible to speculatively select a protocol without knowing for certain if the peer supports it (just like ms1.0).
3. Repeated use of the same protocols within the same session should be efficient, i.e. not require sending the full protocol name every single time.
4. Endpoints might not want to reveal all protocols they support upfront.
    * they might only reveal them after an additional authentication step performed after completion of the handshake.
    * they might only reveal them in response to the peer “trying out” the protocol.
    * any other rule specified by the endpoint.
5. Interplays with pre-handshake-completion data mechanisms:
    * 0.5-RTT data in the case of TLS 1.3.
    * message data in Noise handshakes.
6. Possibly work with message-oriented transports (UDP), cf. multigram.
7. Peers might add new supported protocols (or reveal that they are supporting a protocol) during the lifetime of a connection.
8. Peers may announce support for protocols off-band (e.g. via discovery mechanisms like mDNS, rendezvous, DHT), either deterministically (enumeration) or probabilistically (bloom filter).
9. *Tentative*: When (a) multiple protocols are supported for a given exchange (e.g. in the case of versioned protocols, where a peer supports both old and the new versions), and (b) the peer has no knowledge of what the other party supports (i.e. before either receiving a list of supported protocols, or before trying out both protocols), the peer should be able to eagerly send the request for both protocols within a single message, declaring a precedence, allowing the client to select, keep and respond to at most one.


## Assumptions

1. multiaddr will be extended to convey the secure channel a peer supports, e.g.:
    * `/ip4/1.2.3.4/tcp/9000/tls/id/QmPeer`
    * `/ip4/1.2.3.4/tcp/9001/secio/id/QmPeer`
    * or a more efficient scheme that allows multivariance.
3. Annoucing a multiaddr containing a secure channel implies that a peer supports the multiselect 2.0 protocol.
    * multistream-select 1.0 peers will NOT advertise secure channels.
5. All cryptographic handshake protocols we use can detect a TCP simultaneous open.
    * for example: in TLS, a client will abort the handshake with an `unexpected_message` alert when *receiving* a ClientHello. That way, we can detect that both peers assumed to be clients.

## Proposed Feature Set

0. We dissociate the processes of connection establishment and protocol negotiation. Connection establishment can now happen without multiselect 2.0 (protocol negotiation) intervening.
    * By enhancing multiaddrs to express supported secure channels, peers can handshake immediately. Let's call these _security-explicit addresses_.
    * By leveraging _early data_ mechanisms in the handshake, peers can announce their multiplexers and agree by intersection.
    * If the handshake does not support _early data_ (e.g. SecIO), we have to fall back to multiplexer negotiation.
    * Alternatively, multiplexer negotiation can "piggyback" on top of an embryonic stream.
      * If the initiating peer A has a motivation to send a message to peer B in the context of some subsystem (e.g. DHT, pubsub, application-level protocol), after the hanshake has completed, it can send that message wrapped in a special envelope that enumerates supported multiplexers.
      * The other party will then confirm one of the multiplexers, response to the message, and the embryonic, rudimentary stream will disappear, giving way to a fully multiplexed connection.
      * This dynamic, deferred, ambient upgrade is similar to the HTTP WebSockets upgrade mechanism, and allows for an early exchange to occur without incurring in a synchronous, blocking multiplexer negotiation round trip.
    * We need to be backwards-compatible with older peers that do not advertise security-explicit addresses.
    * Interplay with discovery: the peer record may include secure channel and multiplexer capabilities in fields other than the multiaddr (e.g. `TXT` records in mDNS).
    * Transparent fallback to explicit negotiation has to be supported at any time.

1. We shouldn't require a dedicated round-trip to determine if the peer is upgraded (ms2.0) or not (ms1.0). We can:
    * make probabilistic _inferences_, e.g. presence of inline secure channels in multiaddr means that the peer supports ms2.0.
    * use speculative protocol pipelining (e.g. send many delimited protocols within a single packet, assuming some short-circuiting behaviour).

2. multiselect 2.0 needs to work synergistically with off-band protocol advertisement mechanisms (e.g. DHT, mDNS, pubsub records), under a variety of approaches.
    * Peers may convey protocols deterministically (e.g. list), or probabilistically for space efficiency (e.g. bloom filters, leading to false positives).
    * They may share complete or partial views.
    * Advertisements could be outdated, if the discovery mechanism is asynchronous or eventually consistent in nature.

3. multiselect 2.0 should support both speculative and confident protocol selection, accompanied by a first message.
    * To amortize the cost of an MTU, under the speculative scenario, a peer may attempt multiple, exclusive protocols, each with their corresponding initial message (i.e. `any-of` scenario).
    * The receiver chooses and keeps one of them at most.

4. multiselect 2.0 will support string-based and codec-based protocol selection.
    * To avoid ambiguity, codecs must be universal (e.g. enlisted in the multicodec table) and used only for libp2p protocols (e.g. identify, DHT, etc.)

5. Peers must be able to request – or unilaterally send – a full or partial protocol mapping table.
    * One strategy would be to declare the mapping of a few commonly used protocols as early as possible in the handshake.
    * The rest of the protocols could be sent later on, when spare bandwidth is available.

6. Previously selected protocols must be cheap to re-select within the session.
    * As string-based protocols are selected within a session, the responding peer returns the index with which that protocol can be re-selected within the same session.
    * This mechanism has the advantage that peers don't end up storing irrelevant mappings.
    * Implementation-wise, it could look like this:
    
      1. we hold a mapping of our own protocols to indices.
      2. whenever a peer selects a protocol for the first time, we confirm that selection and return the index with which it can be selected later.
      3. if the peer thinks it _may_ select that protocol later, it memorises that mapping.

7. Sessions _could_ be resumable (benefit is arguable).
    * Nodes could store peer protocol mappings across sessions.
    * When reconnecting to that peer, if a full protocol table had been shared, the initiator could send a merkle hash (or some digest) for the responder to confirm whether the same protocol table is still in effect.
      * Useful if protocol tables are large and mostly invariant.
      * Could consider opaque tokens (issued by the owner of the table) and delta updates, but this is way too complex.
    * This is unrelated to cryptographic/protocol session resumption. Resuming at that level doesn't imply that peer protocols have stayed unchanged.

8. TCP simultaneous open collision detection.
