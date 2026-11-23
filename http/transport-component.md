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
- [HTTP Paths (and other HTTP Semantics)](#http-paths-and-other-http-semantics)
  - [Recommendation on including HTTP semantics in multiaddrs](#recommendation-on-including-http-semantics-in-multiaddrs)

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

- `/dns/example.com/tls/http`
- `/ip4/1.2.3.4/tcp/443/tls/http`
- `/ip6/2001:0db8:85a3:0000:0000:8a2e:0370:7334/tcp/443/tls/http`
- `/ip4/1.2.3.4/udp/50781/quic-v1/http`

Note: When we use `/quic-v1/http` or `/tcp/443/tls/http` (or any other
transport) implementations MUST use the correct HTTP ALPN (e.g. `h3` or `h2`
respectively) and not `libp2p` when using the HTTP transport.

### Recommendation on including HTTP Request semantics in Multiaddrs

In general, it's better to keep the Multiaddrs as a way of addressing an
endpoint and keep the semantics independent of any specific transport. This way
you can use the same semantics among many specific transports.

However, sometimes it's helpful to share a single Multiaddr that contains some
extra application-level data (as opposed to transport data). The recommendation
is to use a new [multicodec in the private
range](https://github.com/multiformats/multicodec#private-use-area) for your
application. Then apply whatever application parameters to the right of your new
multicodec and transport information to the left. E.g.
`<transport>/myapp/<parameters>`
or `/ip4/127.0.0.1/tcp/8080/http/myapp/custom-prefix/foo%2fbar`. Your
application has the flexibility to handle the parameters in any way it wants
(e.g. set HTTP headers, an HTTP path prefix, cookies, etc).

This is a bit cumbersome when you are trying to use multiple transports since
you may end up with many Multiaddrs with different transports but the same
suffix. A potential solution here is to keep them separate. A list of Multiaddrs
for the transports being used, and another Multiaddr for the application-level
data. This is one suggestion, and many other strategies would work as well.
