# mplex

> The spec for the friendly Stream Multiplexer (that works in 3 languages!)

| Lifecycle Stage | Maturity       | Status     | Latest Revision |
|-----------------|----------------|------------|-----------------|
| 3A              | Recommendation | Deprecated | r0, 2018-10-10  |

Authors: [@daviddias], [@Stebalien], [@tomaka]

Interest Group: [@yusefnapora], [@richardschneider], [@jacobheun]

[@daviddias]: https://github.com/daviddias
[@Stebalien]: https://github.com/Stebalien
[@tomaka]: https://github.com/tomaka
[@yusefnapora]: https://github.com/yusefnapora
[@richardschneider]: https://github.com/richardschneider
[@jacobheun]: https://github.com/jacobheun

See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Table of Contents

- [mplex](#mplex)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Deprecation Notice](#deprecation-notice)
  - [Message format](#message-format)
    - [Flag Values](#flag-values)
  - [Protocol](#protocol)
    - [Opening a new stream](#opening-a-new-stream)
    - [Writing to a stream](#writing-to-a-stream)
    - [Closing a stream](#closing-a-stream)
    - [Resetting a stream](#resetting-a-stream)
  - [Implementation notes](#implementation-notes)

## Overview

Mplex is a Stream Multiplexer protocol used by js-ipfs and go-ipfs in their implementations. The origins of this protocol are based in [multiplex](https://github.com/maxogden/multiplex), the JavaScript-only Stream Multiplexer. After many battle field tests, we felt the need to improve and fix some of its bugs and mechanics, resulting on this new version used by libp2p.

This document will attempt to define a specification for the wire protocol and algorithm used in both implementations.

Mplex is a very simple protocol that does not provide many features offered by other stream multiplexers. Notably, mplex does not provide backpressure at the protocol level.

Implementations in:

- [JavaScript](https://github.com/libp2p/js-libp2p-mplex)
- [Go](https://github.com/libp2p/go-mplex)
- [Rust](https://github.com/libp2p/rust-libp2p/tree/master/muxers/mplex)

## Deprecation Notice

**mplex is deprecated** for applications requiring resiliency and liveness.
Users should **prefer QUIC or Yamux**.

**Core limitation: lack of stream flow control**

mplex does not support stream-level flow control, preventing receivers from
applying backpressure. This leads to issues varying from easy to exploit DoS
vulnerabilities due to unbounded sender behavior to hard to debug application
stalls caused by a single slow stream receiver.

**Additional Shortcomings**:
- No stream-level flow control.
  - No way for a reader to backpressure a sender.
  - No good solution for slow readers.
    - Implementations generally do some combination of these mitigations:
      - Reset the stream once we reach a certain amount of unread buffered data.
        [source](https://github.com/libp2p/rust-libp2p/blob/1c9b3ca355aecffa0bcf83d2495cd4cc1019425b/muxers/mplex/src/config.rs#L118)
      - Block operations until the full stream is read from.
        [source](https://github.com/libp2p/rust-libp2p/blob/1c9b3ca355aecffa0bcf83d2495cd4cc1019425b/muxers/mplex/src/config.rs#L130)
      - Block up to a certain amount of time, then reset the stream.
        [source](https://github.com/libp2p/go-mplex/blob/ad9bfb922974b5875cc48c6e7492c4987c0cb94a/multiplex.go#L35-L37)
- Head of line blocking between streams
  - For example, No way to interleave data from streams if one stream makes a
    big write, and another stream has a small write
  - A single slow reader of a single stream can stall the whole application and TCP connection.
- No way of propagating errors.
  - Errors that could explain why a peer reset the stream.
- No way to signal to a peer that you will not read any more data (e.g. QUIC's
  STOP_SENDING frame).
- Both sides can open streams with the same ID, differing only by who opened the
  stream. which may lead to confusion.
- stream names are relatively unused (go-libp2p does not use them. I don't think rust-libp2p or js-libp2p uses them either)

## Message format

Every communication in mplex consists of a header, and a length prefixed data segment.

The header is an [unsigned base128 varint](https://github.com/multiformats/unsigned-varint). The lower three bits are the message flags, and the rest of the bits (shifted down by three bits) are the stream ID this message pertains to:

```
header = readUvarint()
flag = header & 0x07
id = header >> 3
```

The maximum header length is 9 bytes (per the unsigned-varint spec). With 9 continuation bits and 3 message flag bits the maximum stream ID is 60 bits (maximum value of `2^60 - 1`).

### Flag Values

```
| NewStream        | 0 |
| MessageReceiver  | 1 |
| MessageInitiator | 2 |
| CloseReceiver    | 3 |
| CloseInitiator   | 4 |
| ResetReceiver    | 5 |
| ResetInitiator   | 6 |
```

The data segment is length prefixed by another unsigned varint. This results in one message looking like:

```
| header  | length  | data           |
| uvarint | uvarint | 'length' bytes |
```

## Protocol

Mplex operates over a reliable ordered pipe between two peers, such as a TCP socket, or a unix pipe.

### Opening a new stream

To open a new stream, first allocate a new stream ID. Then, send a message with the flag set to `NewStream`, the ID set to the newly allocated stream ID, and the data of the message set to the name of the stream.

Stream names are purely for debugging purposes and are not otherwise considered by the protocol. An empty string may also be used for the stream name, and they may also be repeated (using the same stream name for every stream is valid). Reusing a stream ID after closing a stream may result in undefined behaviour.

The party that opens a stream is called the stream initiator. Both parties can open a substream with the same ID, therefore this distinction is used to identify whether each message concerns the channel opened locally or remotely.

### Writing to a stream

To write data to a stream, one must send a message with the flag `MessageReceiver` (1) or `MessageInitiator` (2) (depending on whether or not the writer is the one initiating the stream). The data field should contain the data you wish to write to the stream, up to 1MiB per message.

### Closing a stream

Mplex supports half-closed streams. Closing a stream closes it for writing and closes the remote end for reading but allows writing in the other direction.

To close a stream, send a message with a zero length body and a `CloseReceiver` (3) or `CloseInitiator` (4) flag (depending on whether or not the closer is the one initiaing the stream). Writing to a stream after it has been closed is a protocol violation. Reading from a remote-closed stream should return all data sent before closing the stream and then EOF thereafter.

### Resetting a stream

To reset a stream, send a message with a zero length body and a `ResetReceiver` (5) or `ResetInitiator` (6) flag.
See [stream resets](../connections/README.md#resets) for a detailed behaviour description.

## Implementation notes

If a stream is being actively written to, the reader must take care to keep up with inbound data. Due to the lack of back pressure at the protocol level, the implementation must handle slow readers by doing one or both of:

1. Blocking the entire connection until the offending stream is read.
2. Resetting the offending stream.

For example, the go-mplex implementation blocks for a short period of time and then resets the stream if necessary.
