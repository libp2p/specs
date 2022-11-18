# libp2p + HTTP: Authentication

Traditionally, libp2p peers authenticate each other during the handshake, proving to each other that they posses the private key associated with their peer ID, which in turn is derived from the corresponding public key.

## Client Authentication

Depending on the nature of the client, authenticating the client might or might not make sense. If the client is a long-running (probably standalone) node, authentication makes a lot of sense, since this allows the client to earn reputation (e.g. in Gossipsub).
For browser nodes, identities are commonly not longer-lived than the browser tab. To make matters worse, due to the lack of suitable crypto APIs, the private key is held in JS, and is therefore susceptible to infiltration by the website.

When considering the browser / CDN use case, it would be advantageous if libp2p clients could skip the generation of an ephemeral libp2p identity, and instead could interact with (a subset of) libp2p protocols in an unauthenticated manner.

**Conclusion**: libp2p protocols need to specify if they require client authentication. In particular, request-response based data transfer protocols can benefit from not authenticating the client.

### On Demand Client Authentication

While many libp2p protocols won’t need client authentication, servers can require clients to authenticate for certain requests and protocols. Typically, a 401 status code (Unauthorized) signals to the client that authenticating might allow access to a resource.

The client proves ownership of its private key by signing a value provided by the server. The server then issues an authentication token, which the client then sets as a header field on subsequent requests to the server. To allow the server to operate statelessly, it MAY encode the client’s peer ID into the authentication token.

TODO: specify endpoints and what exactly to sign. Or maybe there’s prior art we can reuse?

## Server Authentication

While client authentication seems to be dispensible in many cases of interest, things are a little bit more complicated when it comes to server authentication: Even when the server’s peer ID in itself is not of interest (e.g. because there’s no reputation score attached to it), verifying the peer ID during the handshake guarantees that no MITM was performed on the connection.

On the other hand, since a lot of our use cases deal with content-addresses (i.e. self-certifying) data, we often don’t really care who we get the data from (we still care that there’s no MITM who’s reading all of our requests, as this would be a privacy issue).

Depending on the situation, we can use different means to verify that the connection was not MITM’ed:
1. The client is a standalone node: The server can encode its peer ID into the certificate, as we already do for the normal libp2p TLS handshake.
2. The client is a browser node: In this case, establishing a HTTPS connection is only possible if the server possesses a CA-signed certificate for the domain / IP the client is connecting to. In that case, verifying the certificate chain is sufficient. Note that this doesn’t allow the client to learn the server’s peer ID.

### On-Demand Server Authentication

In order to learn and verify the server’s peer ID, the client MAY use a challenge-response protocol. The client issues a POST request to a predefined HTTP endpoint, and the server signs this value (concatenated to a const string) with its private key. It then transfers its public key and the signature to the client.

TODO: this is really straightforward, but we need to specify how exactly this works

### Using the Subdomain to encode a signature

In order to avoid the 1 RTT cost spent on on-demand server authentication, the server could sign the concatenation of a const string with its domain name, and use that signature as the subdomain. This would allow the client to verify the peer ID prior to connecting to the server.

Encoding: An ed25519 signature is 64 bytes long, and therefore doesn’t fit into a (single) subdomain (which is limited to 63 octets). The signature would therefore be split into two part, and the resulting domain name would be `sig-part1.sig-part2.example.com`.

Open questions:
* Does this need to expire at some point? Rolling out an eternally valid signature seems dangerous.
* Is this optimization worth it, given that on-demand verification only takes a single RTT?
