# yamux

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 3A              | Recommendation | Active | r0, 2023-02-17  |

Authors: [@thomaseizinger]

Interest Group: [@marten-seemann], [@wemeetagain], [@ianopolous]

[@thomaseizinger]: https://github.com/thomaseizinger
[@marten-seemann]: https://github.com/marten-seemann
[@wemeetagain]: https://github.com/wemeetagain
[@ianopolous]: https://github.com/ianopolous

See the [lifecycle document][lifecycle-spec] for context about maturity level and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Overview

Yamux is Stream Multiplexer protocol originally specified by [@hashicorp](https://github.com/hashicorp).
The specification lives here: https://github.com/hashicorp/yamux/blob/master/spec.md

The below sections are a verbatim copy (modulo formatting changes) of the spec at the time this document was created.
This allows us to preserve the specification in case the linked document is ever removed or edited.

## Specification

The protocol string of yamux for `multistream-select` is: `/yamux/1.0.0`. 

### Framing

Yamux uses a streaming connection underneath, but imposes a message framing so that it can be shared between many logical streams.
Each frame contains a header like:

* Version (8 bits)
* Type (8 bits)
* Flags (16 bits)
* StreamID (32 bits)
* Length (32 bits)

This means that each header has a 12 byte overhead.
All fields are encoded in network order (big endian).
Each field is described below:

#### Version Field

The version field is used for future backward compatibility.
At the current time, the field is always set to 0, to indicate the initial version.

#### Type Field

The type field is used to switch the frame message type.
The following message types are supported:

* 0x0 Data - Used to transmit data. May transmit zero length payloads depending on the flags.

* 0x1 Window Update - Used to updated the senders receive window size.
  This is used to implement per-stream flow control.

* 0x2 Ping - Used to measure RTT.
  It can also be used to heart-beat and do keep-alives over TCP.

* 0x3 Go Away - Used to close a session.

#### Flag Field

The flags field is used to provide additional information related to the message type.
The following flags are supported:

* 0x1 SYN - Signals the start of a new stream.
  May be sent with a data or window update message.
  Also sent with a ping to indicate outbound.

* 0x2 ACK - Acknowledges the start of a new stream.
  May be sent with a data or window update message.
  Also sent with a ping to indicate response.

* 0x4 FIN - Performs a half-close of a stream.
  May be sent with a data message or window update.

* 0x8 RST - Reset a stream immediately.
  May be sent with a data or window update message.

#### StreamID Field

The StreamID field is used to identify the logical stream the frame is addressing.
The client side should use odd ID's, and the server even.
This prevents any collisions.
Additionally, the 0 ID is reserved to represent the session.

Both Ping and Go Away messages should always use the 0 StreamID.

#### Length Field

The meaning of the length field depends on the message type:

* Data - provides the length of bytes following the header
* Window update - provides a delta update to the window size
* Ping - Contains an opaque value, echoed back
* Go Away - Contains an error code

### Message Flow

There is no explicit connection setup, as Yamux relies on an underlying transport to be provided.
However, there is a distinction between client and server side of the connection.

#### Opening a stream

To open a stream, an initial data or window update frame is sent with a new StreamID.
The SYN flag should be set to signal a new stream.

The receiver must then reply with either a data or window update frame with the StreamID along with the ACK flag to accept the stream or with the RST flag to reject the stream.

Because we are relying on the reliable stream underneath, a connection can begin sending data once the SYN flag is sent.
The corresponding ACK does not need to be received.
This is particularly well suited for an RPC system where a client wants to open a stream and immediately fire a request without waiting for the RTT of the ACK.

This does introduce the possibility of a connection being rejected after data has been sent already.
This is a slight semantic difference from TCP, where the connection cannot be refused after it is opened.
Clients should be prepared to handle this by checking for an error that indicates a RST was received.

#### Closing a stream

To close a stream, either side sends a data or window update frame along with the FIN flag.
This does a half-close indicating the sender will send no further data.

Once both sides have closed the connection, the stream is closed.

Alternatively, if an error occurs, the RST flag can be used to hard close a stream immediately.

#### Flow Control

When Yamux is initially starts each stream with a 256KiB window size.
There is no window size for the session.

To prevent the streams from stalling, window update frames should be sent regularly.
Yamux can be configured to provide a larger limit for windows sizes.
Both sides assume the initial 256KB window, but can immediately send a window update as part of the SYN/ACK indicating a larger window.

Both sides should track the number of bytes sent in Data frames only, as only they are tracked as part of the window size.

#### Session termination

When a session is being terminated, the Go Away message should be sent.
The Length should be set to one of the following to provide an error code:

* 0x0 Normal termination
* 0x1 Protocol error
* 0x2 Internal error

## Implementation considerations

### ACK backlog & backpressure

Yamux allows for a stream to be opened (and used) before it is acknowledged by the remote.
Yamux also does not specify a backpressure mechanism for opening new streams.

This presents a problem:
A peer must read from the socket and decode the frames to make progress on existing streams.
But any frame could also open yet another stream.

The ACK backlog is defined as the number of streams that a peer has opened which have not yet been acknowledged.
To support a basic form of backpressure, implementions:

- SHOULD at most allow an ACK backlog of 256 streams.
- MAY buffer unacknowledged inbound streams instead of resetting them when the application currently cannot handle any more streams.
  Such a buffer MUST be bounded in size to mitigate DoS attacks.
- MAY delay acknowledging new streams until the application has received or is about to send the first DATA frame.
