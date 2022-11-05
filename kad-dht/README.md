# libp2p Kademlia DHT specification

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 3A              | Recommendation | Active | r1, 2021-10-30  |

Authors: [@raulk], [@jhiesey], [@mxinden]

Interest Group:

[@raulk]: https://github.com/raulk
[@jhiesey]: https://github.com/jhiesey
[@mxinden]: https://github.com/mxinden

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

---

## Overview

The Kademlia Distributed Hash Table (DHT) subsystem in libp2p is a DHT
implementation largely based on the Kademlia [0] whitepaper, augmented with
notions from S/Kademlia [1], Coral [2] and the [BitTorrent DHT][bittorrent].

This specification assumes the reader has prior knowledge of those systems. So
rather than explaining DHT mechanics from scratch, we focus on differential
areas:

1. Specialisations and peculiarities of the libp2p implementation.
2. Actual wire messages.
3. Other algorithmic or non-standard behaviours worth pointing out.

For everything else that isn't explicitly stated herein, it is safe to assume
behaviour similar to Kademlia-based libraries.

Code snippets use a Go-like syntax.

## Definitions

### Replication parameter (`k`)

The amount of replication is governed by the replication parameter `k`. The
recommended value for `k` is 20.

### Distance

In all cases, the distance between two keys is `XOR(sha256(key1),
sha256(key2))`.

### Kademlia routing table

An implementation of this specification must try to maintain `k` peers with
shared key prefix of length `L`, for every `L` in `[0..(keyspace-length - 1)]`,
in its routing table. Given the keyspace length of 256 through the sha256 hash
function, `L` can take values between 0 (inclusive) and 255 (inclusive). The
local node shares a prefix length of 256 with its own key only.

Implementations may use any data structure to maintain their routing table.
Examples are the k-bucket data structure outlined in the Kademlia paper [0] or
XOR-tries (see [go-libp2p-xor]).

### Alpha concurrency parameter (`α`)

The concurrency of node and value lookups are limited by parameter `α`, with a
default value of 3. This implies that each lookup process can perform no more
than 3 inflight requests, at any given time.

## Client and server mode

When the libp2p Kademlia protocol is run on top of a network of heterogeneous
nodes, unrestricted nodes should operate in _server mode_ and restricted nodes,
e.g. those with intermittent availability, high latency, low bandwidth, low
CPU/RAM/Storage, etc., should operate in _client mode_.

As an example, running the libp2p Kademlia protocol on top of the Internet,
publicly routable nodes, e.g. servers in a datacenter, might operate in _server
mode_ and non-publicly routable nodes, e.g. laptops behind a NAT and firewall,
might operate in _client mode_. The concrete factors used to classify nodes into
_clients_ and _servers_ depend on the characteristics of the network topology
and the properties of the Kademlia DHT . Factors to take into account are e.g.
network size, replication factor and republishing period.

Nodes, both those operating in _client_ and _server mode_, add another node to
their routing table if and only if that node operates in _server mode_. This
distinction allows restricted nodes to utilize the DHT, i.e. query the DHT,
without decreasing the quality of the distributed hash table, i.e. without
polluting the routing tables.

Nodes operating in _server mode_ advertise the libp2p Kademlia protocol
identifier via the [identify protocol](../identify/README.md). In addition
_server mode_ nodes accept incoming streams using the Kademlia protocol
identifier. Nodes operating in _client mode_ do not advertise support for the
libp2p Kademlia protocol identifier. In addition they do not offer the Kademlia
protocol identifier for incoming streams.

## DHT operations

The libp2p Kademlia DHT offers the following types of operations:

- **Peer routing**

  - Finding the closest nodes to a given key via `FIND_NODE`.

- **Value storage and retrieval**

  - Storing a value on the nodes closest to the value's key by looking up the
    closest nodes via `FIND_NODE` and then putting the value to those nodes via
    `PUT_VALUE`.

  - Getting a value by its key from the nodes closest to that key via
    `GET_VALUE`.

- **Content provider advertisement and discovery**

  - Adding oneself to the list of providers for a given key at the nodes closest
    to that key by finding the closest nodes via `FIND_NODE` and then adding
    oneself via `ADD_PROVIDER`.

  - Getting providers for a given key from the nodes closest to that key via
    `GET_PROVIDERS`.

In addition the libp2p Kademlia DHT offers the auxiliary _bootstrap_ operation.

### Peer routing

The below is one possible algorithm to find nodes closest to a given key on the
DHT. Implementations may diverge from this base algorithm as long as they adhere
to the wire format and make progress towards the target key.


