# libp2p + HTTP: the spec

| Lifecycle Stage | Maturity                 | Status | Latest Revision |
|-----------------|--------------------------|--------|-----------------|
| 1A              | Working Draft            | Active | r0, 2023-01-23  |

Authors: [@marten-seemann]

Interest Group: [@MarcoPolo]

[@marten-seemann]: https://github.com/marten-seemann
[@MarcoPolo]: https://github.com/MarcoPolo

## Introduction

This document defines how libp2p nodes can offer a HTTP endpoint next to (or instead of) their full libp2p node. Services can be offered both via traditional libp2p protocols and via HTTP, allowing a wide variety of nodes to access these services. Crucially, this for the first time, allows browsers to access libp2p services without spinning up a Web{Socket, Transport, RTC} connection first. It also allows interacting with libp2p services from environments where plain HTTP is the only option, e.g. curl from the command line, and certain cloud edge workers and lambdas.

At the same time, nodes that are already connected via a libp2p connection, will be able to (re)use this connection to issue the same kind of requests, without dialing a dedicated HTTP connection.

Any protocol that follows request-response semantics can easily be mapped onto HTTP (mapping protocols that don’t follow a request-response flow can be more challenging). Protocols are encouraged to follow best practices for building REST APIs. Once a mapping has been defined, a single implementation can be used to serve both traditional libp2p as well as libp2p-HTTP clients.

## Addressing

Nodes may advertise HTTP multiaddresses to signal support for libp2p over HTTP. An address might look like this: `/ip4/1.2.3.4/tcp/443/tls/sni/example.com/http/p2p/<peer id>` (for HTTP/1.1 and HTTP/2), or  `/ip4/1.2.3.4/udp/443/quic/sni/example.com/http/p2p/<peer id>` (for HTTP/3).

Nodes MUST use HTTPS (i.e. they MUST NOT use unencrypted HTTP). It is RECOMMENDED to use HTTP/2 and HTTP/3, but the protocols also work over HTTP/1.1.

Note that the peer ID in this address is 1. optional and 2. advisory and not (necessarily) verified during the HTTP handshake (depending on the HTTP client). If and when desired, clients can cryptographically verify the peer ID once the HTTP connection has been established, see [Authentication] for details on peer authentication.

