# Connection Establishment in libp2p

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r0, 2019-05-30  |

Authors: [@yusefnapora]

Interest Group: TBD

[@yusefnapora]: https://github.com/yusefnapora

## Overview

Let's clarify a few terms before we get too deep.

A **connection** is a reliable, bidirectional communication channel between two
libp2p peers that provides **security** and the ability to open multiple
logically independent **streams**.

**Security** in this context means that all communications (after an initial
handshake) are encrypted, and that the identity of each peer is cryptographicaly
verifiable by the other peer.

**Streams** are reliable, bidirectional channels that are multiplexed over a
libp2p connection. They must support backpressure, which prevents receivers from
being flooded by data from eager senders. They can also be "half closed",
meaning that a stream can be closed for writing data but still open to receiving
data and vice versa.

Support for multiple streams ensures that a single connection between peers can
support a wide variety of interactions, each with their own protocol. This is
especially helpful if connections are difficult to establish due to NAT
traversal issues or other connectivity barriers.

Connections take place over an underlying **transport**, for example TCP
sockets, websockets, or various protocols layered over UDP.

While some transport protocols like [QUIC](https://www.chromium.org/quic)
have "built in" security and stream multiplexing, others such as TCP need to
have those capabilites layered on top of the "raw" transport connection.

When the base capabilities of security and stream multiplexing are not natively
supported by the underlying transport protocol, a **connection upgrade** process
occurs to augment the raw transport connection with the required features.

libp2p peers can both initiate connections to other peers and accept incoming
connections. We use the term **dial** to refer to initiating outbound
connections, and **listen** to refer to accepting inbound connections.

## Protocol Negotiation

One of libp2p's core design goals is to be adaptable to many network
environments, including those that don't yet exist. To provide this flexibility,
the connection upgrade process supports multiple protocols for connection
security and stream multiplexing and allows peers to select which to use for
each connection. 

The process of selecting protocols is called **protocol negotiation**. In
addition to its role in the connection upgrade process, protocol negotiation is
also used whenever a new stream is opened over an existing connection. This
allows libp2p applications to route application-specific protocols to the
correct handler functions.

### multistream-select

libp2p uses a protocol called multistream-select for protocol negotiation. Below
we cover the basics of multistream-select and its use in libp2p. For more
details, see [the multistream-select repository][mss].

Each protocol supported by a peer is identified using a unique string called a
**protocol id**. While any string can be used, the most common and recommended
format is a path-like structure containing a short name and a version number,
separated by `/` characters. For example: `/mplex/1.0.0` identifies version
1.0.0 of the [`mplex` stream multiplexing protocol][mplex]. multistream-select
itself has a protocol id of `/multistream/1.0.0`.

Before engaging in the multistream-select negotiation process, it is assumed
that the peers have already established a bidirectional communication channel,
which may or may not have the security and multiplexing capabilities of a libp2p
connection. If those capabilities are missing, multistream-select is used in
the connection upgrade process to determine how to provide them, as described
[below](#upgrading-connections).

Messages are sent encoded as UTF-8 byte strings, and they are always followed by
a `\n` newline character. Each message is also prefixed with its length in bytes
(including the newline), encoded as an unsigned variable-length integer
according to the rules of the [multiformats unsigned varint spec][uvarint].

For example, the string `"na"` is sent as the following bytes (shown here in
hex):

```
0x036e610a
```
The first byte is the varint-encoded length (`0x03`), followed by `na` (`0x6e 0x61`),
then the newline (`0x0a`).


The basic multistream-select interaction flow looks like this:

![see multistream.plantuml for diagram source](multistream.svg)

Let's walk through the diagram above. The peer initiating the connection is
called the **Dialer**, and the peer accepting the connection is the
**Listener**.

The Dialer first opens a channel to the Listener. This channel could either be a
new connection or a new stream multiplexed over an existing connection.

Next, both peers will send the multistream protocol id to establish that they
want to use multistream-select. Note that both sides may send the initial
multistream protocol id simultaneously, without waiting to recieve data from the
other side. If either side recieves anything other than the multistream protocol
id as the first message, they abort the negotiation process.

Once both peers have agreed to use multistream-select, the Dialer sends the
protocol id for the protocol they would like to use. If the Listener supports
that protocol, it will respond by echoing back the protocol id, which signals
agreement. If the protocol is not supported, the Listener will respond with the
string `"na"` to indicate that the requested protocol is Not Available.

If the peers agree on a protocol, multistream-select's job is done, and future
traffic over the channel will adhere to the rules of the agreed-upon protocol.

If a peer recieves a `"na"` response to a proposed protocol id, they can either
try again with a different protocol id or close the channel.


## Upgrading Connections

libp2p is designed to support a variety of transport protocols, including those
that do not natively support the core libp2p capabilities of security and stream
multiplexing. The process of layering capabilites onto "raw" transport
connections is called "upgrading" the connection.

Because there are many valid ways to provide the libp2p capabilities, the
connection upgrade process uses protocol negotiation to decide which specific
protocols to use for each capability. The protocol negotiation process uses
multistream-select as described [above](#protocol-negotiation).

When raw connections need both security and multiplexing, security is always
established first, and the negotiation for stream multiplexing takes place over
the encrypted channel.

Here's an example of the connection upgrade process:

![see conn-upgrade.plantuml for diagram source](conn-upgrade.svg)

First, the peers both send the multistream protocol id to establish that they'll
use multistream-select to negotiate protocols for the connection upgrade.

Next, the Dialer proposes the [TLS protocol](../tls/tls.md) for encryption, but
the Listener rejects the proposal as they don't support TLS.

The Dialer then proposes the [SECIO protocol](../secio), which is supported by
the Listener. The Listener echoes back the protocol id for SECIO to indicate
agreement.

At this point the SECIO protocol takes over, and the peers exchange the SECIO
handshake to establish a secure channel. If the SECIO handshake fails, the
connection establishment process aborts. If successful, the peers will use the
secured channel for all future communications, including the remainder of the
connection upgrade process.

Once security has been established, the peers negotiate which stream multiplexer
to use. The negotiation process works in the same manner as before, with the
dialing peer proposing a multiplexer by sending its protocol id, and the
listening peer responding by either echoing back the supported id or sending
`"na"` if the multiplexer is unsupported.

Once security and stream multiplexing are both established, the connection
upgrade process is complete, and both peers are able to use the resulting libp2p
connection to open new secure multiplexed streams.


### Stream Multiplexing

## Practical Considerations

### Interoperability

### Dialer State Management

#### Peer Metadata Storage

### Connection Management

### Connection Lifecycle Events

[mss]: https://github.com/multiformats/multistream-select
[uvarint]: https://github.com/multiformats/unsigned-varint
[mplex]: ../mplex/README.md
