# RFC 0002 - Signed Address Records

- Start Date: 2019-10-04
- Related Issues:
  - [libp2p/issues/47](https://github.com/libp2p/libp2p/issues/47)
  - [go-libp2p/issues/436](https://github.com/libp2p/go-libp2p/issues/436)
  
## Abstract

This RFC proposes a method for distributing _self-certified_ address records,
which contain a peer's publicly reachable listen addresses. The record also
includes a signature, which proves that the record was produced by the peer
itself and not tampered with in transit.

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
that address could be marked as publicly-routable and advertised in a new record.

Regarding the fourth point about ambiguous addresses, it would also be desirable
for the address record to include a notion of "routability," which would
indicate how "accessible" the address is likely to be. This would allow us to
mark an address as "LAN-only," if we know that it is not mapped to a publicly
reachable address but would still like to distribute it to local peers.

## Address Record Format

There are many potential data structures that we could use to store and transmit
address information. This section sketches out a possible design using
[IPLD][ipld], although we may end up adopting a different format. Everything in
this section is subject to change as part of the RFC process.

These types are defined using IPLD's Schema notation, the best reference for
which I'm currently aware of is [its own schema definition][ipld-schema-schema].

```sh

## How accessible we believe a given address to be.
## Maybe include params? We could potentially have a subnet mask for local addresses
type Routability enum {
  | "GLOBAL"   ## Available on the public internet
  | "LOCAL"    ## Available on a local network (probably in a private address range)
  | "LOOPBACK" ## Available on a loopback address on the same machine
  | "UNKNOWN"  ## Catch all (may include in-memory transports, etc)
}

## How confident we are in the validity of an address
type Confidence enum {
  | "CONFIRMED"   ## We have verified that we're reachable on this address
  | "UNCONFIRMED" ## We suspect, but have not confirmed that we're reachable
  | "INVALID"     ## We know that this address is invalid and should be deleted
  | "UNKNOWN"     ## No assertions about validity one way or another
}

## A tuple of an address, how "routable" (public / private, etc) the address is,
## and how confident we are in its validity.
type AddressInfo struct {
  addr Bytes ## Binary multiaddr
  routability Routability
  confidence Confidence
}

## A point-in-time snapshot of all addresses (plus their info) that we know
## about at the time we issued the record.
##
type AddressState struct {
  ## The subject of this record. Who do these addresses belong to?
  subject PeerRef

  ## When was this record constructed?
  issuedAt Timestamp 
  
  ## A list of all AddressInfo records that apply at the current moment.
  addresses List {
    valueType &AddressInfo
  }
}

## A signed envelope containing an `AddressState` struct, our 
## public key, and a signature of the state (verifiable with public key).
type AddressEnvelope {
  state AddressState
  
  # Public key of issuer.
  pubkey Bytes 

  # Signature of `state`. Can be verified with `pubkey`.
  # Maybe it's better to sign a merkle link to `state` instead...
  sig Bytes
}

## Unix epoch timestamp, UTC timezone. TODO: what precision?
type Timestamp Int

# binary multihash of public key
type PeerId Bytes

## A peer id, plus a peer-specific version clock. 
## Represents a peer _at a moment in time_, where time is loosely defined as
## unit-less quantity that's always increasing. Version
## numbers must increase monotonically but do not need to be strictly
## sequential. If you don't want to preserve state across restarts or coordinate
## a counter, you can use epoch timestamps as version numbers.
type PeerRef struct {
  peer PeerId
  version Int
}
```

The idea with the structure above is that you send some metadata along with your
addresses: your "routability", and your own confidence in the validity of the
address. This is wrapped in an `AddressInfo` struct along with the address
itself.

Then you have a big list of `AddressInfo`s, which we put in an `AddressState`.
An `AddressState` identifies the `subject` of the record, who is also the
issuing peer. We could potentially split that out into a separate `subject` and
`issuer` field, which would let peers make statements about each other in
addition to making statements about themselves. That complicates things though,
and may not be worth it.

The state and a signature of it are wrapped in an `AddressEnvelope`, along with
the public key that produced the signature. Recipients must validate that the
public key is consistent with the peer id of the `subject` and validate the sig.

Here's an example. Alice has an address that she thinks is publicly reachable
but has not confirmed. She also has a LAN-local address that she knows is valid,
but not routable via the public internet:

```javascript
  {

    pubkey: "<alice's public key>",
    state: {
      subject: {
        peer: "QmAlice...",
        version: 23456
      },
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
    },
    sig: "<signature of state>"
  }
```

If Alice wants to publish her address to a public shared resource like a DHT,
she should omit `LOCAL` and other unreachable addresses, and peers should
likewise filter out `LOCAL` addresses from public sources.

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
