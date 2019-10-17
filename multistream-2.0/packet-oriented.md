# Packet-oriented Multiselect 2.0

This proposal defines the packet-oriented extension of multiselect 2.0.

## Protocols

The needs of packet-oriented libp2p differ from those of stream-oriented libp2p
in the following ways:

- The underlying transports are message based, thus the requirements of a
  multiplexer are significantly diminished. Messages across different protocols
  are natively interleaved over a connectionless socket, so a multiplexer need
  only tag messages with their protocol. There are no ordering or transmission
  guarantees in packet-oriented transports such as UDP.
- Packet-oriented communication is inherently unidirectional. Since there is no
  notion of a connection or handshake in the underlying transports,
  packet-oriented protocols may simply speculatively send along packets to their
  peers until they receive a message instructing them otherwise.

As a result, since the underlying transports (e.g. UDP) delimit individual
messages received by a socket, it stands that it would be reasonable to extend
multiselect 2.0 for the packet-oriented case, adding or augmenting the following
messages:

- `multiselect/dynamic-inline`: Similar to `multiselect/dynamic`, but doesn't
  depend on a previous `multiselect/advertise`. Message is of the format:

  ```
  <multistream/multicodec><multistream/dynamic-inline><length(varint)><name(string)><id(varint)><optional payload>
  ```

  In this case, a dynamic identifier is established alongside the protocol's
  string name.
- `multiselect/dynamic`: An extended version of `multiselect/dynamic` that
  supports the optional addition of a payload. This will be used to send
  messages on a protocol for which a dynamic ID has been established via an
  `advertise` or `dynamic-inline` message.
- `multiselect/na`: Reject a protocol, referring to its dynamic identifier. This
  always is in reference to an identifier established by the remote peer.
- A version of `multiselect/multicodec` with optional payload