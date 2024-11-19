# Error Codes

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r0, 2023-01-23  |

Authors: [@sukunrt]

Interest Group: [@marcopolo], [@achingbrain]

[@MarcoPolo]: https://github.com/MarcoPolo
[@achingbrain]: https://github.com/achingbrain

## Introduction

When closing a connection or resetting a stream, it's useful to provide the peer
with a code that explains the reason for the closure. This enables the peer to
better respond to the abrupt closures. For instance, it can implement a backoff
strategy to retry _only_ when it receives a `RATE_LIMITED` error code. An error
code doesn't always indicate an error condition. For example, a node can terminate an idle connection, or close a connection because a connection to the same peer over a better transport is available. In both these cases, it can signal an appropriate error code to the other end. 

## Semantics
Error codes are unsigned 32-bit integers. The range 0 to 10000 is reserved for
libp2p errors. Application specific errors can be defined by protocols from
integers outside of this range. Error Codes can be signaled on Closing a connection or on resetting a Stream.   

From an application perspective, error codes provide a best effort guarantee. On resetting a libp2p stream or closing a connection with an error code, the error code may or may not be delivered to the application on the remote end. The specifics depend on the transport used. For example, WebTransport doesn't support error codes at all, while WebRTC doesn't support Connection Close error codes, but supports Stream Reset error codes. 

### Connection Close and Stream Reset Error Codes
Error codes are defined separately for Connection Close and Stream Reset. The namespace doesn't overlap as it is clear from the context whether the stream was reset by the other end, or it was reset as a result of a connection close. 
Implementations MUST provide the Connection Close error code on streams that are reset as a result of remote closing the connection. 

Libp2p streams are reset unilaterally, calling `Reset` on a stream resets both the read and write end of a stream. For transports, like QUIC, which support cancelling the read and write ends of the stream separately, implementations MAY provide the ability to signal error codes separately on resetting either end. 

## Error Codes Registry
Libp2p connections are shared by multiple applications. The same connection used in the dht may be used for gossip sub, or for any other application. Any of these applications can close the underlying connection on an error, resetting streams used by the other applications. To correctly distinguish which application closed the connection, Connection Close error codes are allocated to applications from a central registry. 

For simplicity, we manage both Connection Close and Stream Reset error codes from a central registry. The libp2p error codes registry is at: https://github.com/libp2p/error-codes/

### Libp2p Reserved Error Codes
Error code 0 signals that no error code was provided. Implementations MUST handle closing a connection with error code 0 as they handle closing a connection with no error code, and resetting a stream with error code 0 as they handle resetting a stream with no error. 

Error codes from 1 to 100 are reserved for transport errors. These are used by the transports to terminate connections on transport errors. 

Error codes from 100 - 10000 are reserved for libp2p. This includes multistream error codes, as it is necessary for libp2p connection establishment over TCP, but not kad-dht or gossip-sub error codes. 

see [Libp2p error codes](./libp2p-error-codes.md) for the libp2p reserved error
codes.

## Transport Specification and Wire Encoding
Different transports will encode the 32-bit error code differently on the wire. They also provide different semantics: Webtransport doesn't define error codes, WebRTC doesn't support Connection Close error codes, Yamux error codes on Connection Close cannot be reliably sent over the wire.  

### QUIC
QUIC provides the ability to send an error on closing the read end of the
stream, resetting the write end of the stream and on closing the connection. 

For stream resets, the error code MUST be sent on `RESET_STREAM` and `STOP_SENDING` frames using the `Application Protocol Error Code` field as per
the frame definitions in the
[RFC](https://www.rfc-editor.org/rfc/rfc9000.html#name-reset_stream-frames).

For Connection Close, the error code MUST be sent on `CONNECTION_CLOSE` frame
using the Error Code field as defined in the
[RFC](https://www.rfc-editor.org/rfc/rfc9000.html#section-19.19-6.2.1).

### Yamux
Yamux streams are reset unilaterally. Receiving a stream frame with `RST` flag set resets both the read and write end of the stream. So, there's no way to separately signal error code on closing the read end of the stream, or resetting the write end of the stream. 

For Connection Close, the 32-bit Length field is interpreted as the error code.

For Stream Resets, the error code is sent in the `Window Update` frame, with the
32-bit Length field interpreted as the error code. See [yamux spec
extension](https://github.com/libp2p/specs/pull/622).

Connection Close error code delivery to the other end depends on the OS TCP implementation and the TCP options used for the socket. In particular, when `SO_LINGER` TCP option is set to 0 and the implementation closes the connection immediately after writing the error code containing frame, the error code may not be delivered.

### WebRTC
There is no way to provide any information on closing a peer connection in
WebRTC. Providing error codes on Connection Close will be taken up in the
future. 

For Stream Resets, the error code can be sent in the `errorCode` field of the
WebRTC message with `flag` set to `RESET_STREAM`.

### WebTransport
Error codes for WebTransport will be introduced when browsers upgrade to draft-9
of the spec. The current WebTransport spec implemented by Chrome and Firefox is
[draft-2 of WebTransport over
HTTP/3](https://www.ietf.org/archive/id/draft-ietf-webtrans-http3-02.html#section-4.3-2).
This version allows for only a 1-byte error code. 1 byte is too restrictive and
as the latest WebTransport draft,
[draft-9](https://www.ietf.org/archive/id/draft-ietf-webtrans-http3-02.html#section-4.3-2)
allows for a 4-byte error code to be sent on stream resets, we will introduce
error codes over WebTransport later.

### Multistream Select
Multistream-Select is used to negotiate Security protocol for TCP connections before a stream muxer has been selected. There's only one error code defined for such cases, `PROTOCOL_NEGOTIATION_FAILED`. To encode this error, send the string `101` prefixed with the length and close the TCP connection.  
