# IPRS - InterPlanetary Record System spec
Authors: [Juan Benet](github.com/jbenet)

Reviewers:

- [Kristoffer Strom](github.com/krl)
- [Jeromy Johnson](github.com/whyrusleeping)
- [W. Trevor King](github.com/wking)

* * *

The [Spec](../) for IPRS.

This spec defines IPRS (InterPlanetary Record System) a system for distributed record keeping meant to operate across networks that may span massive distances (>1AU) or suffer long partitions (>1 earth yr).
IPRS is meant to establish a common record-keeping layer to solve common problems. It is a well-layered protocol: it is agnostic to underlying replication and transport systems, and it supports a variety of different applications.
IPRS is part of the InterPlanetary File System Project, and is general enough to be used in a variery of other systems.

## Definitions

### Records

A (distributed) `record` is a piece of data meant to be transmitted and stored in various computers across a network. It carries a `value` external to the record-keeping system, which clients of the record system use. For example: a namespace record may store the value of a name. All record systems include a notion of _record validity_, which allows users of the record system to verify whether the value of a record is correct and valid under the user's circumstances. For example, a record's validity may depend upon a cryptographic signature, a range of spacetime, et-cetera.

### Record System

A (distributed) `record system` is a protocol which defines a method for crafting, serializing, distributing, verifying, and using records over computer networks. (e.g. the Domain Name System).


- `crafting` - construction of a record (the process of calculating the values of a record)
- `serializing` - formating a record into a bitstring.
- `distributing` - transportation of a record from one set of computers to another.
- `verifying` - checking a record's values to ensure correctness and validity.


### Validity Schemes

A `validity scheme` is a small sub-protocol that defines how a record's _validity_ is to be calculated. `Validity` is the quality of a record being usable by a user at a particular set of circumstances (e.g. a range of time). It is distinct from `correctness` in that `correctness` governs whether the record was correctly constructed, and `validity` governs whether a record may still be used. All _valid_ records must be _correct_. For simplicity, the process of checking correctness is included in the `validity scheme`.

For example, suppose Alice and Bob want to store records on a public bulletin board. To make sure their records are not tampered with, Alice and Bob decide they will include cryptographic signatures. This can ensure correctness. Further, they also agree to add new records every day, to detect whether their records are being replayed or censored. Thus, their `validity scheme` might be:

```go
type Record struct {
  Value     []byte
  Expires   time.Time
  Signature []byte
}

func signablePart(r *Record) []byte {
  var sigbuf bytes.Buffer
  sigbuf.Write(r.Value)
  sigbuf.Write(r.Expires)
  return sigbuf.Bytes()
}

func MakeRecord(value []byte, authorKey crypto.PrivateKey) Record {
  rec := Record{}
  rec.Value = value

  // establish an expiration date
  rec.Expires = time.Now() + time.Day

  // cryptographically sign the record
  rec.Signature = authorKey.Sign(signablePart(rec))

  return rec
}

func VerifyRecord(rec Record, authorKey crypto.PublicKey) (ok bool) {

  // always check the signature first
  sigok := authorKey.Verify(rec.Signature, signablePart(rec))
  if !sigok {
    return false // sig did not check out! forged record?
  }

  // check the expiration.
  if rec.Expires < time.Now() {
    return false // not valid anymore :(
  }

  // everything seems ok!
  return true
}
```

Note that even in such a simple system, we already called out to two other systems Alice and Bob are subscribing to:

- a _Public Key Infrastructure_ (PKI) that lets Alice and Bob know each other's keys, and verify the validity of messages authored by each other.
- a _Time Infrastructure_ (TI) that lets Alice and Bob agree upon a common notion of time intervals and validity durations.

Both of these are large systems on their own, which impose constraints and security parameters on the record system. For example, if Alice and Bob think that NTP timestamps are a good TI, the validity of their records is dependent on their ability to establish an accurate NTP timestamp securely (i.e. they need secure access to shared clocks). Another TI might be to "use the last observed record", and this also is dependent on having a secure announcement channel.

IPRS is _Validity Scheme Agnostic_, meaning that it seeks to establish a common way to craft and distribute records for users of a system without necessarily tying them down to specific world-views (e.g. "NTP is a secure way to keep time", "The CA system is a secure PKI"), or _forcing_ them to work around specific system choices that impose constraints unreasonable for their use case (e.g. "Real-Time Video Over TOR")

### Merkle DAG and IPFS Objects

A merkle dag is a directed acyclic graph whose links are (a) hashes of the edge target, and (b) contained within the edge source. (syn. merkle tree, hash tree)

In this spec, _the merkle dag_ (specific one) refers to the IPFS merkle dag. _IPFS Object_ refers to objects in the merkle dag, which follow the IPFS merkledag format. (Read those specs)


## Constraints

IPRS has the following _hard_ constraints:

- **MUST** be transport agnostic. (transport refers to how computers communicate).
- **MUST** be replication agnostic. (replication refers to the protocol computers use to transfer and propagate whole records and other objects)
- **MUST** be validity scheme agnostic. (validity scheme includes PKI, TI, and other "agreed upon" trusted infrastructure)
- **MUST** be trustless: no trusted third parties are imposed by IPRS (though some may be adopted by a validity scheme. e.g. root CAs in the CA system PKI, or a blockchain in a blockchain TI). In most cases, users may have to trust each other (as they must trust the record value -- e.g. DNS), but in some cases there may be cryptographic schemes that enable full trustlessness.


It is easy to be agnostic to transport, replication, and validity scheme as long as users can expect to control or agree upon the programs or protocols used in concert with IPRS. Concretely, the user can select specific transports or validity schemes to suit the user's application constraints. It is the user's responsibility to ensure both record crafters and verifiers agree upon these selections.

## Construction

### The Objects

IPRS records are expressed as [merkledag](../merkledag) objects. This means that the records are linked authenticated data structures, and can be natively replicated over IPFS itself and other merkledag distribution systems.

The objects:

- A `Record` object expresses a value, a validity scheme, and validity data.
- A `Signature` object could be used to sign and authenticate a record.
- An `Encryption` object could be used to encrypt a record.

```go
Record Node {
  Scheme   Link // link to a validity scheme
  Value    Link // link to an object representing the value.
  Version  Data // record version number
  Validity Data // data needed to satisfy the validity scheme
}
```

To achieve good performance, record storage and transfer should bundle all the necessary objects and transmit them together. While "the record object" is only one of the dag objects, "the full record" means a bundle of all objects needed to fully represent, verify, and use the record. (This recommendation does not necessarily include data that records _describe_, for example an ipfs provider record (which signals to consumers that certain data is available) would not include the data itself as part of "the full record").

### The Interface

The IPRS interface is below. It has a few types and functions. We use the Go language to express it, but this is language agnostic.

```go
// Record is the base type. user can define other types that
// extend Record.
type Record struct {
  Scheme    Link // link to the validity scheme
  Signature Link // link to a cryptographic signature over the rest of record
  Value     Data // an opaque value
}

// Validator is a function that returns whether a record is valid.
// Users provide their own Validator implementations.
type Validator func(r *Record) (bool, error)

// Order is a function that sorts two records based on validity.
// This means that one record should be preferred over the other.
// there must be a total order. if return is 0, then a == b.
// Return value is -1, 0, 1.
type Order func(a, b *Record) int

// Marshal/Unmarshal specifies a way to code the record
type Marshal(r *Record) ([]byte, error)
type Unmarshal(r *Record, []byte) (error)
```

### Interface Example

For example, Alice and Bob earlier could use the following interface:

```go
type Record struct {
  Scheme    Link // link to the validity scheme
  Expires   Data // datetime at which record expires
  Value     Data // an opaque value
}


func Validator(r *Record) (bool, error) {
  authorKey := recordSigningKey(r)

  // always check the signature first
  sigok := authorKey.Verify(r.Signature, signablePart(r))
  if !sigok {
    return false, errors.New("invalid signature. forged record?")
  }

  // check the expiration.
  if r.Expires < time.Now() {
    return false, errors.New("record expired.")
  }

  return true, nil
}

func Order(a, b *Record) int {
  if a.Expires > b.Expires {
    return 1
  }
  if a.Expires < b.Expires {
    return -1
  }

  // only return 0 if records are the exact same record.
  // otherwise, if the ordering doesn't matter (in this case
  // because the expiry is the same) return one of them
  // deterministically. Comparing the hashes takes care of this.
  ra := a.Hash()
  rb := b.Hash()
  return bytes.Compare(ra, rb)
}

func Marshal(r *Record) ([]byte, error) {
  return recordProtobuf.Marshal(r)
}

func Unmarshal(r *Record, d []byte) (error) {
  return recordProtobuf.Unmarshal(r, d)
}
```

## Example Record Types

For ease of use, IPRS implementations should include a set of common record types:

- signed, valid within a datetime range
- signed, expiring after a Time-To-Live
- signed, based on ancestry (chain)
- signed, with cryptographic freshness


### Signed, valid within a datetime range

This record type uses digital signatures (and thus a PKI) and timestamps (and thus a TI). It establishes that a record is valid during a particular datetime range. 0 (beginning of time), and infinity (end of time) can express unbounded validity.

### Signed, expiring after a Time-To-Live

This record type uses digital signatures (and thus a PKI) and TTLs (and thus a TI). It establishes that a record is valid for a certain amount of time after a particular event. For example, an event may be "upon receipt" to specify that a record is valid for a given amount of time after a processor first receives it. This is equivalent to the way DNS sets expiries.

### Signed, based on ancestry (chain)

This record type uses digital signatures (and thus a PKI) and merkle-links to other, previous records. It establishes that the "most recent" record (merkle-ordered) is the most valid. This functions similar to a git commit chain.

### Signed, with cryptographic freshness

This record type uses digital signatures (and thus a PKI) and a cryptographic notion of freshness (and therefore a TI). It establishes that records are only valid if within some threshold of recent time. It is similar to a TTL.
