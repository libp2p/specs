# Multistream Select V2

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r1, 2025-11-13  |

Authors: [@raulk], [@marcopolo]

Interest Group: [@ppopth]

[@marcopolo]: https://github.com/marcopolo
[@ppopth]: https://github.com/ppopth
[@raulk]: https://github.com/raulk

## Terminology

Server: The endpoint advertising its supported protocol strings.

Client: The endpoint receiving the advertisement and using protocol string
abbreviations when opening streams.

Abbreviation Tree: The tree data structure that determines the abbreviation to
use for a given protocol string.

Note, A peer can behave as both a client and server. For the purpose of defining
this protocol, it's useful to focus on the client/server interaction.

## Abbreviation Tree

A list of protocol strings are abbreviated by creating a minimal hash prefix
tree.

### Construction

Each protocol string is hashed and inserted into the tree as shallowly as
possible. Each node in the tree has 256 leaf branches representing a byte of the
hash (2^8). If multiple protocol strings share a common byte prefix, they are
distinguished the next level down the tree.

Each protocol string in the tree has a tombstone bit associated with it. This is
set to true if the protocol is currently not supported (but was previously).

A node in the tree may contain a value as well as children. This only happens
when introducing a new supported protocol introduces a conflict. This does not
happen on initial construction.

### Example

```txt
(root)
  |
  +-- 0xaa -> "/some-protocol/a/v1"
  |
  +-- 0xbb -> "/some-protocol/b/v1"
  |
  +-- 0xcc
  |   |
  |   +-- 0x01 -> "/some-protocol/c/v1"
  |   |
  |   +-- 0x02 -> "/some-protocol/c'/v1"
  |
  +-- 0xdd -> "/some-protocol/d/v1" tombstone=true
```

### Inserting a New Protocol String

The protocol string is inserted into the tree as shallowly as possible. If there
is a conflict, the protocol string should be inserted one level down and
duplicate the conflicting protocol string to the new level if it is not
tombstoned. The conflicting protocol string MUST not removed from its original
position as it may still be referenced.

#### Example

Using the initial example as the initial state and we add three new protocol
strings:

1. `"/new-protocol/foo"` that hashes to `0xaa02`. This example highlights a
   conflict with an existing protocol string.
2. `"/new-protocol/bar"` that hashes to `0xee...`. This example highlights no
   conflicts and inserting shallowly.
3. `"/new-protocol/d"` that hashes to `0xdd02`. This example highlights a
   conflict with a tombstoned protocol string.

```txt
(root)
  |
  +-- 0xaa -> "/some-protocol/a/v1"
  |   |
  |   +-- 0x01 -> "/some-protocol/a/v1"
  |   |
  |   +-- 0x02 -> "/new-protocol/foo"
  |
  +-- 0xbb -> "/some-protocol/b/v1"
  |
  +-- 0xcc
  |   |
  |   +-- 0x01 -> "/some-protocol/c/v1"
  |   |
  |   +-- 0x02 -> "/some-protocol/c'/v1"
  |
  +-- 0xdd -> "/some-protocol/d/v1" tombstone=true
  |   |
  |   +-- 0xdd01 -> "/new-protocol/d"
  |
  +-- 0xee -> "/new-protocol/bar"
```

### Removing a Protocol String

For each instance of the protocol string in the tree, the tombstone bit is set
to true. The protocol string MUST not be removed from the tree as that could
lead to inconsistencies if a new protocol string is introduced with the same
prefix hash.

#### Example

Using the initial example as the initial state and we remove protocol
string `"/some-protocol/b/v1"`.

```txt
(root)
  |
  +-- 0xaa -> "/some-protocol/a/v1"
  |
  +-- 0xbb -> "/some-protocol/b/v1" tombstone=true
  |
  +-- 0xcc
  |   |
  |   +-- 0x01 -> "/some-protocol/c/v1"
  |   |
  |   +-- 0x02 -> "/some-protocol/c'/v1"
  |
  +-- 0xdd -> "/some-protocol/d/v1" tombstone=true
```

