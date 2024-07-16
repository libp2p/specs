# Error Codes

## Introduction
In the event that a node detects violation of a protocol or is unable to
complete the necessary steps required for the protocol, it's useful to provide a
reason for disconnection to the other end. This error code can be sent on both
Connection Close and Stream Reset. Its purpose is similar to http response
status. A server, on receiving an invalid request can reset the stream providing
a `BAD_REQUEST` error code, when it's busy handling too many requests can
provide a `RATE_LIMITED` error code, etc. An error code doesn't always indicate
an error condition. For example, a connection may be closed prematurely because
a connection to the same peer on a better transport is available. 

## Semantics
Error codes are unsigned 32bit integers. The range 0 to 10000 is reserved for
libp2p errors. Application specific errors can be defined by protocols from
integers outside of this range. Implementations supporting error codes MUST
provide the error code provided by the other end to the application.

Error codes provide a best effort guarantee that the error will be propogated to
the applciation layer. This provides backwards compatibility with older nodes,
allows smaller implementations and using transports that don't provide a
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
SHOULD allow sending an error code on both closing the read side of the stream
and resetting the write side of the stream. 

## Libp2p Error Codes
TODO!

## Wire Encoding
Different transports will encode the 32bit error code differently. 
        
### QUIC
QUIC provides the ability to send an error on closing the read end of the
stream, reseting the write end of the stream and on closing the connection. 

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

For Connection Close, the 32bit Length field is to be interpreted as the error
code. The error code MUST be sent as an  Big Endian unsigned 32 bit integer. 

For Stream Resets, the error code is sent as the first 4 bytes of the Data Frame
following the header with RST flag set as defined in the [yamux spec
extension](https://github.com/libp2p/specs/pull/622).

Note: On TCP connections with `SO_LINGER` set to 0, the error code on connection
close may not be delivered.  

### WebRTC
Since WebRTC doesn't provide reliable delivery for frames that are followed by
closing of the underlying data channel, there's no simple way to introduce error
codes in the current implementation. Consider the most common use case of
resetting both read and write sides of the stream and closing the data channel.
The chrome implementation will not deliver the final `RESET_STREAM` msg and
while the go implementation will delivery the `RESET_STREAM` frame and then
close the data channel, there's no guarantee that the chrome implementation will
provide the `RESET_STREAM` msg to the application layer after it receives the
data channel close message. 

### WebTransport
Error codes for webtransport will be introduced when browsers upgrade to draft-9
of the spec. The current webtransport spec implemented by chrome and firefox is
[draft-2 of webtransport over
http3](https://www.ietf.org/archive/id/draft-ietf-webtrans-http3-02.html#section-4.3-2).
This version allows for only a 1 byte error code. 1 byte is too restrictive and
as the latest webtransport draft,
(draft-9)[https://www.ietf.org/archive/id/draft-ietf-webtrans-http3-02.html#section-4.3-2]
allows for a 4 byte error code to be sent on stream resets, we will introduce
error codes over webtransport later.
