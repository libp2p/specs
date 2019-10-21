# RFC 0003 - Address Records with Metadata

- Start Date: 2019-10-04
- Related Issues:
  - [libp2p/issues/47](https://github.com/libp2p/libp2p/issues/47)
  - [go-libp2p/issues/436](https://github.com/libp2p/go-libp2p/issues/436)
  
## Abstract

This RFC proposes a method for distributing address records, which contain a
peer's publicly reachable listen addresses, as well as some metadata that can
help other peers categorize addresses and prioritize thme when dialing.

The record described here does not include a signature, but it is expected to
be serialized and wrapped in a [signed envelope][envelope-rfc], which will
prove the identity of the issuing peer. The dialer can then prioritize
self-certified addresses over addresses from an unknown origin.

## Problem Statement

All libp2p peers keep a "peer store" (called a peer book in some
implementations), which maps [peer ids][peer-id-spec] to a set of known
addresses for each peer. When the application layer wants to contact a peer, the
dialer will pull addresses from the peer store and try to initiate a connection
on one or more addresses.

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

The first point implies that the address record should include some kind of
temporal component, so that newer records can replace older ones as the state
changes over time. This could be a timestamp and/or a simple sequence number
that each node increments whenever they publish a new record.

The second and third points highlight the limits of certifying information that
is itself uncertain. While a signature can prove that the addresses originated
from the peer, it cannot prove that the addresses are correct or useful. Given
the asymmetric nature of real-world NATs, it's often the case that a peer is
_less likely_ to have correct information about its own address than an outside
observer, at least initially.

This suggests that we should include some measure of "confidence" in our
records, so that peers can distribute addresses that they are not fully certain
are correct, while still asserting that they created the record. For example,
when requesting a dial-back via the [AutoNAT service][autonat], a peer could
send a "provisional" address record. When the AutoNAT peer confirms the address,
that address could be marked as confirmed and advertised in a new record.

Regarding the fourth point about ambiguous addresses, it would also be desirable
for the address record to include a notion of "routability," which would
indicate how "accessible" the address is likely to be. This would allow us to
mark an address as "LAN-only," if we know that it is not mapped to a publicly
reachable address but would still like to distribute it to local peers.

## Address Record Format

Here's a protobuf that might work:

```protobuf
// Routability indicates the "scope" of an address, meaning how visible
// or accessible it is. This allows us to distinguish between LAN and
// WAN addresses.
//
// Side Note: we could potentially have a GLOBAL_RELAY case, which would
// make it easy to prioritize non-relay addresses in the dialer. Bit of
// a mix of concerns though.
enum Routability {
  // catch-all default / unknown scope
  UNKNOWN = 1;
  
  // another process on the same machine
  LOOPBACK = 2;
  
  // a local area network
  LOCAL = 3;
  
  // public internet
  GLOBAL = 4;

  // reserved for future use
  INTERPLANETARY = 100;
}


// Confidence indicates how much we believe in the validity of the
// address.
enum Confidence {
  // default, unknown confidence. we don't know one way or another
  UNKNOWN = 1;
  
  // INVALID means we know that this address is invalid and should be deleted
  INVALID = 2;
  
  // UNCONFIRMED means that we suspect this address is valid, but we haven't
  // fully confirmed that we're reachable.
  UNCONFIRMED = 3;
  
  // CONFIRMED means that we fully believe this address is valid.
  // Each node / implementation can have their own criteria for confirmation.
  CONFIRMED = 4;
}

// AddressInfo is a multiaddr plus some metadata.
message AddressInfo {
  bytes multiaddr = 1;
  Routability routability = 2;
  Confidence confidence = 3;
}

// AddressState contains the listen addresses (and their metadata) 
// for a peer at a particular point in time.
//
// Although this record contains a wall-clock `issuedAt` timestamp,
// there are no guarantees about node clocks being in sync or correct.
// As such, the `issuedAt` field should be considered informational,
// and `version` should be preferred when ordering records.
message AddressState {
  // the peer id of the subject of the record.
  bytes subjectPeer = 1;
  
  // `version` is an increment-only counter that can be used to
  // order AddressState records chronologically. Newer records
  // MUST have a higher `version` than older records, but there
  // can be gaps between version numbers.
  uint64 version = 2;
  
  // The `issuedAt` timestamp stores the creation time of this record in
  // seconds from the unix epoch, according to the issuer's clock. There
  // are no guarantees about clock sync or correctness. SHOULD NOT be used
  // to order AddressState records; use `seqno` instead.
  uint64 issuedAt = 3;
  
  // All current listen addresses and their metadata.
  repeated AddressInfo addresses = 4;
}
```

The idea with the structure above is that you send some metadata along with your
addresses: your "routability", and your own confidence in the validity of the
address. This is wrapped in an `AddressInfo` struct along with the address
itself.

Then you have a big list of `AddressInfo`s, which we put in an `AddressState`.
An `AddressState` identifies the `subject` of the record,


#### Example

Here's an example. Alice has an address that she thinks is publicly reachable
but has not confirmed. She also has a LAN-local address that she knows is valid,
but not routable via the public internet:

```javascript
  {
    subjectPeer: "QmAlice...",
    version: 23456,
    issuedAt: 1570215229,
      
    addresses: [
      {
        addr: "/ip4/1.2.3.4/tcp/42/p2p/QmAlice",
        routability: "GLOBAL",
        confidence: "UNCONFIRMED"
      },
      {
        addr: "/ip4/10.0.1.2/tcp/42/p2p/QmAlice",
        routability: "LOCAL",
        confidence: "CONFIRMED"
      }
    ]
  }
```

If Alice wants to publish her address to a public shared resource like a DHT,
she should omit `LOCAL` and other unreachable addresses, and peers should
likewise filter out `LOCAL` addresses from public sources.

## Certification / Verification

This structure can be contained in a [signed envelope][envelope-rfc], which lets
us issue "self-certified" address records that are signed by the `subjectPeer`.

## Peer Store APIs



## Dialing Strategies


## TODO

Some things I'd like to cover but haven't got to or figured out yet:

- how to store signed records 
  - should be separate from "working set" that's optimized for retrieval
  - need to store unaltered bytes
- how to surface routability and confidence via peerstore APIs
- figure out if IPLD is the way to go here. If not, what serialization format,
  etc.
- extend identify protocol to include signed records?
- how are addresses prioritized when dialing?


[identify-spec]: ../identify/README.md
[peer-id-spec]: ../peer-ids/peer-ids.md
[autonat]: https://github.com/libp2p/specs/issues/180
[ipld]: https://ipld.io/
[ipld-schema-schema]: https://github.com/ipld/specs/blob/master/schemas/schema-schema.ipldsch
[envelope-rfc]: ./0002-signed-envelopes.md
