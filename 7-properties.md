7 Properties
============

## 7.1 Communication Model - Streams

The Network layer handles all the problems of connecting to a peer, and exposes
simple bidirectional streams. Users can both open a new stream
(`NewStream`) and register a stream handler (`SetStreamHandler`). The user
is then free to implement whatever wire messaging protocol she desires. This
makes it easy to build peer-to-peer protocols, as the complexities of
connectivity, multi-transport support, flow control, and so on, are handled.

To help capture the model, consider that:

- `NewStream` is similar to making a Request in an HTTP client.
- `SetStreamHandler` is similar to registering a URL handler in an HTTP server

So a protocol, such as a DHT, could:

```go
node := p2p.NewNode(peerid)

// register a handler, here it is simply echoing everything.
node.SetStreamHandler("/helloworld", func (s Stream) {
  io.Copy(s, s)
})

// make a request.
buf1 := []byte("Hello World!")
buf2 := make([]byte, len(buf1))

stream, _ := node.NewStream("/helloworld", peerid) // open a new stream
stream.Write(buf1)  // write to the remote
stream.Read(buf2)   // read what was sent back
fmt.Println(buf2)   // print what was sent back
```

## 7.2 Ports - Constrained Entrypoints

In the Internet of 2015, we have a processing model where a program may be
running without the ability to open multiple -- or even single -- network
ports. Most hosts are behind NAT, whether of household ISP variety or new
containerized data-center type. And some programs may even be running in
browsers, with no ability to open sockets directly (sort of). This presents
challenges to completely peer-to-peer networks that aspire to connect _any_
hosts together -- whether they're running on a page in the browser, or in
a container within a container.

IPFS only needs a single channel of communication with the rest of the
network. This may be a single TCP or UDP port, or a single connection
through WebSockets or WebRTC. In a sense, the role of the TCP/UDP network
stack -- i.e. multiplexing applications and connections -- may now be forced
to happen at the application level.

## 7.3 Transport Protocols

