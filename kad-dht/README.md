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

Records in the DHT are keyed by CID [4], roughly speaking. There are intentions
to move to multihash [5] keys in the future, as certain CID components like the
multicodec are redundant. This will be an incompatible change.

The format of `key` varies depending on message type; however, in all cases, the
distance between the two keys is `XOR(sha256(key1), sha256(key2))`.

* For `GET_VALUE` and `PUT_VALUE`, `key` is an unstructured array of bytes.
  However, all nodes in the DHT will have rules to _validate_ whether or not a
  value is valid for an associated key. For example, the default validator
  accepts keys of the form `/pk/BINARY_PEER_ID` mapped the serialized public key
  associated with the peer ID in question.
* For `ADD_PROVIDER` and `GET_PROVIDERS`, `key` is interpreted and validated as
a CID.
* For `FIND_NODE`, `key` is a binary `PeerId`

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

When `Provide(key)` is called, the DHT finds the closest peers to `key` using
the `FIND_NODE` RPC, and then sends a `ADD_PROVIDER` RPC with its own
`PeerInfo` to each of these peers.

Each peer that receives the `ADD_PROVIDER` RPC should validate that the
received `PeerInfo` matches the sender's `peerID`, and if it does, that peer
must store a record in its datastore the received `PeerInfo` record.

When a node receives a `GET_PROVIDERS` RPC, it must look up the requested
key in its datastore, and respond with any corresponding records in its
datastore, plus a list of closer peers in its routing table.

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

See [protobuf
definition](https://github.com/libp2p/go-libp2p-kad-dht/blob/master/pb/dht.proto)

On any error, the entire stream is reset. This is probably not the behavior we
want.

All RPC messages conform to the following protobuf:
```protobuf
// Record represents a dht record that contains a value
// for a key value pair
message Record {
	// The key that references this record
	bytes key = 1;

	// The actual value this record is storing
	bytes value = 2;

	// Note: These fields were removed from the Record message
	// hash of the authors public key
	//optional string author = 3;
	// A PKI signature for the key+value+author
	//optional bytes signature = 4;

	// Time the record was received, set by receiver
	string timeReceived = 5;
};

message Message {
	enum MessageType {
		PUT_VALUE = 0;
		GET_VALUE = 1;
		ADD_PROVIDER = 2;
		GET_PROVIDERS = 3;
		FIND_NODE = 4;
		PING = 5;
	}

	enum ConnectionType {
		// sender does not have a connection to peer, and no extra information (default)
		NOT_CONNECTED = 0;

		// sender has a live connection to peer
		CONNECTED = 1;

		// sender recently connected to peer
		CAN_CONNECT = 2;

		// sender recently tried to connect to peer repeatedly but failed to connect
		// ("try" here is loose, but this should signal "made strong effort, failed")
		CANNOT_CONNECT = 3;
	}

	message Peer {
		// ID of a given peer.
		bytes id = 1;

		// multiaddrs for a given peer
		repeated bytes addrs = 2;

		// used to signal the sender's connection capabilities to the peer
		ConnectionType connection = 3;
	}

	// defines what type of message it is.
	MessageType type = 1;

	// defines what coral cluster level this query/response belongs to.
	// in case we want to implement coral's cluster rings in the future.
	int32 clusterLevelRaw = 10; // NOT USED

	// Used to specify the key associated with this message.
	// PUT_VALUE, GET_VALUE, ADD_PROVIDER, GET_PROVIDERS
	bytes key = 2;

	// Used to return a value
	// PUT_VALUE, GET_VALUE
	Record record = 3;

	// Used to return peers closer to a key in a query
	// GET_VALUE, GET_PROVIDERS, FIND_NODE
	repeated Peer closerPeers = 8;

	// Used to return Providers
	// GET_VALUE, ADD_PROVIDER, GET_PROVIDERS
	repeated Peer providerPeers = 9;
}
```

Any time a relevant `Peer` record is encountered, the associated multiaddrs
are stored in the node's peerbook.

These are the requirements for each `MessageType`:
* `FIND_NODE`: `key` must be set in the request. `closerPeers` is set in the
response; for an exact match exactly one `Peer` is returned; otherwise `ncp`
(default: 6) closest `Peer`s are returned.

* `GET_VALUE`: `key` must be set in the request.  If `key` is a public key
(begins with `/pk/`) and the key is known, the response has `record` set to
that key. Otherwise, `record` is set to the value for the given key (if found
in the datastore) and `closerPeers` is set to indicate closer peers.

* `PUT_VALUE`: `key` and `record` must be set in the request. The target
node validates `record`, and if it is valid, it stores it in the datastore.

* `GET_PROVIDERS`: `key` must be set in the request. The target node returns
the closest known `providerPeers` (if any) and the closest known `closerPeers`.

* `ADD_PROVIDER`: `key` and `providerPeers` must be set in the request. The
target node verifies `key` is a valid CID, all `providerPeers` that
match the RPC sender's PeerID are recorded as providers.

* `PING`: Target node responds with `PING`. Nodes should respond to this
message but it is currently never sent.

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
