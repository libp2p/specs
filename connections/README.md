# Connection Establishment in libp2p

> Specification for connection handshake between libp2p peers

Revision: draft 1, 2019-05-13

Authors:
- @yusefnapora (yusef@protocol.ai)

TK: brief intro that outlines what's covered in the spec. also add TOC

## Overview

Let's clarify a few terms before we get too deep.

A **connection** is a reliable, bidirectional communication channel between two
libp2p peers that provides **security** and the ability to open multiple
logically independent **streams**.

**Security** in this context means that all communications (after an initial
handshake) are encrypted, and that the identity of each peer is cryptographicaly
verifiable by the other peer.

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
protocol id. While any string can be used, the most common format is a path-like
structure containing a short name and a version number, separated by `/`
characters. For example: `/mplex/1.0.0` identifies version 1.0.0 of the [`mplex`
stream multiplexing protocol][mplex]. multistream-select itself has a protocol
id of `/multistream/1.0.0`.

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
want to use multistream-select. If either side recieves anything other than the
multistream protocol id as the first message, they abort the negotiation
process.

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

### Connection Security

### Stream Multiplexing

## Practical Considerations

### Interoperability

### Connection Management


[mss]: https://github.com/multiformats/multistream-select
[uvarint]: https://github.com/multiformats/unsigned-varint
[mplex]: ../mplex/README.md