IPFS is transport-agnostic. It can run on any transport protocol. The
`ipfs-addr` format (which is an IPFS-specific
[multiaddr](https://github.com/jbenet/multiaddr)) describes the transport.
For example:

```sh
# ipv4 + tcp
/ip4/10.1.10.10/tcp/29087/ipfs/QmVcSqVEsvm5RR9mBLjwpb2XjFVn5bPdPL69mL8PH45pPC

# ipv6 + tcp
/ip6/2601:9:4f82:5fff:aefd:ecff:fe0b:7cfe/tcp/1031/ipfs/QmRzjtZsTqL1bMdoJDwsC6ZnDX1PW1vTiav1xewHYAPJNT

# ipv4 + udp + udt
/ip4/104.131.131.82/udp/4001/udt/ipfs/QmaCpDMGvV2BGHeYERUEnRQAwe3N8SzbUtfsmvsqQLuvuJ

# ipv4 + udp + utp
/ip4/104.131.67.168/udp/1038/utp/ipfs/QmU184wLPg7afQjBjwUUFkeJ98Fp81GhHGurWvMqwvWEQN
```

IPFS delegtes the transport dialing to a multiaddr-based network package, such
as [go-multiaddr-net](https://github.com/jbenet/go-multiaddr-net). It is
advisable to build modules like this in other languages, and scope the
implementation of other transport protocols.

Some of the transport protocols we will be using:

- UTP
- UDT
- SCTP
- WebRTC (SCTP, etc)
- WebSockets
- TCP Remy

## 7.4 Non-IP Networks

Efforts like [NDN](http://named-data.net) and
[XIA](http://www.cs.cmu.edu/~xia/) are new architectures for the Internet,
which are closer to the model IPFS uses than what IP provides today. IPFS
will be able to operate on top of these architectures trivially, as there
are no assumptions made about the network stack in the protocol. Implementations
will likley need to change, but changing implementations is vastly easier than
changing protocols.

## 7.5 On the wire

We have the **hard constraint** of making IPFS work across _any_ duplex stream (an outgoing and an incoming stream pair, any arbitrary connection) and work on _any_ platform.

To make this work, IPFS has to solve a few problems:

- [Protocol Multiplexing](#751-protocol-multiplexing) - running multiple protocols over the same stream
  - [multistream](#752-multistream-self-describing-protocol-stream) - self-describing protocol streams
  - [multistream-select](#753-multistream-selector-self-describing-protocol-stream-selector) - a self-describing protocol selector
  - [Stream Multiplexing](#754-stream-multiplexing) - running many independent streams over the same wire
- [Portable Encodings](#755-portable-encodings) - using portable serialization formats
- [Secure Communications](#756-secure-communication) - using ciphersuites to establish security and privacy (like TLS)

### 7.5.1 Protocol-Multiplexing

Protocol Multiplexing means running multiple different protocols over the same stream. This could happen sequentially (one after the other), or concurrently (at the same time, with their messages interleaved). We achieve protocol multiplexing using three pieces:

- [multistream](#752-multistream-self-describing-protocol-stream) - self-describing protocol streams
- [multistream-select](#753-multistream-selector-self-describing-protocol-stream-selector) - a self-describing protocol selector
- [Stream Multiplexing](#754-stream-multiplexing) - running many independent streams over the same wire

### 7.5.2 multistream - self-describing protocol stream

[multistream](https://github.com/jbenet/multistream) is a self-describing protocol stream format. It is extremely simple. Its goal is to define a way to add headers to protocols that describe the protocol itself. It is sort of like adding versions to a protocol, but being extremely explicit.

For example:

```
/ipfs/QmVXZiejj3sXEmxuQxF2RjmFbEiE9w7T82xDn3uYNuhbFb/ipfs-dht/0.2.3
<dht-message>
<dht-message>
...
```

### 7.5.3 multistream-selector - self-describing protocol stream selector

[multistream-select](https://github.com/jbenet/multistream/tree/master/multistream) is a simple [multistream](https://github.com/jbenet/multistream) protocol that allows listing and selecting other protocols. This means that Protomux has a list of registered protocols, listens for one, and then _nests_ (or upgrades) the connection to speak the registered protocol. This takes direct advantage of multistream: it enables interleaving multiple protocols, as well as inspecting what protocols might be spoken by the remote endpoint.

For example:

```
/ipfs/QmdRKVhvzyATs3L6dosSb6w8hKuqfZK2SyPVqcYJ5VLYa2/multistream-select/0.3.0
/ipfs/QmVXZiejj3sXEmxuQxF2RjmFbEiE9w7T82xDn3uYNuhbFb/ipfs-dht/0.2.3
<dht-message>
<dht-message>
...
```

### 7.5.4 Stream Multiplexing

Stream Multiplexing is the process of multiplexing (or combining) many different streams into a single one. This is a complicated subject because it enables protocols to run concurrently over the same wire, and all sorts of notions regarding fairness, flow control, head-of-line blocking, etc. start affecting the protocols. In practice, stream multiplexing is well understood and there are many stream multiplexing protocols. To name a few:

- HTTP/2
- SPDY
- QUIC
- SSH

IPFS nodes are free to support whatever stream multiplexors they wish, on top of the default one. The default one is there to enable even the simplest of nodes to speak multiple protocols at once. The default multiplexor will be HTTP/2 (or maybe QUIC?), but implementations for it are sparse, so we are beginning with SPDY. We simply select which protocol to use with a multistream header.

For example:

```
/ipfs/QmdRKVhvzyATs3L6dosSb6w8hKuqfZK2SyPVqcYJ5VLYa2/multistream-select/0.3.0
/ipfs/Qmb4d8ZLuqnnVptqTxwqt3aFqgPYruAbfeksvRV1Ds8Gri/spdy/3
<spdy-header-opening-a-stream-0>
/ipfs/QmVXZiejj3sXEmxuQxF2RjmFbEiE9w7T82xDn3uYNuhbFb/ipfs-dht/0.2.3
<dht-message>
<dht-message>
<spdy-header-opening-a-stream-1>
/ipfs/QmVXZiejj3sXEmxuQxF2RjmFbEiE9w7T82xDn3uYNuhbFb/ipfs-bitswap/0.3.0
<bitswap-message>
<bitswap-message>
<spdy-header-selecting-stream-0>
<dht-message>
<dht-message>
<dht-message>
<dht-message>
<spdy-header-selecting-stream-1>
<bitswap-message>
<bitswap-message>
<bitswap-message>
<bitswap-message>
...
```

### 7.5.5 Portable Encodings

In order to be ubiquitous, we _must_ use hyper-portable format encodings, those that are easy to use in various other platforms. Ideally these encodings are well-tested in the wild, and widely used. There may be cases where multiple encodings have to be supported (and hence we may need a [multicodec](https://github.com/jbenet/multicodec) self-describing encoding), but this has so far not been needed.
For now, we use [protobuf](https://github.com/google/protobuf) for all protocol messages exclusively, but other good candidates are [capnp](https://capnproto.org/), [bson](http://bsonspec.org/), and [ubjson](http://ubjson.org/).

### 7.5.6 Secure Communications

The wire protocol is -- of course -- wrapped with encryption. We use cyphersuites similar to TLS. This is explained further in the [network spec](./#encryption).
