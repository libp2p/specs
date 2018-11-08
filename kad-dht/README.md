# libp2p Kademlia DHT specification

The Kademlia Distributed Hash Table (DHT) subsystem in libp2p is a DHT
implementation largely based on the Kademlia [0] whitepaper, augmented with
notions from S/Kademlia [1], Coral [2] and mainlineDHT \[3\].

This specification assumes the reader has prior knowledge of those systems. So
rather than explaining DHT mechanics from scratch, we focus on differential
areas:

1. Specialisations and peculiarities of the libp2p implementation.
2. Actual wire messages.
3. Other algorithmic or non-standard behaviours worth pointing out.

For everything else that isn't explicitly stated herein, it is safe to assume
behaviour similar to Kademlia-based libraries.

Code snippets use a Go-like syntax.

## Authors

* Protocol Labs.

## Editors

* [Raúl Kripalani](https://github.com/raulk)
* [John Hiesey](https://github.com/jhiesey)

## Distance function (dXOR)

The libp2p Kad DHT uses the **XOR distance metric** as defined in the original
Kademlia paper [0]. Peer IDs are normalised through the SHA256 hash function.

For recap, `dXOR(sha256(id1), sha256(id2))` is the number of common leftmost
bits between SHA256 of each peer IDs. The `dXOR` between us and a peer X
designates the bucket index that peer X will take up in the Kademlia routing
table.

## Kademlia routing table

The data structure backing this system is a k-bucket routing table, closely
following the design outlined in the Kademlia paper [0]. The default value for
`k` is 20, and the maximum bucket count matches the size of the SHA256 function,
i.e. 256 buckets.

The routing table is unfolded lazily, starting with a single bucket a position 0
(representing the most distant peers), and splitting it subsequently as closer
peers are found, and the capacity of the nearmost bucket is exceeded.

## Alpha concurrency factor (α)

The concurrency of node and value lookups are limited by parameter `α`, with a
default value of 3. This implies that each lookup process can perform no more
than 3 inflight requests, at any given time.

## Record keys

Records in the DHT are keyed by CID [4]. There are intentions to move to
multihash [5] keys in the near future, as certain CID components like the
multicodec are redundant.

## Interfaces

The libp2p Kad DHT implementation satisfies the routing interfaces:

```go
type Routing interface {
	ContentRouting
	PeerRouting
	ValueStore

	// Kicks off the bootstrap process.
	Bootstrap(context.Context) error
}

// ContentRouting is used to find information about who has what content.
type ContentRouting interface {
	// Provide adds the given CID to the content routing system. If 'true' is
	// passed, it also announces it, otherwise it is just kept in the local
	// accounting of which objects are being provided.
	Provide(context.Context, cid.Cid, bool) error

	// Search for peers who are able to provide a given key.
	FindProvidersAsync(context.Context, cid.Cid, int) <-chan pstore.PeerInfo
}

// PeerRouting is a way to find information about certain peers.
//
// This can be implemented by a simple lookup table, a tracking server,
// or even a DHT (like herein).
type PeerRouting interface {
	// FindPeer searches for a peer with given ID, returns a pstore.PeerInfo
	// with relevant addresses.
	FindPeer(context.Context, peer.ID) (pstore.PeerInfo, error)
}

// ValueStore is a basic Put/Get interface.
type ValueStore interface {
	// PutValue adds value corresponding to given Key.
	PutValue(context.Context, string, []byte, ...ropts.Option) error

	// GetValue searches for the value corresponding to given Key.
	GetValue(context.Context, string, ...ropts.Option) ([]byte, error)
}
```

## Value lookups

When looking up an entry in the DHT, the implementor should collect at least `Q`
(quorum) responses from distinct nodes to check for consistency before returning
an answer.

Should the responses be different, the `Validator.Select()` function is used to
resolve the conflict and select the _best_ result.

**Entry correction.** Nodes that returned _worse_ records are updated via a
direct `PUT_VALUE` RPC call when the lookup completes. Thus the DHT network
eventually converges to the best value for each record, as a result of nodes
collaborating with one another.

### Algorithm

Let's assume we’re looking for key `K`. We first try to fetch the value from the local store. If found, and `Q == { 0, 1 }`, the search is complete.

Otherwise, the local result counts for one towards the search of `Q` values. We then enter an iterative network search.

We keep track of:

* the number of values we've fetched (`cnt`).
* the best value we've found (`best`), and which peers returned it (`Pb`)
* the set of peers we've already queried (`Pq`) and the set of next query candidates sorted by distance from `K` in ascending order (`Pn`).
* the set of peers with outdated values (`Po`). 

**Initialization**: seed `Pn` with the `α` peers from our routing table we know are closest to `K`, based on the XOR distance function.

**Then we loop:**

*WIP (raulk): lookup timeout.*

1. If we have collected `Q` or more answers, we cancel outstanding requests, return `best`, and we notify the peers holding an outdated value (`Po`) of the best value we discovered, by sending `PUT_VALUE(K, best)` messages. _Return._
2. Pick as many peers from the candidate peers (`Pn`) as the `α` concurrency factor allows. Send each a `GET_VALUE(K)` request, and mark it as _queried_ in `Pq`.
3. Upon a response:
	1. If successful, and we receive a value:
		1. If this is the first value we've seen, we store it in `best`, along
           with the peer who sent it in `Pb`.
		2. Otherwise, we resolve the conflict by calling `Validator.Select(best,
           new)`:
			1. If the new value wins, store it in `best`, and mark all formerly
               “best" peers (`Pb`) as _outdated peers_ (`Po`). The current peer
               becomes the new best peer (`Pb`).
			2. If the new value loses, we add the current peer to `Po`.
	2. If successful without a value, the response will contain the closest
       nodes the peer knows to the key `K`. Add them to the candidate list `Pn`,
       except for those that have already been queried.
	3. If an error or timeout occurs, discard it.
4. Go to 1.

## Entry validation

When constructing a DHT node, it is possible to supply a record `Validator`
object conforming to this interface:

``` // Validator is an interface that should be implemented by record
validators. type Validator interface {

	// Validate validates the given record, returning an error if it's
	// invalid (e.g., expired, signed by the wrong key, etc.).
	Validate(key string, value []byte) error

	// Select selects the best record from the set of records (e.g., the
	// newest).
	//
	// Decisions made by select should be stable.
	Select(key string, values [][]byte) (int, error)
}
```

`Validate()` is a pure function that reports the validity of a record. It may
validate a cryptographic signature, or else. It is called on two occasions:

1. To validate incoming values in response to `GET_VALUE` calls.
2. To validate outgoing values before storing them in the network via
   `PUT_VALUE` calls.

Similarly, `Select()` is a pure function that returns the best record out of 2
or more candidates. It may use a sequence number, a timestamp, or other
heuristic to make the decision.

## Public key records

Apart from storing arbitrary values, the libp2p Kad DHT stores node public keys
in records under the `/pk` namespace. That is, the entry `/pk/<peerID>` will
store the public key of peer `peerID`.

DHT implementations may optimise public key lookups by providing a
`GetPublicKey(peer.ID) (ci.PubKey)` method, that, for example, first checks if
the key exists in the local peerstore.

The lookup for public key entries is identical to a standard entry lookup,
except that a custom `Validator` strategy is applied. It checks that equality
`SHA256(value) == peerID` stands when:

1. Receiving a response from a `GET_VALUE` lookup.
2. Storing a public key in the DHT via `PUT_VALUE`.

The record is rejected if the validation fails.

## Provider records

Nodes must keep track of which nodes advertise that they provide a given key
(CID). These provider advertisements should expire, by default, after 24 hours.
These records are managed through the `ADD_PROVIDER` and `GET_PROVIDERS`
messages.

_WIP (jhiesey): explain what actually happens when `Provide()` is called._

For performance reasons, a node may prune expired advertisements only
periodically, e.g. every hour.

## Node lookups

_WIP (raulk)._

## Bootstrap process
The bootstrap process is responsible for keeping the routing table filled and
healthy throughout time. It runs once on startup, then periodically with a
configurable frequency (default: 5 minutes).

On every run, we generate a random node ID and we look it up via the process
defined in *Node lookups*. Peers encountered throughout the search are inserted
in the routing table, as per usual business.

This process is repeated as many times per run as configuration parameter
`QueryCount` (default: 1). Every repetition is subject to a `QueryTimeout`
(default: 10 seconds), which upon firing, aborts the run.

## RPC messages

_WIP (jheisey): consider just dumping a nicely formatted and simplified
protobuf._

See [protobuf
definition](https://github.com/libp2p/go-libp2p-kad-dht/blob/master/pb/dht.proto)

On any error, the entire stream is reset. This is probably not the behavior we
want.

* `FIND_NODE(key bytes) -> (nodes PeerInfo[])` Finds the `ncp` (default:6) nodes
closest to `key` from the routing table and returns an array of `PeerInfo`s. If
a node with id equal to `key` is found, returns only the `PeerInfo` for that
node.
* `GET_VALUE(key bytes) -> (record Record, closerPeers PeerInfo[])` If `key` is
a public key (begins with `/pk/`) and the key is known, returns a `Record`
containing that key. Otherwise, returns the `Record` for the given key (if in
the datastore) and an array of `PeerInfo`s for closer peers.
* `PUT_VALUE(key bytes, value Record) -> ()` Validates `value` and, if it is
valid, stores it in the datastore.
* `GET_PROVIDERS(key bytes) -> (providerPeers PeerInfo[], closerPeers
PeerInfo[])` Verifies `key` is a valid CID. Returns `providerPeers` if in the
providers cache, and an array of closer peers.
* `ADD_PROVIDER(key, providerPeers PeerInfo[]) -> ()` Verifies `key` is a valid
CID. For each provider `PeerInfo` that matches the sender's id and contains one
or more multiaddrs, that provider info is added to the peerbook and the peer is
added as a provider for the CID.
* `PING() -> ()` Tests connectivity to destination node. Currently never sent.

# Appendix A: differences in implementations

The `addProvider` handler behaves differently across implementations:
  * in js-libp2p-kad-dht, the sender is added as a provider unconditionally.
  * in go-libp2p-kad-dht, it is added once per instance of that peer in the
    `providerPeers` array.

---

# References

[0]: Maymounkov, P., & Mazières, D. (2002). Kademlia: A Peer-to-Peer Information System Based on the XOR Metric. In P. Druschel, F. Kaashoek, & A. Rowstron (Eds.), Peer-to-Peer Systems (pp. 53–65). Berlin, Heidelberg: Springer Berlin Heidelberg. https://doi.org/10.1007/3-540-45748-8_5

[1]: Baumgart, I., & Mies, S. (2014). S / Kademlia : A practicable approach towards secure key-based routing S / Kademlia : A Practicable Approach Towards Secure Key-Based Routing, (June). https://doi.org/10.1109/ICPADS.2007.4447808

[2]: Freedman, M. J., & Mazières, D. (2003). Sloppy Hashing and Self-Organizing Clusters. In IPTPS. Springer Berlin / Heidelberg. Retrieved from www.coralcdn.org/docs/coral-iptps03.ps

[3]: [bep_0005.rst_post](http://bittorrent.org/beps/bep_0005.html)

[4]: [GitHub - ipld/cid: Self-describing content-addressed identifiers for distributed systems](https://github.com/ipld/cid)

[5]: [GitHub - multiformats/multihash: Self describing hashes - for future proofing](https://github.com/multiformats/multihash)