### Reintroducing a previously removed protocol string

For each instance of the protocol string in the tree, the tombstone bit should
be set to false. The protocol string should then be inserted into the tree as if
inserting a new protocol string. If the protocol string is already present as a
leaf node, no changes are required.

#### Example

Using the example for removing a protocol string as the initial state. We
reintroduce protocol string `"/some-protocol/b/v1"`.

```txt
(root)
  |
  +-- 0xaa -> "/some-protocol/a/v1"
  |
  +-- 0xbb -> "/some-protocol/b/v1"
  |
  +-- 0xcc
  |   |
  |   +-- 0x01 -> "/some-protocol/c/v1"
  |   |
  |   +-- 0x02 -> "/some-protocol/c'/v1"
  |
  +-- 0xdd -> "/some-protocol/d/v1" tombstone=true
```

#### Example with a new leaf node

If the tombstoned protocol string is no longer at a leaf position we need to
insert a new protocol string, as well as untombstoning the existing protocol
string.

Initial State:

```txt
(root)
  |
  +-- 0xaa -> "/some-protocol/a/v1"
  |
  +-- 0xbb -> "/some-protocol/b/v1" tombstone=true
  |   |
  |   +-- 0x02 -> "/some-protocol/b'/v1"
  |
  +-- 0xcc
  |   |
  |   +-- 0x01 -> "/some-protocol/c/v1"
  |   |
  |   +-- 0x02 -> "/some-protocol/c'/v1"
  |
  +-- 0xdd -> "/some-protocol/d/v1" tombstone=true
```

After reintroducing `"/some-protocol/b/v1"`:

```txt
(root)
  |
  +-- 0xaa -> "/some-protocol/a/v1"
  |
  +-- 0xbb -> "/some-protocol/b/v1"
  |   |
  |   +-- 0x01 -> "/some-protocol/b/v1"
  |   |
  |   +-- 0x02 -> "/some-protocol/b'/v1"
  |
  +-- 0xcc
  |   |
  |   +-- 0x01 -> "/some-protocol/c/v1"
  |   |
  |   +-- 0x02 -> "/some-protocol/c'/v1"
  |
  +-- 0xdd -> "/some-protocol/d/v1" tombstone=true
```

## Limits

Implementations SHOULD limit the number of protocol strings they track
(including tombstoned protocol strings).

## Mapping Algorithm

A mapping algorithm maps a protocol string to byte array. This byte array is
used for the abbreviation tree.

SHA256 MUST be used for the mapping algorithm.

TODO: Do we want to consider faster keyed hashes? Risks complicating
implementations.

TODO: Do we need a hash function at all? Would an index into the list of a
server's protocols work instead?

## Initial Server Client Exchange

When a client connects to a server, the server shares all the state necessary to
create an abbreviation tree it can use to communicate with the server. Namely:
the list of supported protocol strings, and the list of previously supported
protocol strings (tombstoned protocol strings).

The client's abbreviation tree will differ from the server's abbreviation tree
only in that protocol strings will only exist at leaf nodes in the client's
abbreviation tree. This is because non-leaf protocol strings only occur when
adding a protocol string to an existing tree.

# Multistream Select V2

## Wire Format

TODO define the wire format of multistream select v2.

## Client opening a new stream

A client identifies the protocol string it wishes to use on a stream by the
minimal hash prefix as determined by the abbreviate stream.

## Server accepting a new stream

The server identifies the protocol string by looking up the minimal hash prefix
in the tree.

## Version Negotiation

Multistream Select V2 does not support negotiating different protocols on a
single stream like Multistream Select V1 does. A client specifies what protocol
they would like to use for a stream and MAY start sending protocol immediately.
If the server does not support this protocol, it MUST close the stream with
error code (TODO specify this).
