# libp2p over HTTP <!-- omit in toc -->

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r0, 2022-11-10  |

Authors: [@marcopolo]

Interest Group: [@marcopolo], [@mxinden], [@marten-seemann]

[@marcopolo]: https://github.com/mxinden
[@mxinden]: https://github.com/mxinden
[@marten-seemann]: https://github.com/marten-seemann

# Table of Contents <!-- omit in toc -->
- [Context](#context)
  - [Why not two separate stacks?](#why-not-two-separate-stacks)
  - [Why HTTP rather than a custom request/response protocol?](#why-http-rather-than-a-custom-requestresponse-protocol)
- [Implementation](#implementation)
  - [HTTP over libp2p streams](#http-over-libp2p-streams)
  - [libp2p over plain HTTPS](#libp2p-over-plain-https)
  - [Choosing between libp2p streams vs plain HTTPS](#choosing-between-libp2p-streams-vs-plain-https)
- [Implementation recommendations](#implementation-recommendations)
  - [Example – Go](#example--go)
- [Prior art](#prior-art)

# Context

HTTP is everywhere. Especially in CDNs, cloud offerings, and caches.

HTTP on libp2p and libp2p on HTTP are both commonly requested features. This has
come up recently at [IPFS Camp 2022](https://2022.ipfs.camp/) and especially in
the [data transfer track]. One aspect of the discussion makes it seem like you
can use HTTP _OR_ use libp2p, but that isn't the case. Before this spec you
could use the HTTP protocol on top of a libp2p stream (with little to no extra
cost). And this spec outlines how to use libp2p _on top of_ HTTP.

This spec defines a new libp2p abstraction for stateless request/response
protocols. This abstraction is notably nothing new, it is simply HTTP. Being
HTTP, This abstraction can run over a plain TCP+TLS HTTP (henceforth referred to
as _plain https_) or on top of a libp2p stream.

## Why not two separate stacks?

Having libp2p as the abstraction over _how_ the HTTP request gets sent gives developers a lot of benefits for free, such as:

1. NAT traversal: You can make an HTTP request to a peer that's behind a NAT.
1. Fewer connections: If you already have a libp2p connection, we can use use that to create a stream for the HTTP request. The HTTP request will be faster since you don't have to pay the two round trips to establish the connection.
1. Allows JS clients to make HTTPS requests to _any_ peer via WebTransport or WebRTC.
1. Allows more reuse of the protocol logic, just like how applications can integrate GossipSub, bitswap, graphsync, and Kademlia.
1. You get mutual authentication of peer IDs automatically.


## Why HTTP rather than a custom request/response protocol?

HTTP has been around for 30+ years, and it isn't going anywhere. Developers are already very familiar with it. There's is no need to reinvent the wheel here.

# Implementation

## HTTP over libp2p streams

If we have an existing libp2p connection that supports streams, we can run the HTTP protocol as follows:

Client:
1. Open a new stream to the target peer.
1. Negotiate the `/libp2p-http` protocol.
1. Use this stream for HTTP. (i.e. start sending the request)
1. Close the write side when finished uploading the HTTP request.
1. Close the stream when the response is received.

Server:
1. Register a stream handler for the `/libp2p-http` protocol.
1. On receiving a new stream speaking `/libp2p-http`, parse the HTTP request and pass it to the HTTP handler.
1. Write the response from the HTTP handler to the stream.
1. Close the stream when finished writing the response.

## libp2p over plain HTTPS

This is nothing more than a thin wrapper over standard HTTP. The only thing
libp2p should do here is ensure that we verify the peer's TLS certificate as
defined by the [tls spec](../tls/tls.md). This SHOULD be interoperable with standard HTTP clients who pass a correct TLS cert. For example curl should work fine:

```
$ curl --insecure --cert ./client.cert --key ./client.key https://127.0.0.1:9561/echo -d "Hello World"

Hello World
```

## Choosing between libp2p streams vs plain HTTPS

Implementations SHOULD choose a libp2p stream if an existing libp2p connection
is available. If there is an existing HTTP connection, then implementations
SHOULD use that connection rather than starting a new libp2p connection. If
there is no connection implementations may choose either to create a new HTTP
connection or a libp2p connection or expose this as an option to users.

# Implementation recommendations

Each implementation should decide how this works, but the general recommendations are:

1. Make this look and feel like a normal HTTP client and server. There's no
benefit of doing things differently here, and the familiarity will let people
build things faster.

1. Aim to make the returned libp2p+HTTP objects interop with the general HTTP ecosystem of the language.

## Example – Go

We create a host as normal, but enable HTTP:
```
h, err := libp2p.New(libp2p.WithHTTP(
    HTTPConfig: HTTPConfig{
        EnableHTTP:     true,
        // Enable
        HTTPServerAddr: multiaddr.StringCast("/ip4/127.0.0.1/tcp/9561/tls/http"),
    }))
```

We can define HTTP Handlers using standard types:
```
h1.SetHTTPHandler("/echo", func(peer peer.ID, w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(200)
    io.Copy(w, r.Body)
})
```

We can create a client that accepts standard types
```
    // client is a standard http.Client
	client, err := h2.NewHTTPClient(h1.ID())
	require.NoError(t, err)

	resp, err := client.Post("/echo", "application/octet-stream", bytes.NewReader([]byte("Hello World")))
```

For more details see the implementation [PR](https://github.com/libp2p/go-libp2p/pull/1874).

# Prior art

- rust-libp2p's request-response protocol: https://github.com/libp2p/rust-libp2p/tree/master/protocols/request-response.
- go-libp2p's [go-libp2p-http].
- The Indexer project uses [go-libp2p-stream](https://github.com/libp2p/go-libp2p-gostream) to do [HTTP over libp2p](https://github.com/filecoin-project/storetheindex/blob/main/dagsync/p2p/protocol/head/head.go).

[data transfer track]: (https://youtube.com/watch?v=VRn_U8ytvok&feature=share&si=EMSIkaIECMiOmarE6JChQQ)
[rust-libp2p request-response protocol]: (https://github.com/libp2p/rust-libp2p/tree/master/protocols/request-response)
[go-libp2p-http]: (https://github.com/libp2p/go-libp2p-http)