Let's assume we’re looking for nodes closest to key `Key`. We then enter an
iterative network search.

We keep track of the set of peers we've already queried (`Pq`) and the set of
next query candidates sorted by distance from `Key` in ascending order (`Pn`).
At initialization `Pn` is seeded with the `k` peers from our routing table we
know are closest to `Key`, based on the XOR distance function (see [distance
definition](#distance)).

Then we loop:

1. > The lookup terminates when the initiator has queried and gotten responses
   from the k (see [replication parameter `k`](#replication-parameter-k)) closest nodes it has seen.

   (See Kademlia paper [0].)

   The lookup might terminate early in case the local node queried all known
   nodes, with the number of nodes being smaller than `k`.
2. Pick as many peers from the candidate peers (`Pn`) as the `α` concurrency
   factor allows. Send each a `FIND_NODE(Key)` request, and mark it as _queried_
   in `Pq`.
3. Upon a response:
	1. If successful the response will contain the `k` closest nodes the peer
       knows to the key `Key`. Add them to the candidate list `Pn`, except for
       those that have already been queried.
	2. If an error or timeout occurs, discard it.
4. Go to 1.

### Value storage and retrieval

#### Value storage

To _put_ a value the DHT finds `k` or less closest peers to the key of the value
using the `FIND_NODE` RPC (see [peer routing section](#peer-routing)), and then
sends a `PUT_VALUE` RPC message with the record value to each of the peers.

#### Value retrieval

When _getting_ a value from the DHT, implementions may use a mechanism like
quorums to define confidence in the values found on the DHT, put differently a
mechanism to determine when a query is _finished_. E.g. with quorums one would
collect at least `Q` (quorum) responses from distinct nodes to check for
consistency before returning an answer.

Entry validation: Should the responses from different peers diverge, the
implementation should use some validation mechanism to resolve the conflict and
select the _best_ result (see [entry validation section](#entry-validation)).

Entry correction: Nodes that returned _worse_ records and nodes that returned no
record but where among the closest to the key, are updated via a direct
`PUT_VALUE` RPC call when the lookup completes. Thus the DHT network eventually
converges to the best value for each record, as a result of nodes collaborating
with one another.

The below is one possible algorithm to lookup a value on the DHT.
Implementations may diverge from this base algorithm as long as they adhere to
the wire format and make progress towards the target key.

Let's assume we’re looking for key `Key`. We first try to fetch the value from the
local store. If found, and `Q == { 0, 1 }`, the search is complete.

Otherwise, the local result counts for one towards the search of `Q` values. We
then enter an iterative network search.

We keep track of:

* the number of values we've fetched (`cnt`).
* the best value we've found (`best`), and which peers returned it (`Pb`)
* the set of peers we've already queried (`Pq`) and the set of next query
  candidates sorted by distance from `Key` in ascending order (`Pn`).
* the set of peers with outdated values (`Po`).

At initialization we seed `Pn` with the `α` peers from our routing table we know
are closest to `Key`, based on the XOR distance function.

Then we loop:

1. If we have collected `Q` or more answers, we cancel outstanding requests and
   return `best`. If there are no outstanding requests and `Pn` is empty we
   terminate early and return `best`. In either case we notify the peers holding
   an outdated value (`Po`) of the best value we discovered, or holding no value
   for the given key, even though being among the `k` closest peers to the key,
   by sending `PUT_VALUE(Key, best)` messages.
2. Pick as many peers from the candidate peers (`Pn`) as the `α` concurrency
   factor allows. Send each a `GET_VALUE(Key)` request, and mark it as _queried_
   in `Pq`.
3. Upon a response:
	1. If successful, and we receive a value:
		1. If this is the first value we've seen, we store it in `best`, along
           with the peer who sent it in `Pb`.
		2. Otherwise, we resolve the conflict by e.g. calling
           `Validator.Select(best, new)`:
			1. If the new value wins, store it in `best`, and mark all formerly
               “best" peers (`Pb`) as _outdated peers_ (`Po`). The current peer
               becomes the new best peer (`Pb`).
			2. If the new value loses, we add the current peer to `Po`.
	2. If successful with or without a value, the response will contain the
       closest nodes the peer knows to the key `Key`. Add them to the candidate
       list `Pn`, except for those that have already been queried.
	3. If an error or timeout occurs, discard it.
4. Go to 1.

#### Entry validation

Implementations should validate DHT entries during retrieval and before storage
e.g. by allowing to supply a record `Validator` when constructing a DHT node.
Below is a sample interface of such a `Validator`:

``` go
// Validator is an interface that should be implemented by record
// validators.
type Validator interface {
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

`Validate()` should be a pure function that reports the validity of a record. It
may validate a cryptographic signature, or else. It is called on two occasions:

1. To validate values retrieved in a `GET_VALUE` query.
2. To validate values received in a `PUT_VALUE` query before storing them in the
   local data store.

Similarly, `Select()` is a pure function that returns the best record out of 2
or more candidates. It may use a sequence number, a timestamp, or other
heuristic of the value to make the decision.

### Content provider advertisement and discovery

Nodes must keep track of which nodes advertise that they provide a given key
(CID). These provider advertisements should expire, by default, after 24 hours.
These records are managed through the `ADD_PROVIDER` and `GET_PROVIDERS`
messages.

#### Content provider advertisement

When the local node wants to indicate that it provides the value for a given
key, the DHT finds the closest peers to the key using the `FIND_NODE` RPC (see
[peer routing section](#peer-routing)), and then sends an `ADD_PROVIDER` RPC with
its own `PeerInfo` to each of these peers.

Each peer that receives the `ADD_PROVIDER` RPC should validate that the received
`PeerInfo` matches the sender's `peerID`, and if it does, that peer should store
the `PeerInfo` in its datastore. Implementations may choose to not store the
addresses of the providing peer e.g. to reduce the amount of required storage or
to prevent storing potentially outdated address information.

#### Content provider discovery

_Getting_ the providers for a given key is done in the same way as _getting_ a
value for a given key (see [getting values section](#getting-values)) except
that instead of using the `GET_VALUE` RPC message the `GET_PROVIDERS` RPC
message is used.

When a node receives a `GET_PROVIDERS` RPC, it must look up the requested
key in its datastore, and respond with any corresponding records in its
datastore, plus a list of closer peers in its routing table.

### Bootstrap process

The bootstrap process is responsible for keeping the routing table filled and
healthy throughout time. The below is one possible algorithm to bootstrap.
Implementations may diverge from this base algorithm as long as they adhere to
the wire format and keep their routing table up-to-date, especially with peers
closest to themselves.

The process runs once on startup, then periodically with a configurable
frequency (default: 5 minutes). On every run, we generate a random peer ID and
we look it up via the process defined in [peer routing](#peer-routing). Peers
encountered throughout the search are inserted in the routing table, as per
usual business.

This is repeated as many times per run as configuration parameter `QueryCount`
(default: 1). In addition, to improve awareness of nodes close to oneself,
implementations should include a lookup for their own peer ID.

Every repetition is subject to a `QueryTimeout` (default: 10 seconds), which
upon firing, aborts the run.

## RPC messages

Remote procedure calls are performed by:

1. Opening a new stream.
2. Sending the RPC request message.
3. Listening for the RPC response message.
4. Closing the stream.

On any error, the stream is reset.

Implementations may choose to re-use streams by sending one or more RPC request
messages on a single outgoing stream before closing it. Implementations must
handle additional RPC request messages on an incoming stream.

All RPC messages sent over a stream are prefixed with the message length in
bytes, encoded as an unsigned variable length integer as defined by the
[multiformats unsigned-varint spec][uvarint-spec].

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
    //
    // Hash of the authors public key
    // optional string author = 3;
    // A PKI signature for the key+value+author
    // optional bytes signature = 4;

    // Time the record was received, set by receiver
    // Formatted according to https://datatracker.ietf.org/doc/html/rfc3339
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

These are the requirements for each `MessageType`:

* `FIND_NODE`: In the request `key` must be set to the binary `PeerId` of the
  node to be found. In the response `closerPeers` is set to the `k` closest
  `Peer`s.

* `GET_VALUE`: In the request `key` is an unstructured array of bytes. `record`
  is set to the value for the given key (if found in the datastore) and
  `closerPeers` is set to the `k` closest peers.

* `PUT_VALUE`: In the request `record` is set to the record to be stored and `key`
  on `Message` is set to equal `key` of the `Record`. The target node validates
  `record`, and if it is valid, it stores it in the datastore and as a response
  echoes the request.

* `GET_PROVIDERS`: In the request `key` is set to a CID. The target node
  returns the closest known `providerPeers` (if any) and the `k` closest known
  `closerPeers`.

* `ADD_PROVIDER`: In the request `key` is set to a CID. The target node verifies
  `key` is a valid CID, all `providerPeers` that match the RPC sender's PeerID
  are recorded as providers.

* `PING`: Deprecated message type replaced by the dedicated [ping
  protocol][ping]. Implementations may still handle incoming `PING` requests for
  backwards compatibility. Implementations must not actively send `PING`
  requests.

Note: Any time a relevant `Peer` record is encountered, the associated
multiaddrs are stored in the node's peerbook.

---

## Practical Examples
<details>
  <summary>Searching the <b>IPFS</b> Kad DHT for a Peer's Public Key</summary><blockquote>
  
  &nbsp;
  ##### Lets find the Public Key for the IPFS Bootstrap node with the PeerID "QmaCpDMGvV2BGHeYERUEnRQAwe3N8SzbUtfsmvsqQLuvuJ"
  1. Derive the key to search the DHT for
     1. We're searching for a public key record therefore we're going to use the `/pk/` namespace
     2. And we want the public key associated with the PeerID `QmaCpDMGvV2BGHeYERUEnRQAwe3N8SzbUtfsmvsqQLuvuJ`
     3. Putting these together we get `/pk/QmaCpDMGvV2BGHeYERUEnRQAwe3N8SzbUtfsmvsqQLuvuJ`
     4. But we need to turn this into it's raw byte representation
     5. For the namespace and forward slashes we just convert the utf8 string into bytes
     6. For the PeerID we need to remember that this is a [base58btc encoding](peer-ids.md#decoding) 
      ---

      | String | / | pk | / |  Qm | aCpDMGvV2BGHeYERUEnRQAwe3N8SzbUtfsmvsqQLuvuJ |
      |--------|---|----|---|-----|----------------------------------------------|
      | Part | slash | namespace | slash | Multihash prefix | Multihash digest | 
      | Encoding | utf8 | utf8 | utf8 | base58btc | base58btc | 
      | Bytes (UInt8) | 47 | 112, 107 | 47 | 18, 32 | 176, 74, 87, 212, 14, 202, 19, 136, 9, 241, 57, 167, 107, 18, 4, 67, 51, 195, 116, 3, 145, 201, 191, 28, 233, 216, 226, 26, 121, 33, 11, 253 | 

      ---
      7. Key = [47, 112, 107, 47, 18, 32, 176, 74, 87, 212, 14, 202, 19, 136, 9, 241, 57, 167, 107, 18, 4, 67, 51, 195, 116, 3, 145, 201, 191, 28, 233, 216, 226, 26, 121, 33, 11, 253]
  
  2. Prepare an [RPCMessage](#rpc-messages) with the `type` set to `GET_VALUE` and the `key` set to the above bytes

  3. In this example, if we send this message directly to the bootstrap node (at `/ip4/104.131.131.82/tcp/4001/p2p/QmaCpDMGvV2BGHeYERUEnRQAwe3N8SzbUtfsmvsqQLuvuJ`), we should get a response that has the `record` parameter set with the following data   
  ```protobuf 
  message Record {
    // The values Key (note that it matches the key we searched for)
    bytes key = [47, 112, 107, 47, 18, 32, 176, 74, 87, 212, 14, 202, 19, 136, 9, 241, 57, 167, 107, 18, 4, 67, 51, 195, 116, 3, 145, 201, 191, 28, 233, 216, 226, 26, 121, 33, 11, 253];

    // The Marshaled Public Key
    bytes value = [8, 0, 18, 166, 4, 48, 130, 2, 34, 48, 13, 6, 9, 42, 134, 72, 134, 247, 13, 1, 1, 1, 5, 0, 3, 130, 2, 15, 0, 48, 130, 2, 10, 2, 130, 2, 1, 0, 161, 245, 192, 231, 192, 213, 229, 86, 175, 192, 232, 69, 102, 248, 197, 101, 119, 58, 219, 84, 141, 220, 33, 156, 169, 104, 134, 19, 160, 9, 108, 45, 253, 6, 152, 4, 200, 73, 104, 84, 91, 156, 157, 241, 157, 209, 49, 204, 132, 8, 183, 120, 29, 247, 221, 250, 242, 8, 164, 42, 130, 21, 35, 206, 3, 149, 81, 100, 166, 45, 202, 182, 189, 16, 221, 38, 248, 80, 117, 23, 86, 124, 161, 40, 240, 10, 5, 109, 134, 54, 185, 84, 157, 219, 89, 202, 114, 118, 40, 119, 92, 144, 189, 145, 214, 37, 26, 219, 223, 211, 107, 246, 138, 9, 195, 191, 230, 158, 27, 21, 135, 232, 243, 26, 75, 85, 175, 200, 9, 94, 123, 111, 102, 131, 22, 95, 156, 14, 240, 173, 27, 34, 216, 183, 55, 73, 238, 2, 170, 70, 86, 108, 213, 247, 169, 255, 110, 177, 9, 159, 227, 107, 54, 58, 189, 78, 18, 147, 16, 138, 109, 71, 58, 52, 158, 119, 172, 161, 94, 73, 178, 15, 254, 97, 180, 34, 46, 179, 166, 52, 232, 72, 29, 113, 167, 253, 206, 234, 136, 162, 4, 79, 165, 206, 221, 225, 222, 227, 20, 226, 120, 128, 188, 113, 60, 165, 120, 129, 70, 132, 232, 94, 13, 33, 207, 244, 14, 35, 195, 65, 241, 62, 225, 160, 100, 82, 242, 132, 102, 73, 153, 134, 41, 115, 229, 29, 105, 43, 87, 140, 217, 183, 222, 137, 215, 134, 173, 107, 174, 188, 248, 223, 195, 67, 219, 142, 218, 67, 74, 21, 146, 149, 145, 145, 124, 82, 191, 22, 116, 19, 89, 20, 157, 14, 112, 146, 188, 145, 153, 40, 241, 213, 178, 92, 180, 139, 15, 144, 167, 160, 91, 14, 178, 154, 220, 169, 147, 248, 147, 198, 251, 19, 122, 83, 165, 196, 112, 168, 163, 9, 181, 116, 187, 79, 216, 8, 121, 189, 231, 220, 194, 55, 234, 242, 206, 154, 23, 185, 25, 48, 50, 223, 153, 200, 191, 85, 25, 135, 86, 30, 226, 100, 160, 151, 48, 249, 2, 150, 16, 87, 22, 37, 224, 208, 225, 226, 167, 249, 4, 105, 166, 164, 128, 237, 8, 207, 155, 76, 58, 240, 86, 123, 254, 154, 191, 71, 0, 121, 216, 204, 125, 127, 34, 239, 200, 53, 152, 248, 108, 158, 6, 120, 202, 247, 158, 34, 153, 169, 156, 71, 200, 208, 87, 231, 243, 184, 175, 64, 24, 92, 141, 212, 153, 161, 193, 103, 195, 88, 215, 171, 131, 175, 101, 129, 148, 76, 224, 184, 182, 189, 44, 254, 75, 248, 12, 140, 158, 127, 97, 254, 148, 129, 109, 247, 158, 18, 174, 94, 130, 197, 136, 248, 148, 184, 111, 213, 153, 218, 89, 18, 248, 117, 77, 226, 162, 63, 45, 21, 41, 132, 90, 85, 112, 167, 45, 141, 133, 55, 50, 91, 149, 221, 60, 105, 217, 202, 48, 184, 24, 108, 32, 23, 13, 16, 149, 91, 125, 162, 22, 130, 44, 115, 2, 3, 1, 0, 1];

    // The time at which the record was received
    string timeReceived = "2022-11-05T12:57:46.346597716Z";
  }
  ```
  4. The Record's `value` is the Marshaled Public Key belonging to the Peer with ID `QmaCpDMGvV2BGHeYERUEnRQAwe3N8SzbUtfsmvsqQLuvuJ`.

  5. Important! When querying the DHT for values you should follow the [value retrieval](#value-retrieval) algorithm stated above.
</blockquote>
</details>

---

## References

[0]: Maymounkov, P., & Mazières, D. (2002). Kademlia: A Peer-to-Peer Information System Based on the XOR Metric. In P. Druschel, F. Kaashoek, & A. Rowstron (Eds.), Peer-to-Peer Systems (pp. 53–65). Berlin, Heidelberg: Springer Berlin Heidelberg. https://doi.org/10.1007/3-540-45748-8_5

[1]: Baumgart, I., & Mies, S. (2014). S / Kademlia : A practicable approach towards secure key-based routing S / Kademlia : A Practicable Approach Towards Secure Key-Based Routing, (June). https://doi.org/10.1109/ICPADS.2007.4447808

[2]: Freedman, M. J., & Mazières, D. (2003). Sloppy Hashing and Self-Organizing Clusters. In IPTPS. Springer Berlin / Heidelberg. Retrieved from www.coralcdn.org/docs/coral-iptps03.ps

[bittorrent]: http://bittorrent.org/beps/bep_0005.html

[uvarint-spec]: https://github.com/multiformats/unsigned-varint

[ping]: https://github.com/libp2p/specs/issues/183

[go-libp2p-xor]: https://github.com/libp2p/go-libp2p-xor
