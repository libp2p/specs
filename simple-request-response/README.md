# A simple request/response abstraction

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r0, 2023-07-14  |

Authors: [@MarcoPolo]

todo: others welcome to join
Interest Group: [@mxinden] [@marten-seemann]

[@marten-seemann]: https://github.com/marten-seemann
[@MarcoPolo]: https://github.com/MarcoPolo
[@mxinden]: https://github.com/mxinden

## Introduction

Many application protocols map well to request/response semantics where a peer
makes a request to another peer, and receives a response back. For example,
requesting a file from a peer and getting the file back. In contrast to
request/response, stream semantics allow two peers to continously send data
back and forth with no specific ordering. Both styles have their uses. This
document focuses on _one_ way of implementing request/response semantics and
how to map it to stream based transports and an HTTP transport.

## Goals of this document

A goal of this document is to define _a_ simple way to write request/response
style application protocols that can make use of all libp2p transports
seamlessly (all stream transports and the HTTP transport). This is only one way
of writing request/response style protocols, and users may choose to not use it.

Another goal is to be backwards compatible with existing application protocols
that follow these semantics to make upgrading them easier so that they may take
advantage of the new HTTP transport without sacrificing backwards compatibility.

The final goal is to define something simple such that it's easy to follow,
implement, and use.

## The abstraction

This abstraction takes in a blob from the requesting peer (aka client) that
represents the request and delivers the blob to the responding peer (aka
server). The server responds with a blob that respresents the response. This
abstraction is agnostic to what the blobs are or how they are encoded. That's up
to the application protocol to decide.

## How to run on top of a libp2p stream

Each request and response should happen in a single stream. There MUST NOT be
pipelining. After sending a request, the client SHOULD close its write side
(signalling EOF to the peer). After handling the response, the client SHOULD
close the stream. After sending the response the server SHOULD close the stream
side (signalling EOF to the peer as well as signalling no future writes will be accepted.).

## How to run on top of an HTTP transport

The client's request is placed in the body of an HTTP POST request. The server
places its response in the body of the HTTP response. Headers are unused by the
application protocol (but may be used by the libp2p implementation to provide
authentication). The HTTP path used is defined by the server's
`.well-known/libp2p` HTTP resource (see the [HTTP](../http/README.md) spec for
more details).


## Prior Art

This spec is inspired by existing work to use request response protocols on top
of libp2p streams including, but not limited to:
- go-libp2p-kad-dht
- Identify Push
- AutoNATV2

This is also inspired by rust-libp2p's [Request/Response
crate](https://docs.rs/libp2p-request-response/0.25.0/libp2p_request_response/).

