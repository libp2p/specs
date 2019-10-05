# Security Negotiation for Packet-oriented libp2p - PSEC
_Level 1, Working Draft_

This document defines a security negotiation protocol for packet-oriented
libp2p. This protocol is meant to enable two peers to agree upon a security
scheme to protect traffic between them over packet-oriented, potentially
unreliable transports such as UDP. Examples of such security schemes include
[DTLS](#) and [QUIC DATAGRAM](#). Within the document, this protocol shall be
referred to as **PSEC**, for **P**acket **Sec**urity.

This packet will occasionally reference the follow specifications:

- [Multihash](#)
- [Varints](#)
- [Peer IDs](#)

## Frames

Messages exchanged in the PSEC protocol share a simple framing:

```
<Message Type, uint8>
[Optional Message Body]
```

Valid message types include:

```
0   - Propose security scheme
1   - Accept security scheme
255 - Reject security schemes
```

## Protocol

This protocol attempts to be friendly to peer-to-peer situations in which two
peers simulataneously send messages to one another, and will deterministically
arrive at a single "leader" who will go on to initiate the security scheme,
should consensus be achieved.

### Proposal

The protocol begins when at least one of a pair of peers sends the other a
"proposal" message. The purpose of the proposal, as the name suggests, is to
propose a set of security schemes.

A proposal packet is framed with the afforementioned code, 0. The message body
is as follows:

```
<Varint delimited sender peer ID encoded as multihash>
<8-bit unsigned integer, N, number of security schemes>
<N varint delimited strings representing security schemes>
[Optional var-int delimited initiation packet for first-listed scheme]
```

The message begins with the sender's peer ID, useful in the case when the
receiving peer has not yet engaged with the sender. Next, the sender encodes an
8-bit unsigned integer value, N, representing the number of security schemes
it is proposing.

Following the integer N, the sender encodes N varint delimited strings
representing the sender's proposed security schemes. These strings are
considered to be priority ordered, so the first encoded string represents the
sender's first choice, and so on.

After the Nth string, the sender may optionally include (should they wish to and
should it fall under the underlying transport's maximum packet size) the first
packet they would send over their **first choice** security scheme's intiation
packet, should such a concept be relevant to the scheme.

### Response

There are two possible scenarios that a peer receiving a proposal may find
themselves in:

- Simultaneous negotiation, in which both peers have sent and received a
  proposal packet before receiving a response packet
- Standard negotiation, in which the receiver has not sent an outstanding
  proposal

These scenarios are described separately.

#### Simultaneous Negotiation

In the event of a simultaneous negotiation as described, rather than send accept
or reject message, the peers may proceed as follows.

If there is no intersection between the lists of strings provided in each
proposal packet, the session may be terminated as there is no shared security
scheme present.

If there are one or more intersecting strings in the lists provided, choose the
cumulativley higher priority one, determined by adding the scheme's index in
each list and choosing the scheme with the lowest cumulative index. If two or
more items share a cumulative index, choose the option favored by the peer with
the ID which, when viewed in its binary encoded form as a big unsigned
integer, is closer to 0. **The peer with the lowest peer ID is now the initiator
if such a concept is relevant to the winning scheme and may initiate a secure
channel.** From here, all future communications with this peer via this
transport can be assumed to be the security scheme.

#### Standard Negotiation

In the standard case, the receiver parses the proposal packet. If the receiver 
wishes to proceed with any of the listed schemes, they may send an accept
packet, framed with 1, the accept type. The body of the message is the varint
delimited string naming the security scheme. Unlike the simultaneous case, the
initiator of the selected security scheme shall be assumed to be the sender of 
the proposal. From here, all future communications with this peer via this
transport can be assumed to be the security scheme.

If the receiver does not wish to proceed with any of the listed schemes, the
receiver may send a reject packet, framed with the code 255, followed by no
additional data.