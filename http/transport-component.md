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
HTTP. Intuitively if you can `curl` it with HTTP, then it speaks HTTP.

Most environments will have a way to create an HTTP Client and Server, and the
specific HTTP version used will be opaque. We use the `/http` component at the
end of the multidadr to signal that this server supports an HTTP transport. The
end user agent decides on HTTP version to use, based on the multiaddr prefix,
application, server negotiation, and specific use case. This follows what
existing `http://` URL implementations do.

## Multiaddr representation

The multiaddr of a node with an HTTP transport ends with `/http` and is prefixed
by information that would let an HTTP client know how to reach the server
(remember that multiaddrs are [interpreted right to
left](https://github.com/multiformats/multiaddr#interpreting-multiaddrs)). 

The following are examples of multiaddrs for HTTP transport capable nodes:

* `/dns/example.com/tls/http`
* `/ip4/1.2.3.4/tcp/443/tls/http`
* `/ip6/2001:0db8:85a3:0000:0000:8a2e:0370:7334/tcp/443/tls/http`
* `/ip4/1.2.3.4/udp/50781/tls/http`


## HTTP Paths

It may be tempting to add an HTTP path to end of the multiaddr to specify some
information about a user protocol. However the `/http` component is not a user
protocol, and it doesn't accept any parameters. It only signals that a node is
capable of an HTTP transport.

The HTTP Path exists in the user protocol level. HTTP Semantics are transport-agnostic, and defined by [RFC 9110](https://httpwg.org/specs/rfc9110.html). You can
use these semantics on any transport including, but not limited to, the HTTP
transports like [HTTP/1.1](https://www.rfc-editor.org/info/rfc7235), [HTTP/2](https://www.rfc-editor.org/info/rfc9113), or [HTTP/3](https://www.rfc-editor.org/info/rfc9114).

For example, say you want to signal that a node supports the [IPFS trustless
HTTP gateway] protocol. It may be tempting to use the following multiaddr to
signal that:

```
/ip4/127.0.0.1/tcp/8080/http/httppath/ipfs
```

But `/http` is a transport and it doesn't accept any parameters. It would be the
same as if we used the following multiaddr:

```
/ip4/127.0.0.1/udp/1234/quic-v1/httppath/ipfs
```

What does `httppath/` mean here? `/quic-v1` is a transport and doesn't accept
parameters. Who handles the input from `/httppath`?

What we're really trying to do here is to highlight that the node that can be
found at those Multiaddrs supports the [IPFS trustless HTTP gateway] protocol.
That can and should be done some other way such as
[identify](https://github.com/libp2p/specs/tree/master/identify) or soon the
[`.well-known/libp2p`](https://github.com/libp2p/specs/pull/529) HTTP endpoint
or some other custom application logic.

If having this information on the multiaddr is desired and you are willing to
make the tradeoff of potentially multiplying the number of multiaddrs you have
by the number of protocols you want to signal, you could use a multicodec from
the [private use
area](https://github.com/multiformats/multicodec#private-use-area) and append
this to your multiaddr. The result would be something like:

```
myProtocol = 0x300000

/ip4/127.0.0.1/tcp/8080/http/myProtocol
/ip4/127.0.0.1/udp/1234/quic-v1/myProtocol
```

Note that the problem appears when we want to add another protocol here:
```
myProtocol = 0x300000
anotherProtocol = 0x300001

/ip4/127.0.0.1/tcp/8080/http/myProtocol
/ip4/127.0.0.1/udp/1234/quic-v1/myProtocol
/ip4/127.0.0.1/tcp/8080/http/anotherProtocol
/ip4/127.0.0.1/udp/1234/quic-v1/anotherProtocol
```

[IPFS trustless HTTP gateway]: (https://specs.ipfs.tech/http-gateways/trustless-gateway/)
