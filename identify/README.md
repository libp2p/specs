# Identify v1.0.0

The identify protocol is used to identify a peer and its capabilities.

The protocol works by opening a stream, using `/ipfs/id/1.0.0` as the protocol string.
The peer being identified responds by returning an `Identify` message and closes the
stream.

## The Identify Message

```protobuf
message Identify {
  optional string protocolVersion = 5;
  optional string agentVersion = 6;
  optional bytes publicKey = 1;
  repeated bytes listenAddrs = 2;
  optional bytes observedAddr = 4;
  repeated string protocols = 3;
}
```

### protocolVersion

The protocol version identifies the family of protocols used by the peer.
The current protocol version is `ipfs/0.1.0`; if the protocol major or minor
version does not match the protocol used by the initiating peer, then the connection
is considered unusable and the peer must close the connection.

### agentVersion

This is a free-form string, identifying the implementation of the peer.
The usual format is `agent-name/version`, where `agent-name` is
the name of the program or library and `version` is its semantic version.

### publicKey

This is the public key of the peer, marshalled in binary form as specicfied
in [peer-ids](../peer-ids).


### listenAddrs

These are the addresses on which the peer is listening as multi-addresses.

### observedAddr

This is the connection source address of the stream initiating peer as observed by the peer
being identified; it is a multi-address. The initiator can use this address to infer
the existence of a NAT and its public address.

For example, in the case of a TCP/IP transport the observed addresses will be of the form
`/ip4/x.x.x.x/tcp/xx`. In the case of a circuit relay connection, the observed address will
be of the form `/p2p/QmRelay/p2p-circuit`. In the case of onion transport, there is no
observable source address.

### protocols

This is a list of protocols supported by the peer.
