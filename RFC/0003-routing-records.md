# RFC 0003 - Peer Routing Records

- Start Date: 2019-10-04
- Related Issues:
  - [libp2p/issues/47](https://github.com/libp2p/libp2p/issues/47)
  - [go-libp2p/issues/436](https://github.com/libp2p/go-libp2p/issues/436)

## Abstract

This RFC proposes a method for distributing peer routing records, which contain
a peer's publicly reachable listen addresses, and may be extended in the future
to contain additional metadata relevant to routing. This serves a similar
purpose to [Ethereum Node Records][eip-778]. Like ENR records, libp2p routing
records should be extensible, so that we can add information relevant to as-yet
unknown use cases.

The record described here does not include a signature, but it is expected to
be serialized and wrapped in a [signed envelope][envelope-rfc], which will
prove the identity of the issuing peer. The dialer can then prioritize
self-certified addresses over addresses from an unknown origin.

## Problem Statement

All libp2p peers keep a "peer store", which maps [peer ids][peer-id-spec] to a
set of known addresses for each peer. When the application layer wants to
contact a peer, the dialer will pull addresses from the peer store and try to
initiate a connection on one or more addresses.

Addresses for a peer can come from a variety of sources. If we have already made
a connection to a peer, the libp2p [identify protocol][identify-spec] will
inform us of other addresses that they are listening on. We may also discover
their address by querying the DHT, checking a fixed "bootstrap list", or perhaps
through a pubsub message or an application-specific protocol.

In the case of the identify protocol, we can be fairly certain that the
addresses originate from the peer we're speaking to, assuming that we're using a
secure, authenticated communication channel. However, more "ambient" discovery
methods such as DHT traversal and pubsub depend on potentially untrustworthy
third parties to relay address information.

Even in the case of receiving addresses via the identify protocol, our
confidence that the address came directly from the peer is not actionable, because
the peer store does not track the origin of an address. Once added to the peer
store, all addresses are considered equally valid, regardless of their source.

We would like to have a means of distributing _verifiable_ address records,
which we can prove originated from the addressed peer itself. We also need a way to
track the "provenance" of an address within libp2p's internal components such as
the peer store. Once those pieces are in place, we will also need a way to
prioritize addresses based on their authenticity, with the most strict strategy
being to only dial certified addresses.

### Complications

While producing a signed record is fairly trivial, there are a few aspects to
this problem that complicate things.

1. Addresses are not static. A given peer may have several addresses at any given
   time, and the set of addresses can change at arbitrary times.
2. Peers may not know their own addresses. It's often impossible to automatically
   infer one's own public address, and peers may need to rely on third party
   peers to inform them of their observed public addresses.
3. A peer may inadvertently or maliciously sign an address that they do not
   control. In other words, a signature isn't a guarantee that a given address is
   valid.
4. Some addresses may be ambiguous. For example, addresses on a private subnet
   are valid within that subnet but are useless on the public internet.

The first point can be addressed by having records contain a sequence number
that increases monotonically when new records are issued, and by having newer
records replace older ones.

The other points, while worth thinking about, are out of scope for this RFC.
However, we can take care to make our records extensible so that we can add
additional metadata in the future. Some thoughts along these lines are in the
[Future Work section below](#future-work).

## Address Record Format

Here's a protobuf that might work:

```protobuf
syntax = "proto3";

package peer.pb;

// PeerRecord messages contain information that is useful to share with other peers.
// Currently, a PeerRecord contains the public listen addresses for a peer, but this
// is expected to expand to include other information in the future.
//
// PeerRecords are designed to be serialized to bytes and placed inside of
// SignedEnvelopes before sharing with other peers.
message PeerRecord {

  // AddressInfo is a wrapper around a binary multiaddr. It is defined as a
  // separate message to allow us to add per-address metadata in the future.
  message AddressInfo {
    bytes multiaddr = 1;
  }

  // peer_id contains a libp2p peer id in its binary representation.
  bytes peer_id = 1;

  // seq contains a monotonically-increasing sequence counter to order PeerRecords in time.
  uint64 seq = 2;

  // addresses is a list of public listen addresses for the peer.
  repeated AddressInfo addresses = 3;
}
```

The `AddressInfo` wrapper message is used instead of a bare multiaddr to allow
us to extend addresses with additional metadata [in the future](#future-work).

The `seq` field contains a sequence number that MUST increase monotonically as
new records are created. Newer records MUST have a higher `seq` value than older
records. To avoid persisting state across restarts, implementations MAY use unix
epoch time as the `seq` value, however they MUST NOT attempt to interpret a
`seq` value from another peer as a valid timestamp.

#### Example

```javascript
  {
    peer_id: "QmAlice...",
    seq: 1570215229,
    addresses: [
      {
        multiaddr: "/ip4/192.0.2.0/tcp/42/p2p/QmAlice",
      },
      {
        multiaddr: "/ip4/198.51.100.0/tcp/42/p2p/QmAlice",
      }
    ]
  }
```

A peer SHOULD only include addresses that it believes are routable via the
public internet, ideally having confirmed that this is the case via some
external mechanism such as a successful AutoNAT dial-back.

In some cases we may want to include localhost or LAN-local address; for
example, when testing the DHT using many processes on a single machine. To
support this, implementations may use a global runtime configuration flag or
environment variable to control whether local addresses will be included.

## Certification / Verification

This structure can be serialized and contained in a [signed
envelope][envelope-rfc], which lets us issue "self-certified" address records
that are signed by the peer that the addresses belong to.

To produce a "self-certified" address, a peer will construct a `RoutingState`
containing their listen addresses and serialize it to a byte array using a
protobuf encoder. The serialized records will then be wrapped in a [signed
envelope][envelope-rfc], which is signed with the libp2p peer's private host
key. The corresponding public key MUST be included in the envelope's
`public_key` field.

When receiving a `RoutingState` wrapped in a signed envelope, a peer MUST
validate the signature before deserializing the `RoutingState` record. If the
signature is invalid, the envelope MUST be discarded without deserializing the
envelope payload.

Once the signature has been verified and the `RoutingState` has been
deserialized, the receiving peer MUST verify that the `peer_id` contained in the
`RoutingState` matches the `public_key` from the envelope. If the public key in
the envelope cannot derive the peer id contained in the routing state record,
the `RoutingState` MUST be discarded.

### Signed Envelope Domain

Signed envelopes require a "domain separation" string that defines the scope
or purpose of a signature.

When wrapping a `RoutingState` in a signed envelope, the domain string MUST be
`libp2p-routing-state`.

### Signed Envelope Payload Type

Signed envelopes contain a `payload_type` field that indicates how to interpret
the contents of the envelope.

Ideally, we should define a new multicodec for routing records, so that we can
identify them in a few bytes. While we're still spec'ing and working on the
initial implementation, we can use the UTF-8 string
`"/libp2p/routing-state-record"` as the `payload_type` value.

## Peer Store APIs

We will need to add a few methods to the peer store:

- `AddCertifiedAddrs(envelope) -> Maybe<Error>`
  - Add a self-certified address, wrapped in a signed envelope. This should
    validate the envelope signature & store the envelope for future reference.
    If any certified addresses already exist for the peer, only accept the new
    envelope if it has a greater `seq` value than existing envelopes.

- `CertifiedAddrs(peer_id) -> Set<Multiaddr>`
  - return the set of self-certified addresses for the given peer id

- `SignedRoutingState(peer_id) -> Maybe<SignedEnvelope>`
  - retrieve the signed envelope that was most recently added to the peerstore
    for the given peer, if any exists.

And possibly:

- `IsCertified(peer_id, multiaddr) -> Boolean`
  - has a particular address been self-certified by the given peer?

We'll also need a method that constructs a new `RoutingState` containing our
listen addresses and wraps it in a signed envelope. This may belong on the Host
instead of the peer store, since it needs access to the private signing key.

When adding records to the peerstore, a receiving peer MUST keep track of the
latest `seq` value received for each peer and reject incoming `RoutingState`
messages unless they contain a greater `seq` value than the last received.

After integrating the information from the `RoutingState` into the peerstore,
implementations SHOULD retain the original signed envelope. This will allow
other libp2p systems to share signed `RoutingState` records with other peers in
the network, preserving the signature of the issuing peer. The [Exchanging
Records section](#exchanging-records) section lists some systems that would need
to retrieve the original signed record from the peerstore.

## Dialing Strategies

Once self-certified addresses are available via the peer store, we can update
the dialer to prefer using them when possible. Some systems may want to _only_
dial self-certified addresses, so we should include some configuration options
to control whether non-certified addresses are acceptable.

## Exchanging Records

We currently have several systems in libp2p that deal with peer addressing and
which could be updated to use signed routing records:

- Public peer discovery using [libp2p's DHT][dht-spec]
- Local peer discovery with [mDNS][mdns-spec]
- Direct exchange using the [identify protocol][identify-spec]
- Service discovery via the [rendezvous protocol][rendezvous-spec]
- A proposal for [a public peer exchange protocol][pex-proposal]

Of these, the highest priority for updating seems to be the DHT, since it's
actively used by several deployed systems and is vulnerable to routing attacks
by malicious peers. We should work on extending the `FIND_NODE`, `ADD_PROVIDER`,
and `GET_PROVIDERS` RPC messages to support returning signed records in addition
to the current unsigned address information they currently support.

We should also either define a new "secure peer routing" interface or extend the
existing peer routing interfaces to support signed records, so that we don't end
up with a bunch of similar but incompatible APIs for exchanging signed address
records.

## Future Work

Some things that were originally considered in this RFC were trimmed so that we
can focus on delivering a basic self-certified record, which is a pressing need.

This includes a notion of "routability", which could be used to communicate
whether a given address is global (reachable via the public internet),
LAN-local, etc. We may also want to include some kind of confidence score or
priority ranking, so that peers can communicate which addresses they would
prefer other peers to use.

To allow these fields to be added in the future, we wrap multiaddrs in the
`AddressInfo` message instead of having the `addresses` field be a list of "raw"
multiaddrs.

Another potentially useful extension would be a compact protocol table or bloom
filter that could be used to test whether a peer supports a given protocol
before interacting with them directly. This could be added as a new field in the
`RoutingState` message.

[identify-spec]: ../identify/README.md
[peer-id-spec]: ../peer-ids/peer-ids.md
[mdns-spec]: ../discovery/mdns.md
[rendezvous-spec]: ../rendezvous/README.md
[pex-proposal]: https://github.com/libp2p/notes/issues/7
[envelope-rfc]: ./0002-signed-envelopes.md
[eip-778]: https://eips.ethereum.org/EIPS/eip-778
[dht-spec]: https://github.com/libp2p/specs/blob/master/kad-dht/README.md
