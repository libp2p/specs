# Peer ID Authentication over HTTP

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r0, 2023-01-23  |

Authors: [@MarcoPolo]

Interest Group: Same as [HTTP](README.md)

## Introduction

This spec defines one way of authenticating Peer IDs over HTTP using a
challenge-response scheme.

## Mutual Client and Server Peer ID Authentication

1. The server initiates the authentication by responding to a request that must
   be authenticated with the response header `WWW-Authenticate: Libp2p-Challenge
   challenge="<base64-encoded-challenge>, Libp2p-Challenge-Server-Only"`. The
   challenge MUST be randomly generated from server for sole purpose of
   authenticating the client. The server SHOULD store the challenge temporarily
   until the authentication is done. The challenge SHOULD be at least 32 bytes.
1. The client sends a request and sets the `Authorization`
   [header](https://www.rfc-editor.org/rfc/rfc9110.html#section-11.6.2) header
   to the following:
   ```
   Libp2p-Challenge peer-id="<encoded-peer-id-bytes>",client-challenge="<base64-encoded-client-challenge>",sig="<base64-signature-bytes>"
   ```
   * The peer-id is encoded per the [peer-ids spec](../peer-ids/peer-ids.md).
   * The signature is over the concatenated result of:
   ```
     <varint-length> + "origin=" + server-name + 
     <varint-length> + "client-challenge=" + base64-encoded-client-chosen-client-challenge + 
     <varint-length> + "challenge=" + base64-encoded-challenge
   ```
   * The client chosen client-challenge MUST be randomly generated.
   * The client chosen client-challenge SHOULD be at least 32 bytes.
   * The client MUST use the same server-name as what is used for the TLS
     session.
1. The server MUST verify the signature using the server name used in the TLS
   session. The server MUST return 401 Unauthorized if the server fails to
   validate the signature.
1. If the signature is valid, the server has authenticated the client's peer id
   and MAY fulfill the request according to application logic. If the request is
   fulfilled, the server sets the `Authentication-Info` response header to the
   following:
    ```
    Libp2p-Challenge peer-id="<encoded-peer-id-bytes>",sig="<base64-signature-bytes>"
    ```
   * The signature is over the concatenated result of:
        ```
        <varint-length> + "origin=" + server-name + 
        <varint-length> + "client-challenge=" + base64-encoded-client-chosen-client-challenge + 
        <varint-length> + "client=" + <encoded-client-peer-id-bytes>
        ```
1. The client can then authenticate the server with the the signature from
   `Authentication-info`.

## Server Authentication

Clients may wish to only authenticate the server's peer ID, but not themselves.
For example, a short lived client may want to get a block from a specific peer.

The protocol to do so is as follows:

1. The client should set the request header `Authorization` to
   `Libp2p-Challenge-Server-Only <base64-encoded-client-chosen-client-challenge>`.
1. The server should response to the request and set `Authentication-Info`
   response header to the following:
    ```
    Libp2p-Challenge-Server-Only peer-id="<encoded-peer-id-bytes>",sig="<base64-signature-bytes>"
    ```
   * The signature is over the concatenated result of:
        ```
        <varint-length> + "origin=" + server-name + 
        <varint-length> + "client-challenge=" + base64-encoded-client-chosen-client-challenge
        ```
1. The client can now authenticate the server.

## Authentication Endpoint

Because the client needs to make a request to authenticate the server, and the
client may not want to make the real request before authenticating the server,
the server MAY provide an authentication endpoint. This authentication endpoint
is like any other application protocol, and it shows up in `.well-known/libp2p`,
but it only does the authentication flow. It doesn’t send any other data besides
what is defined in the above authentication flows. The protocol id for the
authentication endpoint is `/http-peer-id-auth/1.0.0`.


## Considerations for Implementations

* Implementations SHOULD limit the maximum length of any variable length field.

## Note on web PKI

Protection against man-in-the-middle (mitm) type attacks is through web PKI. If
the client is in an environment where web PKI can not be fully trusted (e.g. an
enterprise network with a custom enterprise root CA installed on the client),
then this authentication scheme can not protect the client from a mitm attack.
