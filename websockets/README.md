# libp2p WebSockets

| Lifecycle Stage | Maturity                 | Status | Latest Revision |
|-----------------|--------------------------|--------|-----------------|
| 2A              | Candidate Recommendation | Active | r0, 2022-10-12  |

Authors: [@achingbrain]

Interest Group: [@MarcoPolo]

[@achingbrain]: https://github.com/achingbrain
[@MarcoPolo]: https://github.com/MarcoPolo

See the [lifecycle document](../00-framework-01-spec-lifecycle.md) for context about maturity level
and spec status.

## Introduction

[WebSockets](https://websockets.spec.whatwg.org/) are a way for web applications to maintain bidirectional communications with server-side processes.

All major browsers have shipped WebSocket support and the implementations are both robust and well understood.

A WebSocket request starts as a regular HTTP request, which is renegotiated as a WebSocket connection using the [HTTP protocol upgrade mechanism](https://developer.mozilla.org/en-US/docs/Web/HTTP/Protocol_upgrade_mechanism).

## Drawbacks

WebSockets suffer from [head of line blocking](https://en.wikipedia.org/wiki/Head-of-line_blocking) and provide no mechanism for stream multiplexing, encryption or authentication so additional features must be added by the developer or by libp2p.

In practice they only run over TCP so are less effective with [DCuTR Holepunching](../relay/DCUtR.md).

## Certificates

With [some exceptions](https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts#when_is_a_context_considered_secure) browsers will prevent making connections to unencrypted WebSockets when the request is made from a [Secure Context](https://www.w3.org/TR/secure-contexts/).

Given that libp2p makes extensive use of the [SubtleCrypto API](https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto), and that API is only available in Secure Contexts, it's safe to assume that any incoming libp2p connections initiated over WebSockets originate from a Secure Context.

Consequently server-side processes listening for incoming libp2p connections via WebSockets must use TLS certificates that can be verified by the connecting user agent.

These must be obtained externally and configured in the same way as you would for an HTTP server.

The only exception to this is if both server and client are operating exclusively on loopback or localhost addresses such as in a testing or offline environment. Such addresses should not be shared outside of these environments.

## Stream Multiplexing

WebSockets have no built in stream multiplexing. Server-side processes listening for incoming libp2p connections via WebSockets should support [multi-stream select](https://github.com/multiformats/multistream-select) and negotiate an appropriate stream multiplexer such as [yamux](../yamux/README.md).

## Authentication

WebSockets have no built in authentication mechanism. Server-side processes listening for incoming libp2p connections via WebSockets should support [multi-stream select](https://github.com/multiformats/multistream-select) and negotiate an appropriate authentication mechanism such as [noise](../noise/README.md).

## Encryption

Server-side processes listening on WebSocket addresses should use TLS certificates to secure transmitted data at the transport level.

This does not provide any assurance that the remote peer possesses the private key that corresponds to their public key, so an additional handshake is necessary.

During connection establishment over WebSockets, before the connection is made available to the rest of the application, if all of the following criteria are met:

1. `noise` is negotiated as the connection encryption protocol
2. An initial handshake is performed with the `handshake_only` boolean extension set to true
3. The transport layer is secured by TLS

Then all subsequent data is sent without encrypting it at the libp2p level, instead relying on TLS encryption at the transport layer.

If any of the above is not true, all data is encrypted with the negotiated connection encryption method before sending.

This prevents double-encryption but only when both ends opt-in to ensure backwards compatibility with existing deployments.

### MITM mitigation

The TLS certificate used should be signed by a trusted certificate authority, and the host name should correspond to the common name contained within the certificate.

This requires trusting the certificate authority to issue correct certificates, but is necessary due to limitations of certain user agents, namely web browsers which do not allow use of self-signed certificates that could be otherwise be verified via preshared certificate fingerprints.

## Addressing

A WebSocket address contains `/ws`, `/tls/ws` or `/wss` and runs over TCP. If a TCP port is omitted, a secure WebSocket (e.g. `/tls/ws` or `/wss` is assumed to run on TCP port 443), an insecure WebSocket is assumed to run on TCP port 80 similar to HTTP addresses.

Examples:

* `/ip4/192.0.2.0/tcp/1234/ws` (an insecure address with a TCP port)
* `/ip4/192.0.2.0/tcp/1234/tls/ws` (a secure address with a TCP port)
* `/ip4/192.0.2.0/ws` (an insecure address that defaults to TCP port 80)
* `/ip4/192.0.2.0/tls/ws` (a secure address that defaults to TCP port 443)
* `/ip4/192.0.2.0/wss` (`/tls` may be omitted when using `/wss`)
* `/dns/example.com/wss` (a DNS address)
* `/dns/example.com/wss/http-path/path%2Fto%2Fendpoint` (an address with a path)
