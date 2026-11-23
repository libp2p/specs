# A request/response interface for application protocols on any transport

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r0, 2023-07-14  |

Authors: [@MarcoPolo]

Interest Group: [@mxinden] [@marten-seemann] [@thomaseizinger]

[@marten-seemann]: https://github.com/marten-seemann
[@MarcoPolo]: https://github.com/MarcoPolo
[@mxinden]: https://github.com/mxinden
[@thomaseizinger]: https://github.com/thomaseizinger

## Introduction

Many application protocols map well to request/response semantics where a peer
makes a request to another peer, and receives a response back. For example,
requesting a file from a peer and getting the file back. In contrast to
request/response, stream semantics allow two peers to continously send data
back and forth with no specific ordering. Both styles have their uses. This
document focuses on _one_ way of implementing request/response semantics and
how to map it to stream based transports and an HTTP transport.

## The interface

At its core, request-response means:
- taking _one_ blob from the requesting peer (aka the client)
- delivering this blob to the responding peer (aka the server)
- taking _one_ blob from the responding peer
- delivering this blob to the requesting peer

The defining characteristics are:

- Each party can only send one message
- The interaction is linear in time (the response can only be initiated after the request has been received)

This is in contrast to for example streaming protocols where the responding peer may send any number of messages or event/notification-based protocols where a message may be received without a prior request.

What the blobs are and how they are encoded is subject to the application
protocol and not defined in this interface.

A rough suggestion for implementors to follow is provide something like:
```
async fn handleRequest(request) -> response
```

where the request/response may be read incrementally and asynchronously and the
request/response may also be sent incrementally and asynchronously. This is
similar to how many implementations do HTTP request/response:

- JS [Fetch](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API) api returns a [`Response`](https://fetch.spec.whatwg.org/#response) object as soon as the server returns headers. The
  body of both requests and responses are `ReadableStreams`.
- Go's [http.Request](https://pkg.go.dev/net/http@go1.20.5#Request) and [http.Response](https://pkg.go.dev/net/http@go1.20.5#Response) bodies are both [`io.ReadCloser`](https://pkg.go.dev/io@go1.20.5#ReadCloser) types.
- The Rust [hyper](https://docs.rs/hyper) crate has a similar [`HTTPBody`](https://docs.rs/hyper/latest/hyper/body/trait.HttpBody.html) that reads request/response data
  incrementally and asynchronously.

## Goals of this document

The primary goal of this document is to define an interface that application
protocols can build on and transports can fulfill.

Another goal is to be backwards compatible with existing application protocols
that follow these semantics to make upgrading them easier so that they may take
advantage of the new HTTP transport without sacrificing backwards compatibility.

The final goal is to define something simple such that it's easy to follow,
implement, and use.

## How to map to a libp2p stream

Each request and response should happen in a single stream. There SHOULD NOT be
pipelining. After sending a request, the client SHOULD close its write side
(signalling EOF to the peer). After handling the response, the client SHOULD
close the stream. After sending the response the server SHOULD close the stream
side (signalling EOF to the peer as well as signalling no future writes will be accepted.).

## How to map to an HTTP transport

The client's request is placed in the body of an HTTP POST request. The server
places its response in the body of the HTTP response. Headers are unused by the
application protocol (but may be used by the libp2p implementation to provide
authentication). The HTTP path used for the application protocol is defined by
the server's `.well-known/libp2p` HTTP resource (see the
[HTTP](../http/README.md) spec for more details).

## Considerations for applications

- Applications should define a reasonable maximum amount of expected data, and
  limit the amount of data they receive at any time. For example, Kademlia may
  limit the maximum size of a request to
  [16KiB](https://github.com/libp2p/rust-libp2p/blob/master/protocols/kad/src/protocol.rs#L48)
  or
  [4MiB](https://github.com/libp2p/go-libp2p/blob/master/core/network/network.go#L23).

## Prior Art

This spec is inspired by existing work to use request response protocols on top
of libp2p streams including, but not limited to:
- go-libp2p-kad-dht
- Identify Push
- AutoNATV2

This is also inspired by rust-libp2p's [Request/Response
crate](https://docs.rs/libp2p-request-response/0.25.0/libp2p_request_response/).

