# Plaintext Secure Channel

> An insecure connection handshake **for non-production environments.**

> **⚠️ Intended only for debugging and interoperability testing purposes. ⚠️**

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r0, 2019-05-27  |


Authors: [@yusefnapora]

Interest Group: [@raulk], [@Warchant], [@Stebalien], [@mhchia]

[@yusefnapora]: https://github.com/yusefnapora
[@raulk]: https://github.com/raulk
[@Warchant]: https://github.com/Warchant
[@Stebalien]: https://github.com/Stebalien
[@mhchia]: https://github.com/mhchia

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Overview

Secure communications are a key feature of libp2p, and encrypted transport is
configured by default in libp2p implementations to encourage security for all
production traffic. However, there are some use cases such as testing in which
encryption is unnecessary. For such cases, the plaintext "security" protocol can
be used. By conforming to the same interface as real security adapters like
[SECIO][secio-spec] and [TLS][tls-spec], the plaintext module can be used as a
drop-in replacement when encryption is not needed.

As the name suggests, the plaintext security module does no encryption, and all
data is transmitted in plain text. However, peer identity in libp2p is [derived
from public keys][peer-id-spec], even when peers are communicating over an
insecure channel. For this reason, peers using the plaintext protocol still
exchange public keys and peer ids when connecting to each other.

It bears repeating that the plaintext protocol was designed for development and
testing **ONLY**, and **MUST NOT** be used in production environments. No
encryption or authentication of any kind is provided. Also note that enabling
the plaintext module will effectively nullify the security guarantees of any
other security modules that may be enabled, as an attacker will be able to
negotiate a plaintext connection at any time.

This document describes the exchange of peer ids and keys that occurs when
initiating a plaintext connection. This exchange happens after the plaintext
protocol has been negotiated as part of the [connection upgrade
process][conn-spec-conn-upgrade].

## Protocol Id and Version History

The plaintext protocol described in this document has the protocol id of
`/plaintext/2.0.0`. 

An earlier version, `/plaintext/1.0.0`, was implemented in several languages,
but it did not include any exchange of public keys or peer ids. This led to
undefined behavior in parts of libp2p that assumed the presence of a peer id.

As version `1.0.0` had no associated wire protocol, it was never specified.

## Messages

Peers exchange their peer id and public key encoded in a
[protobuf][protobuf-spec] message using the protobuf version 2 syntax.

``` protobuf
syntax = "proto2";

message Exchange {
  optional bytes id = 1;
  optional PublicKey pubkey = 2;
}
```

The `id` field contains the peer's id encoded as a [multihash][multihash],
using the binary multihash encoding.

The `PublicKey` message uses the same definition [specified in the peer id
spec][peer-id-spec-pubkey-message]. For reference, it is defined as follows:

``` protobuf
enum KeyType {
	RSA = 0;
	Ed25519 = 1;
	Secp256k1 = 2;
	ECDSA = 3;
}

message PublicKey {
	required KeyType Type = 1;
	required bytes Data = 2;
}
```

The encoding of the `Data` field in the `PublicKey` message is specified in the
[key encoding section of the peer id spec][peer-id-spec-key-encoding].

## Protocol

### Prerequisites

Prior to undertaking the exchange described below, it is assumed that we have
already established a dedicated bidirectional channel between both parties, and
that they have negotiated the [plaintext protocol
id](#protocol-id-and-version-history) as described in the [protocol negotiation
section of the connection establishment spec][conn-spec-protocol-negotiation].

### Message Framing

All messages sent over the wire are prefixed with the message length in bytes,
encoded as an unsigned variable length integer as defined by the [multiformats
unsigned-varint spec][uvarint-spec].

### Exchange

Once the plaintext protocol has been negotiated, both peers immediately send an
`Exchange` message containing their peer id and public key.

Upon receiving an `Exchange` message from the remote peer, each side will
validate that the given peer id is consistent with the given public key by
deriving a peer id from the key and asserting that it's a match with the `id`
field in the `Exchange` message.

Dialing a peer in libp2p requires knowledge of the listening peer's peer id. As
a result, the dialing peer ALSO verifies that the peer id presented by the
listening peer matches the peer id that they attempted to dial. As the listening
peer has no prior knowledge of the dialer's id, only one peer is able to perform
this additional check.

Once each side has received the `Exchange` message, they may store the public
key and peer id for the remote peer in their local peer metadata storage (e.g.
go-libp2p's [peerstore][go-libp2p-peerstore], or js-libp2p's
[peer-book][js-peer-book]).

Following delivery and verification of `Exchange` messages, the plaintext
protocol is complete. Should a verification or timeout error occur, the
connection MUST be terminated abruptly.

The connection is now ready for insecure and unauthenticated data exchange.
While we do exchange public keys upfront, replay attacks and forgery are
trivial, and we perform no authentication of messages. Therefore, we reiterate
the unsuitability of `/plaintext/2.0.0` for production usage.

[protobuf-spec]: https://developers.google.com/protocol-buffers/docs/reference/proto2-spec
[secio-spec]: ../secio/README.md
[tls-spec]: ../tls/tls.md
[peer-id-spec]: ../peer-ids/peer-ids.md
[peer-id-spec-pubkey-message]: ../peer-ids/peer-ids.md#keys
[peer-id-spec-key-encoding]: ../peer-ids/peer-ids.md#how-keys-are-encoded-and-messages-signed
[uvarint-spec]: https://github.com/multiformats/unsigned-varint
[multihash]: https://github.com/multiformats/multihash
[conn-spec-conn-upgrade]: ../connections/README.md#connection-upgrade
[conn-spec-protocol-negotiation]: ../connections/README.md#protocol-negotiation
[go-libp2p-peerstore]: https://github.com/libp2p/go-libp2p-peerstore
[js-peer-book]: https://github.com/libp2p/js-peer-book
