# Peer ID Authentication over HTTP

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r0, 2023-01-23  |

Authors: [@MarcoPolo]

[@MarcoPolo]: https://github.com/MarcoPolo

Interest Group: Same as [HTTP](README.md)

## Introduction

This spec defines one way of authenticating Peer IDs over HTTP using a
challenge-response scheme. The authentication scheme is called `Libp2p-PeerID``

## Mutual Client and Server Peer ID Authentication

1. The server initiates the authentication by responding to a request that must
   be authenticated with the response header `WWW-Authenticate: Libp2p-PeerID
   challenge-client="<base64-encoded-challenge>`. The challenge MUST be
   indistinguishable from random data. The Server MAY randomly generate this
   data, or MAY use an server-encrypted value. If using random data the
   server SHOULD store the challenge temporarily until the authentication is
   done. The challenge SHOULD be at least 32 bytes.

1. The client sends a request and sets the `Authorization`
   [header](https://www.rfc-editor.org/rfc/rfc9110.html#section-11.6.2) header
   to the following:
   ```
   Libp2p-PeerID peer-id="<encoded-peer-id-bytes>",[challenge-server="<base64-encoded-challenge-server>",]sig="<base64-signature-bytes>"]
   ```

   * The `challenge-server` parameter is optional. The client should set it if
     the client wants to authenticate the server.
   * The peer-id is encoded per the [peer-ids spec](../peer-ids/peer-ids.md).
   * The signature is over the concatenated result of:
   ```
     <varint-length> + "origin=" + server-name + 
     [<varint-length> + "challenge-server=" + base64-encoded-client-chosen-challenge-server + ]
     <varint-length> + "challenge-client=" + base64-encoded-challenge
   ```
   * Strings are UTF-8 encoded.
   * If the challenge server was omitted in the `Authorization` header it MUST
     be omitted in the signature.
   * If provided, the client-chosen `challenge-server`` MUST be randomly generated.
   * The client-chosen `challenge-server` SHOULD be at least 32 bytes.
   * The client MUST use the same server-name as what is used for the TLS
     session.
   * If the client _only_ wants to authenticate the server and the server does
     not need to authenticate the client, the client can omit the
     `challenge-client` from the parameters and signature on its initial request
     (since it did not receive a `challenge-client`). If a resource requires
     client authentication, the server MUST return `401 Unauthorized` if a
     client attempts to authenticate without a `challenge-client`.
   * Example on building the message to sign:
    ```
    origin=example.com
    client-challenge=qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqo=
    challenge=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
    ```

    Message To Sign in hex with comments
    ```
    12 // (18 bytes)
    6f726967696e3d6578616d706c652e636f6d // (origin=example.com)

    3d // (61 bytes)
    636c69656e742d6368616c6c656e67653d7171717171717171717171717171717171717171717171717171717171717171717171717171717171716f3d // (client-challenge=qq...o=)

    36 // (54 bytes)
    6368616c6c656e67653d414141414141414141414141414141414141414141414141414141414141414141414141414141414141413d // (challenge=AA...A=)
    ```

    All together:
    ```
    Message To Sign in hex:
    126f726967696e3d6578616d706c652e636f6d3d636c69656e742d6368616c6c656e67653d7171717171717171717171717171717171717171717171717171717171717171717171717171717171716f3d366368616c6c656e67653d414141414141414141414141414141414141414141414141414141414141414141414141414141414141413d
    ```
2. The server MUST verify the signature using the server name used in the TLS
   session. The server MUST return 401 Unauthorized if the server fails to
   validate the signature.
3. If the signature is valid, the server has authenticated the client's peer id
   and MAY fulfill the request according to application logic. If the request is
   fulfilled, the server sets the `Authentication-Info` response header to the
   following:
    ```
    Libp2p-PeerID peer-id="<encoded-peer-id-bytes>",sig="<base64-signature-bytes>"
    ```
   * The signature is over the concatenated result of:
        ```
        <varint-length> + "origin=" + server-name + 
        [<varint-length> + "challenge-server=" + base64-encoded-client-chosen-challenge-server + ]
        <varint-length> + "client=" + <encoded-client-peer-id-bytes>
        ```
    * Strings are UTF-8 encoded.
    * Optionally, the server MAY include a [Bearer
      token](https://datatracker.ietf.org/doc/html/rfc6750) in the
      `Authentication-Info` response header. This allows clients to avoid a
      future iteration of this authentication protocol. If clients see a bearer
      token, they SHOULD store it for future use. For example,  an
      `Authentication-Info` header with a bearer token would look like:
      ```
      Libp2p-PeerID peer-id="<encoded-peer-id-bytes>",sig="<base64-signature-bytes>",bearer-token="<token>".
      ```
4. The client can then authenticate the server with the the signature from
   `Authentication-info`.

## Authentication Endpoint

Because the client needs to make a request to authenticate the server, and the
client may not want to make the real request before authenticating the server,
the server MAY provide an authentication endpoint. This authentication endpoint
is like any other application protocol, and it shows up in `.well-known/libp2p`,
but it only does the authentication flow. The client and server SHOULD NOT send
any data besides what is defined in the above authentication flows. The protocol
id for the authentication endpoint is `/http-peer-id-auth/1.0.0`.


## Considerations for Implementations

* Implementations MUST only authenticate over a secured connection (i.e. TLS).
* Implementations SHOULD limit the maximum length of any variable length field.

## Note on web PKI

Protection against man-in-the-middle (mitm) type attacks is through web PKI. If
the client is in an environment where web PKI can not be fully trusted (e.g. an
enterprise network with a custom enterprise root CA installed on the client),
then this authentication scheme can not protect the client from a mitm attack.
