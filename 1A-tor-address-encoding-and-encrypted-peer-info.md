# Tor Address Encoding and Encrypted `PeerInfo`

| Lifecycle Stage | Maturity      | Status | Latest Revision   |
|-----------------|---------------|--------|-------------------|
| 1A              | Working Draft | Active | DRAFT, 2019-05-31 |

Authors: [@Zolmeister]

Interest Group: [@yusefnapora], others TBD

[@Zolmeister]: https://github.com/Zolmeister
[@yusefnapora]: https://github.com/yusefnapora

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

### Context:

IPNS addresses are encoded as:

```
peer_id = base58(Multihash_SHA256(protobuf(RSA_PUBLIC_KEY)
# e.g. QmNUhKfcGJyQJnZu3AKn8NoiomDwDCRBicgqPt1YRqJBCz
```

And added to the DHT like so (~ I think):

```
PUT(peer_id, PeerInfo, signature)
GET(peer_id) -> PeerInfo, signature
```

The proposal is to encode IPNS addresses as [Tor rend-spec-v3 onion addresses](https://gitweb.torproject.org/torspec.git/tree/rend-spec-v3.txt#n2029):

```
peer_id = base32(PUBKEY | CHECKSUM | VERSION)
CHECKSUM = SHA3("peerid checksum" | PUBKEY | VERSION)[:2]

where:
  - PUBKEY is the 32 bytes ed25519 public key
  - VERSION is a 1-byte version field (default value '\x03')
  - "peerid checksum" is a constant string
  - CHECKSUM is truncated to two bytes

# e.g. pg6mmjiyjmcrsslvykfwnntlaru7p5svn6y2ymmju6nubxndf4pscryd
```

And added to the DHT like so:

```
PUT(BlindKey, Encrypt(PeerInfo, DeriveKey(peer_id)), signature)
GET(BlindKey) -> EncryptedPeerInfo, signature
```

Where `BlindKey` is derived from the ed25519 keypair using [Tors derivation scheme](https://gitweb.torproject.org/torspec.git/tree/rend-spec-v3.txt#n2161), except without key rotation

Note that `BlindKey` derivation _only_ works for ed25519 keypairs

`Encrypt` and `DeriveKey` follow Tors [hidden service descriptor encryption key derivation](https://gitweb.torproject.org/torspec.git/tree/rend-spec-v3.txt#n1424) (again without shared random)


### Motivation

Adversaries can:
  - discover all services by walking the DHT
  - monitor changes to `PeerInfo` of all services
  - monitor `PeerInfo` requests of other members in the network

### Scope and Rationale

IPNS address calculation, IPNS DHT read/write and validation

### Goals

Significantly improve the privacy of IPNS services

### Expected Feature Set: a summary/enumeration of features the spec provides.

Encrypted `PeerInfo` records and base32 IPNS addressing with inlined signing keys

### Tentative Technical Directions

Add a ney `KeyType` to the public key protobuf

### Address Tradeoffs

  - base32 for DNS
    - always, ux consistency. no multibase
  - version byte at end
    - using a common prefix (`Qm`) makes it much harder for people to distinguish addresses
    - better vanity addresses
  - has checksum
  - fixed signing key type
    - public key is always inline
    - changing signing algorithm requires version byte increment, forces consistency within PeerID versions

### Additional Notes

  - Original writeup: https://github.com/libp2p/specs/issues/139
  - All of this is heavily based on [Tor rend-spec-v3](https://gitweb.torproject.org/torspec.git/tree/rend-spec-v3.txt) which contains much of the implementation details
  - `PUT(Hash(PeerID), Encrypt(PeerInfo, PeerID))` (proposed elsewhere)
    - cannot be signed, because signature verification would require revealing `PeerID` to parties before inserting into the DHT
  - Unlike Tor, `BlindKeys` are not rotated daily using a shared random value
    - The consquences of this have not been explored thorougly
      - One point though is that the position within the DHT does not change over time (so certain network nodes could be targeted for DOS)
  - Tor additionally supports a second encryption layer for records for access control (a 'password' to access the service after querying the DHT)
  - Tor additionally pads their descriptors with `NUL` bytes to 10k, and 'stubs' extra fields to shield access controlled descriptors (which are longer)
  - I would have liked to have added the shared random `BlindKey` rotation, but could not find a suitable generation scheme
    - Tor uses a voting consensus system among their special `HSDir` servers
    - [Algorand](https://medium.com/algorand/algorand-releases-first-open-source-code-of-verifiable-random-function-93c2960abd61) does some neat tricks with VRF, but relies on crypto-assets
    
