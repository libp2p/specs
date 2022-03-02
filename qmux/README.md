# A new stream muxer for libp2p

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r0, 2019-06-20  |

Authors: [@marten-seemann]
Interest Group: [@vyzo], [@vasco-santos], [@max-inden]

This stream muxer is inspired by QUIC's stream muxer, but deviates from its design in a few points:

1. TCP provides an ordering guarantee. This allow us to omit a few fields. For example, STREAM frames don't need to encode an offset, the offset is given implicitly by the order the frames are received in.
2. QUIC uses the cryptographic handshake to negotiate muxer parameters like initial flow control windows and the initial maximum stream number. Here, we define a SETTINGS frame to exchange muxer stettings.
3. In order to be able to send data right after initializing the muxer (and without waiting for the peer's SETTINGS frame), we define reasonable (minimal) default values.

Readers familiar with RFC 9000 will notice many similarities. This is not by accident: large parts of this document were copied from there and only slightly modified to fit TCP.

## Protocol Specification

### Settings

The first frame sent on a connection MUST be a SETTINGS frame. After sending a SETTINGS frame, a peer can start opening streams and send application data.

To allow sending of application data, the following limits apply before receipt of the peer's SETTINGS frame:

* initial max streams: 8 per type (unidirection and bidirectional)
* initial stream flow control window: 16 kB
* initial connection flow control window: 64 kB

The stream flow control limits apply to the first streams, no matter which value the peer sent in its SETTINGS frame. For all streams opened beyond that, the limits given in the SETTINGS frame apply.

### Streams

This section describes streams in terms of their send or receive components.  Two state machines are described: one for the streams on which an endpoint transmits data ([Sending Stream States](#sending-stream-states)) and another for streams on which an endpoint receives data ([Receiving Stream States](#receiving-stream-states)).

Unidirectional streams use either the sending or receiving state machine, depending on the stream type and endpoint role. Bidirectional streams use both state machines at both endpoints. For the most part, the use of these state machines is the same whether the stream is unidirectional or bidirectional. The conditions for opening a stream are slightly more complex for a bidirectional stream because the opening of either the send or receive side causes the stream to open in both directions.

The state machines shown in this section are largely informative. This document uses stream states to describe rules for when and how different types of frames can be sent and the reactions that are expected when different types of frames are received.  Though these state machines are intended to be useful in implementing the multiplexer, these states are not intended to constrain implementations. An implementation can define a different state machine as long as its behavior is consistent with an implementation that implements these states.

### Sending Stream States


          o
          | Create Stream (Sending)
          | Peer Creates Bidirectional Stream
          v
      +-------+
      | Ready | Send RESET_STREAM
      |       |-----------------------.
      +-------+                       |
          |                           |
          | Send STREAM /             |
          |      STREAM_DATA_BLOCKED  |
          v                           |
      +-------+                       |
      | Send  | Send RESET_STREAM     |
      |       |---------------------->|
      +-------+                       |
          |                           |
          | Send STREAM + FIN         |
          v                           v
      +-------+                   +-------+
      | Data  | Send RESET_STREAM | Reset |
      | Sent  |------------------>| Sent  |
      +-------+                   +-------+

The sending part of a stream that the endpoint initiates (types 0 and 2 for clients, 1 and 3 for servers) is opened by the application. The "Ready" state represents a newly created stream that is able to accept data from the application. Stream data might be buffered in this state in preparation for sending.

Sending the first STREAM or STREAM_DATA_BLOCKED frame causes a sending part of a stream to enter the "Send" state. An implementation might choose to defer allocating a stream ID to a stream until it sends the first STREAM frame and enters this state, which can allow for better stream prioritization.

The sending part of a bidirectional stream initiated by a peer (type 0 for a server, type 1 for a client) starts in the "Ready" state when the receiving part is created.

In the "Send" state, an endpoint transmits stream data in STREAM frames. The endpoint respects the flow control limits set by its peer and continues to accept and process MAX_STREAM_DATA frames. An endpoint in the "Send" state generates STREAM_DATA_BLOCKED frames if it is blocked from sending by stream flow control limits (**TODO**: reference section).

After the application indicates that all stream data has been sent and a STREAM frame containing the FIN bit is sent, the sending part of the stream enters the "Data Sent" state. The endpoint does not need to check flow control limits or send STREAM_DATA_BLOCKED frames for a stream in this state. MAX_STREAM_DATA frames might be received until the peer receives the final stream offset. The endpoint can safely ignore any MAX_STREAM_DATA frames it receives from its peer for a stream in this state.

From any state that is one of "Ready", "Send", or "Data Sent", an application can signal that it wishes to abandon transmission of stream data. Alternatively, an endpoint might receive a STOP_SENDING frame from its peer. In either case, the endpoint sends a RESET_STREAM frame, which causes the stream to enter the "Reset Sent" state.

An endpoint MAY send a RESET_STREAM as the first frame that mentions a stream; this causes the sending part of that stream to open and then immediately transition to the "Reset Sent" state.


### Receiving Stream States

          o
          | Recv STREAM / STREAM_DATA_BLOCKED / RESET_STREAM
          | Create Bidirectional Stream (Sending)
          | Recv MAX_STREAM_DATA / STOP_SENDING (Bidirectional)
          | Create Higher-Numbered Stream
          v
      +-------+
      | Recv  | Recv RESET_STREAM
      |       |-----------------------.
      +-------+                       |
          |                           |
          | Recv STREAM + FIN         |
          v                           |
      +-------+                       |
      | Size  | Recv RESET_STREAM     |
      | Known |---------------------->|
      +-------+                       |
          |                           |
          | Recv All Data             |
          v                           v
      +-------+ Recv RESET_STREAM +-------+
      | Data  |--- (optional) --->| Reset |
      | Recvd |  Recv All Data    | Recvd |
      +-------+<-- (optional) ----+-------+
          |                           |
          | App Read All Data         | App Read Reset
          v                           v
      +-------+                   +-------+
      | Data  |                   | Reset |
      | Read  |                   | Read  |
      +-------+                   +-------+

The receiving part of a stream initiated by a peer (types 1 and 3 for a client, or 0 and 2 for a server) is created when the first STREAM, STREAM_DATA_BLOCKED, or RESET_STREAM frame is received for that stream. For bidirectional streams initiated by a peer, receipt of a MAX_STREAM_DATA or STOP_SENDING frame for the sending part of the stream also creates the receiving part. The initial state for the receiving part of a stream is "Recv".

For a bidirectional stream, the receiving part enters the "Recv" state when the sending part initiated by the endpoint (type 0 for a client, type 1 for a server) enters the "Ready" state.

An endpoint opens a bidirectional stream when a MAX_STREAM_DATA or STOP_SENDING frame is received from the peer for that stream. Receiving a MAX_STREAM_DATA frame for an unopened stream indicates that the remote peer has opened the stream and is providing flow control credit. Receiving a STOP_SENDING frame for an unopened stream indicates that the remote peer no longer wishes to receive data on this stream.

Before a stream is created, all streams of the same type with lower-numbered stream IDs MUST be created. This ensures that the creation order for streams is consistent on both endpoints.

In the "Recv" state, the endpoint receives STREAM and STREAM_DATA_BLOCKED frames. Incoming data is buffered passed to the application. As data is consumed by the application and buffer space becomes available, the endpoint sends MAX_STREAM_DATA frames to allow the peer to send more data.

When a STREAM frame with a FIN bit is received, the final size of the stream is known; see **TODO: link**. The receiving part of the stream then enters the "Size Known" state. In this state, the endpoint no longer needs to send MAX_STREAM_DATA frames; it only receives any retransmissions of stream data.

Once all data for the stream has been received, the receiving part enters the "Data Recvd" state. This might happen as a result of receiving the same STREAM frame that causes the transition to "Size Known".

The "Data Recvd" state persists until stream data has been delivered to the application. Once stream data has been delivered, the stream enters the "Data Read" state, which is a terminal state.

Receiving a RESET_STREAM frame in the "Recv" or "Size Known" state causes the stream to enter the "Reset Recvd" state.  This might cause the delivery of stream data to the application to be interrupted.

Sending a RESET_STREAM means that an endpoint cannot guarantee delivery of stream data; however, there is no requirement that stream data not be delivered if a RESET_STREAM is received. An implementation MAY interrupt delivery of stream data, discard any data that was not consumed, and signal the receipt of the RESET_STREAM. A RESET_STREAM signal might be suppressed or withheld if stream data is completely received and is buffered to be read by the application. If the RESET_STREAM is suppressed, the receiving part of the stream remains in "Data Recvd".

Once the application receives the signal indicating that the stream was reset, the receiving part of the stream transitions to the "Reset Read" state, which is a terminal state.

### Permitted Frame Types

The sender of a stream sends just three frame types that affect the state of a stream at either the sender or the receiver: STREAM, STREAM_DATA_BLOCKED and RESET_STREAM.

A sender MUST NOT send any of these frames from a terminal state ("Data Recvd" or "Reset Recvd"). A sender MUST NOT send a STREAM or STREAM_DATA_BLOCKED frame for a stream in the "Reset Sent" state or any terminal state -- that is, after sending a RESET_STREAM frame.

The receiver of a stream sends MAX_STREAM_DATA frames and STOP_SENDING frames.

The receiver only sends MAX_STREAM_DATA frames in the "Recv" state. A receiver MAY send a STOP_SENDING frame in any state where it has not received a RESET_STREAM frame -- that is, states other than "Reset Recvd" or "Reset Read". However, there is little value in sending a STOP_SENDING frame in the "Data Recvd" state, as all stream data has been received. A sender could receive either of these two types of frames in any state as a result of delayed delivery of packets.

### Solicited State Transitions

If an application is no longer interested in the data it is receiving on a stream, it can abort reading the stream and specify an application error code.

If the stream is in the "Recv" or "Size Known" state, the transport SHOULD signal this by sending a STOP_SENDING frame to prompt closure of the stream in the opposite direction.  This typically indicates that the receiving application is no longer reading data it receives from the stream, but it is not a guarantee that incoming data will be ignored.

STREAM frames received after sending a STOP_SENDING frame are still counted toward connection and stream flow control, even though these frames can be discarded upon receipt.

A STOP_SENDING frame requests that the receiving endpoint send a RESET_STREAM frame. An endpoint that receives a STOP_SENDING frame MUST send a RESET_STREAM frame if the stream is in the "Ready" or "Send" state.

An endpoint SHOULD copy the error code from the STOP_SENDING frame to the RESET_STREAM frame it sends, but it can use any application error code. An endpoint that sends a STOP_SENDING frame MAY ignore the error code in any RESET_STREAM frames subsequently received for that stream.

STOP_SENDING SHOULD only be sent for a stream that has not been reset by the peer. STOP_SENDING is most useful for streams in the "Recv" or "Size Known" state.

An endpoint that wishes to terminate both directions of a bidirectional stream can terminate one direction by sending a RESET_STREAM frame, and it can encourage prompt termination in the opposite direction by sending a STOP_SENDING frame.

## Data Flow Control

qmux employs a limit-based flow control scheme where a receiver advertises the limit of total bytes it is prepared to receive on a given stream or for the entire connection.  This leads to two levels of data flow control in qmux:

   *  Stream flow control, which prevents a single stream from consuming the entire receive buffer for a connection by limiting the amount of data that can be sent on each stream.
   *  Connection flow control, which prevents senders from exceeding a receiver's buffer capacity for the connection by limiting the total bytes of stream data sent in STREAM frames on all streams. 

Senders MUST NOT send data in excess of either limit.

A receiver sets initial limits for all streams in the SETTINGS frame. Subsequently, a receiver sends MAX_STREAM_DATA frames or MAX_DATA frames to the sender to advertise larger limits.

A receiver can advertise a larger limit for a stream by sending a MAX_STREAM_DATA frame with the corresponding stream ID. A MAX_STREAM_DATA increases the maximum absolute byte offset of a stream. A receiver could determine the flow control offset to be advertised based on the current offset of data consumed on that stream.

A receiver can advertise a larger limit for a connection by sending a MAX_DATA frame, which increases the maximum of the sum of the absolute byte offsets of all streams. A receiver maintains a cumulative sum of bytes received on all streams, which is used to check for violations of the advertised connection or stream data limits. A receiver could determine the maximum data limit to be advertised based on the sum of bytes consumed on all streams.

Once a receiver advertises a limit for the connection or a stream, it MUST NOT advertise a smaller limit. Advertising a smaller limit leads to a FLOW_CONTROL_ERROR.

A receiver MUST close the connection with an error of type FLOW_CONTROL_ERROR if the sender violates the advertised connection or stream data limits.

If a sender has sent data up to the limit, it will be unable to send new data and is considered blocked. A sender SHOULD send a STREAM_DATA_BLOCKED or DATA_BLOCKED frame to indicate to the receiver that it has data to write but is blocked by flow control limits. If a sender is blocked for a period longer than a locally chosen timeout, the receiver might close the connection even when the sender has data that is available for transmission. To keep the connection from closing, a sender that is flow control limited SHOULD periodically send a STREAM_DATA_BLOCKED or DATA_BLOCKED frame.

**TODO**: we'll have to think about this very carefully.

### Increasing Flow Control Limits

Implementations decide when and how much credit to advertise in MAX_STREAM_DATA and MAX_DATA frames, but this section offers a few considerations.

To avoid blocking a sender, a receiver MAY send a MAX_STREAM_DATA or MAX_DATA frame multiple times within a round trip or send it early enough to allow time for loss of the frame and subsequent recovery.

Control frames contribute to connection overhead.  Therefore, frequently sending MAX_STREAM_DATA and MAX_DATA frames with small changes is undesirable.  On the other hand, if updates are less frequent, larger increments to limits are necessary to avoid blocking a sender, requiring larger resource commitments at the receiver. There is a trade-off between resource commitment and overhead when determining how large a limit is advertised.

A receiver can use an autotuning mechanism to tune the frequency and amount of advertised additional credit based on a round-trip time estimate and the rate at which the receiving application consumes data, similar to common TCP implementations.  As an optimization, an endpoint could send frames related to flow control only when there are other frames to send, ensuring that flow control does not cause extra packets to be sent.

A blocked sender is not required to send STREAM_DATA_BLOCKED or DATA_BLOCKED frames.  Therefore, a receiver MUST NOT wait for a STREAM_DATA_BLOCKED or DATA_BLOCKED frame before sending a MAX_STREAM_DATA or MAX_DATA frame; doing so could result in the sender being blocked for the rest of the connection. Even if the sender sends these frames, waiting for them will result in the sender being blocked for at least an entire round trip.

### Handling Stream Cancellation

Endpoints need to eventually agree on the amount of flow control credit that has been consumed on every stream, to be able to account for all bytes for connection-level flow control.

On receipt of a RESET_STREAM frame, an endpoint will tear down state for the matching stream and ignore further data arriving on that stream.

RESET_STREAM terminates one direction of a stream abruptly. For a bidirectional stream, RESET_STREAM has no effect on data flow in the opposite direction. Both endpoints MUST maintain flow control state for the stream in the unterminated direction until that direction enters a terminal state.

### Stream Final Size

The final size is the amount of flow control credit that is consumed by a stream. This value is one higher than the offset of the byte with the largest offset sent on the stream, or zero if no bytes were sent.

A sender always communicates the final size of a stream to the receiver, no matter how the stream is terminated. The final size is the sum of the Length fields of all STREAM frames received, once the STREAM frame with the FIN flag has been received.
Alternatively, the Final Size field of a RESET_STREAM frame carries this value.  This guarantees that both endpoints agree on how much flow control credit was consumed by the sender on that stream.

An endpoint will know the final size for a stream when the receiving part of the stream enters the "Size Known" or "Reset Recvd" state. The receiver MUST use the final size of the stream to account for all bytes sent on the stream in its connection-level flow controller.

An endpoint MUST NOT send data on a stream at or beyond the final size.

Once a final size for a stream is known, it cannot change.  If a RESET_STREAM or STREAM frame is received indicating a change in the final size for the stream, an endpoint SHOULD respond with an error of type FINAL_SIZE_ERROR. A receiver SHOULD treat receipt of data at or beyond the final size as an error of type FINAL_SIZE_ERROR, even after a stream is closed. Generating these errors is not mandatory, because requiring that an endpoint generate these errors also means that the endpoint needs to maintain the final size state for closed streams, which could mean a significant state commitment.

### Controlling Concurrency

An endpoint limits the cumulative number of incoming streams a peer can open.  Only streams with a stream ID less than "(max_streams * 4 + first_stream_id_of_type)" can be opened.  Initial limits are set in the SETTINGS frame (**TODO**: link). Subsequent limits are advertised using MAX_STREAMS frames. Separate limits apply to unidirectional and bidirectional streams.

Endpoints MUST NOT exceed the limit set by their peer.  An endpoint that receives a frame with a stream ID exceeding the limit it has sent MUST treat this as a connection error of type STREAM_LIMIT_ERROR.

Once a receiver advertises a stream limit using the MAX_STREAMS frame, advertising a smaller limit has no effect. MAX_STREAMS frames that do not increase the stream limit MUST be ignored.

As with stream and connection flow control, this document leaves implementations to decide when and how many streams should be advertised to a peer via MAX_STREAMS. Implementations might choose to increase limits as streams are closed, to keep the number of streams available to peers roughly consistent.

An endpoint that is unable to open a new stream due to the peer's limits SHOULD send a STREAMS_BLOCKED frame. This
signal is considered useful for debugging. An endpoint MUST NOT wait to receive this signal before advertising additional credit, since doing so will mean that the peer will be blocked for at least an entire round trip, and potentially indefinitely if the peer chooses not to send STREAMS_BLOCKED frames.
   
## Wire Format

MAX_STREAM_DATA increases the stream flow control limit for a particular stream.

```
MAX_STREAM_DATA {
	StreamID varint
	Increment varint
}
```

MAX_DATA increases the connection flow control limit.

```
MAX_DATA {
	Increment varint
}
```

MAX_STREAMS increases the number of streams the peer is allowed to open.

```
MAX_STREAMS {
	Type bool // uni- or bidirectional
	Increment varint
}
```

RESET_STREAM resets the send-side of a stream.

```
RESET_STREAM {
	StreamID varint
	ErrorCode varint
}
```

STOP_SENDING asks the peer to stop sending on a stream. On receipt of this frame, the peer MUST immediately send a RESET_STREAM frame.

```
STOP_SENDING {
	StreamID varint
	ErrorCode varint
}
```

STREAM frames carry application data.

```
STREAM {
	StreamID varint
	Length varint
	Data []byte
}
```

CONNECTION_CLOSE closes the connection.

```
CONNECTION_CLOSE {
	ErrorCode varint
	ReasonLength varint
	Reason string
}

```

The SETTINGS frame carries configuration options for the stream muxer.
```
SETTINGS {
	Length varint
	[
		SettingID varint
		Length varint
		Value []byte
	]
}
```

Currently, the following settings are defined:

1. Initial Stream Flow Control Window (for each stream type)
2. Initial Max Streams (for each stream type)
