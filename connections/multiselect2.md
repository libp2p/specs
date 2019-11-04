# Multiselect 2.0

## Introduction

Multiselect 2.0 replaces the Multistream protocol. Compared to its predecessor, it offers:

1. Downgrade protection for the security protocol negotiation.
2. Zero-rountrip stream multiplexer negotiation for handshake protocols that take advantage of early data mechanisms (one-roundtrip negotation for protocols / implementations that don't).
3. Compression for the protocol identifiers of frequently used protocols.

By using protobufs for all control messages, Multiselect 2.0 provides an easy path for future protocol upgrades. The protobuf format guarantees that unknown field in a message will be skipped, thus future version of the protocol can add new fields that signal support for new protocol features.

## High-Level Overview

### Handshake Protocol Selection

Handshake protocols are not being negotiated, but are announced in the peers' multiaddrs. 

**TODO**: Do we need to describe the format here? I guess we don't, but we will probably need another document for that change, and we can link to it from here.

Peers advertising a multiaddr that includes a handshake protocol MUST support Multiselect 2.0 as described in this document.

#### TCP Simultaneous Open

TCP allows the establishment of a connection if two endpoints start initiating a connection at the same time. This is called TCP Simultaneous Open. For libp2p, this is problematic, since most stream multiplexers assign stream IDs based on the role (client or server) of and endpoint.

It is therefore desirable to fail a connection attempt as early as possible, if a TCP Simultaneous Open occurs. TLS 1.3 and Noise provide this guarantee: For example, the TLS handshake will fail if an endpoint receives a ClientHello instead of a ServerHello as a response to its ClientHello.

Since secio doesn't provide this property, secio cannot be used with Multiselect 2.0.

### Stream Multiplexer Selection

This section only applies if Multiselect 2 is run over a transport that is not natively multipexed. Transports that provide stream multiplexing on the transport layer (e.g. QUIC) don't need to do anything described in this section.

Some handshake protocols (TLS 1.3, some variants of Noise (**TODO**: specify which)) support sending of *Early Data*. Early Data can be sent by the server after receiving the first handshake message from the client. It is encrypted, however, at that point of the handshake the client's identity is not yet verified.

In Multiselect 2 the server makes use of Early Data by sending a list of stream multiplexers. This ensures that the client can choose a stream multiplexer as soon as the handshake completes (or fail the connection if it doesn't support any stream multiplexer offered by the server).

Note that this negotiation scheme allows peers to negotiate a "monoplexed" connection, i.e. a connection that doesn't use any stream multiplexer. Endpoints can offer support for monoplexed connections by offering the `/monoplex` stream multiplexer.

**TODO**: Do we need to define a way to send an error code / error string? Or do we have something like that in libp2p already?

![](handshake.png)

Handshake protocols (or implementations of handshake protocols) that don't support sending of Early Data will have to run the stream multiplexer selection after the handshake completes.

#### 0-RTT

When using 0-RTT session resumption as offered by TLS 1.3 and some variants of Noise (**TODO**: specify which), the endpoints MUST remember the negotiated stream multiplexer used on the original connection. This ensures that the client can send application data in the first flight when resuming a connection.

## Protocol Speficiation

All messages are Protobuf messages using the `proto3` syntax. Every message is wrapped by the `Multiselect` message:

```protobuf
# Wraps every message
message Multiselect {
    oneof message {
        Offer offer = 1;
        Use use = 2;
    }
}
```

The `Offer` message is used to initiate a conversation on a new stream. It contains either a single or multiple protocols that the endpoint would like to use on the stream.
A `Protocol` is the application protocol spoken on top of an ordered byte stream. The `name` of a protocol is the protocol identifier, e.g. `/ipfs/ping/1.0.0`. The `id` is a numeric abbreviation for this protocol (see below for details how `id`s are assigned).
If the endpoint only selects a single protocol, it MAY start sending application data right after the protobuf message. Since it has not received confirmation if the peer actually supports the protocol, any such data might be lost in that case.
If the endpoint selects multiple protocols, it MUST wait for the peer's choice of the application protocol (see description of the `Use` message) before sending application.

```protobuf
# Select a list of protocols.
message Offer {
    message Protocol {
        oneof protocol {
            string name = 1;
            uint64 id = 2;
        }
    }
    repeated Protocol protocols = 1;
}
```

The `Use` message is sent in response to the `Offer`. And endpoint MUST treat the receipt of a `Use` message before having sent a `Offer` message on the stream as a connection error.
If none of the protocol(s) listed in the `Offer` message are acceptable, and endpoint resets both the send- and the receive-side of the stream.

If an endpoint receives an  `Offer` message that only offers a single protocol, it accepts this protocol by sending an empty `Use` message (i.e. a message that doesn't list any `protocol`), or a `Use` message that assigns a protocol id (see below). Sending an empty `Use` message in response to a`Offer` message that offers multiple protocols is not permitted, and MUST be treated as a connection error by an endpoint.

If an endpoint receives a `Offer` message that offers multiple protocols, it chooses an application protocol that it would like to speak on this stream. It informs the peer about its choice by sending its selection in the `protocol` field of the `Use` message.

When choosing a protocol, an endpoint can allow its peer to save bytes on the wire for future use of the same protocol by assigning a numeric identifier for the protocol by sending an `id`. The identifier is valid for the lifetime of the connection. The identifier must be unique for the protocol, an endpoint MUST NOT use the same identifier for different protocols.

```protobuf
# Declare that a protocol is used on this stream.
# By using an id (instead of a name), an endpoint can provide the peer
# an abbreviation to use for future uses of the same protocol.
message Use {
    message Protocol {
        uint64 id = 1;
        string name = 2;
    }
    Protocol protocol = 1;
}
```
