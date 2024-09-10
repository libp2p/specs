# Error Codes

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r0, 2023-01-23  |

Authors: [@sukunrt]

Interest Group: [@marcopolo], [@achingbrain]

[@MarcoPolo]: https://github.com/MarcoPolo
[@achingbrain]: https://github.com/achingbrain

## Introduction

When closing a connection or resetting a stream, it's useful to provide the peer with a code that explains the reason for the closure. This enables the peer to better respond to the abrupt closures. For instance, it can implement a backoff strategy to retry _only_ when it receives a `RATE_LIMITED` error code. An error code doesn't always indicate an error condition. For example, a connection may be closed because a connection to the same peer over a better transport is available. 

## Semantics
Error codes are unsigned 32-bit integers. The range 0 to 10000 is reserved for
libp2p errors. Application specific errors can be defined by protocols from
integers outside of this range. Implementations supporting error codes MUST
provide the error code provided by the other end to the application.

Error codes provide a best effort guarantee that the error will be propagated to
the application layer. This provides backwards compatibility with older nodes,
allows smaller implementations, and using transports that don't provide a
mechanism to provide an error code. For example, Yamux has no equivalent of
QUIC's [STOP_SENDING](https://www.rfc-editor.org/rfc/rfc9000.html#section-3.5-4)
frame that would tell the peer that the node has stopped reading. So there's no
way of signaling an error while closing the read end of the stream on a yamux
connection.

### Connection Close and Stream Reset Error Codes
Error codes are defined separately for Connection Close and Stream Reset. Stream
Reset errors are from the range 0 to 5000 and Connection Close errors are from
the range 5001 to 10000. Having separate errors for Connection Close and stream
reset requires some overlap between the error code definitions but provides more
information to the receiver. Receiving a `Bad Request: Connection Closed` error
on reading from a stream also tells the receiver that no more streams can be
started on the same connection. Implementations MUST provide the Connection
Close error code on streams that are reset as a result of remote closing the
connection. 

For stream resets, when the underlying transport supports it, implementations
SHOULD allow sending an error code on both closing the read side of the stream, and resetting the write side of the stream. 

## Libp2p Error Codes
TODO!

## Wire Encoding
Different transports will encode the 32-bit error code differently. 
        
### QUIC
QUIC provides the ability to send an error on closing the read end of the
stream, resetting the write end of the stream and on closing the connection. 

For stream resets, the error code MUST be sent on the `RESET_STREAM` or the
`STOP_SENDING` frame using the `Application Protocol Error Code` field as per
the frame definitions in the
[RFC](https://www.rfc-editor.org/rfc/rfc9000.html#name-reset_stream-frames).

For Connection Close, the error code MUST be sent on the CONNECTION_CLOSE frame
using the Error Code field as defined in the
[RFC](https://www.rfc-editor.org/rfc/rfc9000.html#section-19.19-6.2.1).

### Yamux
Yamux has no `STOP_SENDING` frame, so there's no way to signal an error on
closing the read side of the stream.

For Connection Close, the 32-bit Length field is interpreted as the error
code.

For Stream Resets, the error code is sent in the `Window Update` frame, with the 32-bit Length field interpreted as the error code. See [yamux spec
extension](https://github.com/libp2p/specs/pull/622).

Note: On TCP connections with `SO_LINGER` set to 0, the Connection Close error code may not be delivered.  

### WebRTC
There is no way to provide any information on closing a peer connection in WebRTC. Providing error codes on Connection Close will be taken up in the future. 

For Stream Resets, the error code can be sent in the `errorCode` field of the WebRTC message with `flag` set to `RESET_STREAM` .

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
