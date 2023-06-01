# HTTP Transport Component <!-- omit in toc -->

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r0, 2023-05-31  |

Authors: [@marcopolo]

Interest Group: [@marcopolo], [@mxinden], [@marten-seemann]

[@marcopolo]: https://github.com/marcopolo
[@mxinden]: https://github.com/mxinden
[@marten-seemann]: https://github.com/marten-seemann

## Table of Contents <!-- omit in toc -->
- [Context](#context)
- [What is an HTTP transport](#what-is-an-http-transport)
- [Multiaddr representation](#multiaddr-representation)
- [HTTP Paths](#http-paths)


## Context

This document is only about advertising support for an HTTP transport. It
doesn't make any assertions about how libp2p should interact with that
transport. That will be defined in a future document.

This exists to clarify the role of the `/http` component in Multiaddrs early to
avoid confusion and conflicting interpretations.

## What is an HTTP transport

An HTTP transport is simply a node that can speak some standardized version of
HTTP that is at least HTTP/1.1. Currently that means HTTP/1.1, HTTP/2, and
HTTP/3. Intuitively if you can `curl` it with HTTP, then it speaks HTTP.

Most environments will have a way to create an HTTP Client and Server, and the
specific HTTP version used will be opaque. The client will negotiate (or [learn
about](https://www.rfc-editor.org/rfc/rfc9114.html#section-3.1.1)) the specific HTTP version to use when communicating
with the HTTP server.

For this opaque case, we use the `/http` component at the end of the multidadr.
If a node wants to advertise specific HTTP versions it may advertise a
`/http-1.1`, `/http-2`, or `/h3` instead. Although these components are not
currently [registered](https://github.com/multiformats/multiaddr), this document
claims their use.


## Multiaddr representation

The multiaddr of a node with an HTTP transport ends with `/http` and is prefixed
by information that would let an HTTP client know how to reach the server
(remember that multiaddrs are [interpreted right to
left](https://github.com/multiformats/multiaddr#interpreting-multiaddrs)). 

The following are examples of multiaddrs for HTTP transport capable nodes:

* `/dns/example.com/tls/http`
* `/dns/example.com/https`
* `/ip4/1.2.3.4/tcp/443/https`
* `/ip4/1.2.3.4/tcp/443/tls/http`
* `/ip6/2001:0db8:85a3:0000:0000:8a2e:0370:7334/tcp/443/tls/http`
* `/ip4/1.2.3.4/udp/50781/tls/http` // We can infer this is an HTTP/3 address
* `/ip4/1.2.3.4/udp/50781/quic-v1/http` // Not necessary to specify that the
  HTTP endpoint is on top of QUIC, but it is okay if it does.


## HTTP Paths

It may be tempting to add an HTTP path to end of the multiaddr to specify some
information about a user protocol. However the `/http` component is not a user
protocol, and it doesn't accept any parameters. It only signals that a node is
capable of an HTTP transport.

The HTTP Path exists in the user protocol level. HTTP Semantics are transport-agnostic, and defined by [RFC 9110](https://httpwg.org/specs/rfc9110.html). You can
use these semantics on any transport including, but not limited to, the HTTP
transport.

For example, say you want to fetch a file using the [IPFS trustless HTTP
gateway](https://specs.ipfs.tech/http-gateways/trustless-gateway/). It may be tempting to
use the following URL to reference a file:

```
/ip4/127.0.0.1/tcp/8080/http/httppath/ipfs%2fbafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi
```

But `/http` is a transport and it doesn't accept any parameters. It would be the
same as if we used the following multiaddr:

```
/ip4/127.0.0.1/udp/1234/quic-v1/httppath/ipfs%2fbafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi
```

What does `httppath/` mean here? Does it mean make a `GET` request? How would
you make a `POST` request? What about headers? Does it leave that unspecified
and ask the user to specify that as they would with curl?

We could be more precise here and specify a `/GET` component to the multiaddr
that accepts parameters and describes what user protocol we are trying to do
here.

```
/ip4/127.0.0.1/udp/1234/http/GET/httppath/ipfs%2fbafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi

or

/ip4/127.0.0.1/udp/1234/quic-v1/GET/httppath/ipfs%2fbafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi
```

This is fine since `httppath` passes the path parameter to `GET` which parses
the rest of the multiaddr as the address of the node to connect to and make an
HTTP GET request which can happen over an HTTP transport or any other transport
(e.g. QUIC streams or yamux+noise+tcp).

You may end up with a lot of duplicate information if you have many multiaddrs
since each one will have the same suffix of `GET/httppath/...`. Therefore this
isn't recommended, but may be useful if you just need one multiaddr
with some extra protocol information.

To summarize, HTTP Paths don't make sense appended to an `/http` component, but may make sense
appended to some other custom user protocol component.