Nodes can also link to a specific resource directly, similar to how a URL includes a path. This will require us to resolve [https://github.com/multiformats/multiaddr/issues/63](https://github.com/multiformats/multiaddr/issues/63) first. For example, the URL of a specific CID might be: `/ip4/1.2.3.4/tcp/443/tls/sni/example.com/http/<my data transfer protocol>/{/path/to/<cid>}`.

## Namespace

libp2p does not squat the global namespace. By convention, all libp2p services are located at a well-known URL: `http://example.com/.well-known/libp2p/<service name>/<path (optional)>`.

Putting the service name into the URL allows for future extensibility. It is easy to define new protocols, and the replace existing protocols by newer versions.

Applications MAY expose services under different URIs. For example, an application might decide to generate nicer-looking (and probably more SEO-friendly) URLs, and map paths under `[https://example.com/dht/](https://example.com/dht/)` to `https://example.com/.well-known/libp2p/kad-dht-v1/`. 

### Service Names

Traditionally, libp2p protocols have used path-like protocol identifiers, e.g. `/libp2p/autonat/1.0.0`. Due to the use of `/`s, this doesn’t work well with the naming convention defined above.

Protocols that wish to use the libp2p request-response mechanism MUST define a service name that is a valid URI component (according to RFC 8820).

In practice, this isn’t expected cause too much friction, since current libp2p protocols were not designed to use the request-reponse mechanism, and will need to make arrangements to support it anyway (e.g. define how requests and responses are serialized).

### Privacy Properties

This leads to some very desirable properties:

1. It is possible to run libp2p alongside a normal HTTP web service, i.e. on the same domain and port, without having to worry about collisions. 
    1. As an on-path observer only sees SNI and ALPN, this effectively hides the fact that a client is establishing a connection in order to speak libp2p.
2. Since authentication is flexible (see below), this enables servers to
    1. require authentication to (some) paths below `.well-known/libp2p`, and to enforce ACLs
    2. stealth mode: return 404 for paths below `.well-known/libp2p`, *unless* the client has already authenticated itself, thereby hiding the fact that it runs a libp2p server, even if probed explicitly

## Certificates

libp2p doesn’t prescribe how nodes obtain the TLS certificate to secure the HTTPS connection. Since browsers are expected to connect to the node, the certificate’s trust chain must end in the browser’s trust store.

This is somewhat tricky in a p2p context, as nodes might not have a (sub)domain, which for many CAs is a requirement to obtain a certificate. Specifically, Let’s Encrypt doesn’t support IP certificates at the moment. ZeroSSL does, however, this requires setting up a (free) account.

To speed of server authentication, a node MAY include the libp2p TLS extension in its certificate. Note that this is currently not possible when using Let’s Encrypt, since the libp2p TLS extension is not whitelisted by LE. Not every HTTP client will have access to the TLS certificate (for example, browsers usually don’t expose an API for that), but if an HTTP client does, it SHOULD use that information.

## Authentication

Traditionally, libp2p was built on the assumption that both peers authenticate each other during the libp2p handshake. libp2p+HTTP acknowledges that this isn’t always possible, or even desirable, and that different use cases call for different authentication modes. For example, a server might offer a certain set of services to any client, like a HTTP webserver does.

### Server Authentication

Since HTTP requests are independent from each other (they are not bound to a single connection, and when using HTTP/1.1, will actually use different connections), the server needs to authenticate itself on every single request.

As browsers don’t expose an API to access details of the TLS certificate used, nor allow any access to the (an exporter to) the TLS master secret, server authentication is a bit more contrived than one might initially expect.

To request the server to authenticate, the client sets the `libp2p-server-auth` HTTP header to a randomly generated ASCII string of at least 10 (and a maximum of 100) characters. The server signs the following string using its host key:

```
"libp2p-server-auth:" || the value of the libp2p-server-auth header || "libp2p-server-domain:" || the domain (including subdomains)
```

It then sets the following two HTTP headers on the response:

1. `libp2p-server-pubkey`: its public key (from the libp2p key pair)
2. `libp2p-server-auth-signature`: the signature derived as described above

When requesting server authentication, the client MUST check that these two header fields are present, and MUST check the signature. It MUST NOT process the response if either one of these checks fails

### Client Authentication

When an unauthenticated client tries to access a resource that requires authentication, the server SHOULD use a [401 HTTP status code](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401). The client MAY then authenticate itself using the protocol described below, and then retry the request.

Support for client authentication is an optional feature. It is expected that only a subsection of clients will implement it. For example, browser simply retrieving a few (elements of) web pages from IPFS probably won’t have any need to even generate a libp2p identity in the first place.

The protocol defined here takes 2 RTTs to authenticate the client. It is designed to be stateless on the server side. In the first round-trip, the client obtains a (pseudo-) random value from the server, which it then signs with its host key and sends back to the server, which then issues an authentication token (acting somewhat like a cookie) which can be included on future requests.

The service name is `client-auth`. For the first step, the client sends a GET request to this HTTP endpoint. As described in [server-authentication], the client MUST authenticate the server in this step. The server responds with at least 8 and up to 1024 bytes of pseudorandom data:

```json
{
	"random": <multibase-encoded random bytes>,
  "signature": <multibase-encoded signature>
}
```

In order to keep this exchange stateless, the server SHOULD 1. include the current timestamp or an expiry data and 2. a signature in that data. This allows it to check in step 2 that it actually generated that data.
The client MUST check that the signature obtained in the JSON response is correct and was generated using the same key that the server used to authenticate itself.

The client signs the data received in step 1, and sends a POST request with the following JSON object to the server:

```json
{
  "data": <the random bytes received from the server, multibase encoded>,
  "peer-id": <peer ID, in string reprensentation>,
  "signature": <multibase-encoded signature>
}
```

The server verifies the signature and issues an authentication token. In order to allow stateless operation, at the very minimum, the authentication token SHOULD contain the peer ID. It SHOULD also contain an expiry date and it MAY be bound to the client’s IP address. The token is sent in the response body.

The client uses the auth token on requests that require client authentication, by setting the `libp2p-auth-token` HTTP header.

## Mapping to libp2p Streams

libp2p services whose service is specified as request-response protocols can use a single protocol implementation to make the service available over HTTP as well as on top of libp2p streams.

The libp2p protocol identifier is `/http1.1`. After negotiating this protocol using multistream-select, nodes treat the stream as a HTTP/1.1 stream for a single HTTP request (i.e. nodes MUST NOT use request pipelining).

## Outlook: Interaction with Intermediaries

One of the advantages of running HTTP is that there’s widely deployed caching infrastructure (CDNs). Content-addressed data is infinitely cacheable. Assuming a properly design data transfer protocol, retrieval for CIDs could be cached by the CDN and made available via a POP (geographically) close to the user, dramatically reducing retrieval latencies.

Services SHOULD specify the caching properties (if any), and set the appropriate cache headers (according to RFC 9111).

CDNs can also be used to increase censorship resistance, since the CDN effectively hides the IP address of the origin server. With the upcoming introduction of ECHO (Encrypted ClientHello) in TLS, all that an on-path observer will be able to see is that a client is establishing a connection to a certain CDN, but not to which domain name.

The level of delegation between the origin node and the CDN can be adjusted. In the simplest configuration, the origin node is the only node that holds the libp2p private key, thus requests to the `server-auth` protocol would be forwarded from the CDN to the origin server. In a more advanced configuration, it would be possible to move the private key to a worker on the edge of the CDN, and perform the signing operation there (thereby reducing the request latency for `server-auth` requests).

## FAQ

### Why not gRPC?

This would be the perfect fit, allowing both request-response schemes as well as variations with multiple requests and multiple responses. However, it’s not possible to use gRPC from the browser.

### Why tie ourselves to HTTP when mapping onto libp2p? Can’t we have a more general serialization format?

We could, but rolling our own serialization comes with some costs. First of all, we’d have define how HTTP request and response header, bodies, trailers are serialized onto the wire. Most likely, we’d define a Protobuf for that. Second, once we add more features to that format, they would need to be back-ported to HTTP, so that nodes that only speak HTTP can make use of them as well.

It’s just simpler to commit to HTTP.

### Why not use HTTP/3 for the libp2p mapping?

I’d love to! This would allow us to use HTTP header compression using QPACK, and a binary format instead of a text-based one. However, HTTP/3 requires the peers to exchange HTTP/3 SETTINGS frames first, and it’s not immediately obvious when / how this would be done in libp2p. It’s also not clear how easy it would be to use HTTP/3 in JavaScript.

The good news is that once we’ve come up with a solution for these two problems, it will be rather easy to add support for HTTP/3: nodes will just offer `/http3` in addition (and one day, instead of) `/http1.1`, and nodes that support can hit that endpoint. Nothing in the implementation of the protocols will need to change, since protocols only deal with (deserialized) HTTP requests and responses.

### Can I run QUIC, WebTransport and an HTTP/3 server on the same IP and port?

Yes, once [https://github.com/libp2p/specs/issues/507](https://github.com/libp2p/specs/issues/507) is resolved.
