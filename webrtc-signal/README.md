# WebRTC Signaling Protocol

Author: Alex Browne (@albrow)

Revision: DRAFT; 2019-04-21

This specification describes a protocol for establishing a WebRTC connection
between two peers via a common third peer, called the "signaler".

## Motivation

A standard protocol for WebRTC Signaling can be used to develop a WebRTC
transport. Such a transport can be used to faciliate connections between two
browser peers without relying on a relay or any other third-party (They only
need to rely on the signaler to establish the initial connection).

## Background

WebRTC is currently the best and most widely supported technology for
browser-based peer-to-peer communication. While often used for VoIP/video chat
applications, WebRTC also supports "data channels" for communicating arbitrary
bytes of data.

Partly due to browser security concerns, it is not possible to directly dial an
arbitrary peer (e.g. via their IP address) using WebRTC. Instead, WebRTC
utilizes the
[Interactive Connectivity Establishment (or "ICE") protocol](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Connectivity)
to establish a connection between two peers. Roughly speaking, the process is
as follows:

1. One peer, called the "offerer", generates an "offer". The offer includes some
   information about how this peer can be reached (IP address, port, etc.) as
   well as one or more proposed configurations for the connection.
2. The offer is communicated to another peer, called the "answerer".
3. The answerer generates an "answer" corresponding to the offer. If possible,
   it selects the best of the connection configurations proposed by the offerer.
4. The answer is communicated back to the original offerer. If both the offerer
   and answerer have come to an agreement, a connection is established.

This process may be repeated until both the offerer and the answerer have agreed
on a configuration for their connection.

Neither WebRTC nor ICE specify _how_ answers and offers should be communicated.
That detail is left to application developers. The goal of this document is to
provide a more detailed specification about how answers and offers can be
communicated to peers using a third-party called a signaler.

## Identity and Authenticity

Each peer that communicates with the signaler is identified by a PeerID.
Messages sent to the signaler are signed with a private key
corresponding to that PeerID. This prevents tampering and impersontation. In
other words, it ensures that a peer can only be connected to the peer that they
intended to connect to.

## Peer Discovery

This document does not specify how peers should discover one another and is
designed to be compatible with any peer discovery mechanism. Here are the
requirements for the WebRTC signaling protocol described in this document:

1. A peer knows the PeerID of the peer it wants to connect to.
2. Both peers agree to use the same signaler.

It is possible for a signaler itself to implement peer discovery (e.g.,
using the Rendezvous Protocol), but this is not a strict requirement.

## Multiaddress format

The Signaling Protocol is designed to work over existing libp2p transports. We
use the following multiaddress format for dialing and listening:

```
<signaler-multiaddr>/p2p-webrtc-signal/<signaler-peer-id>
```

Where `<signaler-multiaddr>` is the multiaddress for the signaler (including
the transport to be used for signaling) and `<signaler-peer-id>` is the
base58-encoded PeerID of the signaler. `<signaler-multiaddr>` may be omitted to
use an existing connection to `<signaler-peer-id>` for signaling.

This multiaddress format allows for flexibility in the underlying transport
used. The signaler can be either centralized (all peers use the same signaler)
or decentralized (two peers use a common third peer for signaling).

### Examples

- Signaling over WebSockets using an IPv4 address:
  `/ip4/192.168.1.46/tcp/9000/ws/p2p-webrtc-signal/QmWaWqTtzPCaYnpfxsAAGtrVhNumHqQ7jtdcsFsjvs3csS`
- Signaling over HTTP using a domain name:
  `/dns6/signaler.myapp.com/tcp/80/http/p2p-webrtc-signal/QmZbw3TKr3dxhHXiPkbNraWaeGoqPNXAXfAcV8RP2Eqngj`
- Signaling via a common peer:
  `/p2p-webrtc-signal/QmWeRHDDiwuGnS4xbjF2zXETucL7xQLjadoaTZ4yJE3hQs`

## Message Types

### SendOffer

Used by an offerer to send an offer to a specific peer.

#### Request

```javascript
{
  "peer_id": String, // The PeerID of the peer sending this request (the offerer).
  "answerer_id": String, // The PeerID of the answerer.
  "offer": { // An RTCSessionDescription of type "offer". See https://developer.mozilla.org/en-US/docs/Web/API/RTCSessionDescription.
    "type": "offer",
    "sdp:": String
  }
}
```

#### Response

```javascript
{
}
```

### GetOffers

Used by an answerer to receive up to `max_count` pending offers.

#### Request

```javascript
{
  "peer_id": String, // The PeerID of the peer sending this request (the answerer).
  "max_count": Number, // The maximum number of offers to be returned.
}
```

#### Response

```javascript
{
  "offers": [ // An array of RTCSessionDescriptions of type "offer".
    {
      "type": "offer",
      "sdp": String
    }
  ]
}
```

### SendAnswer

Used by an answerer to send an answer to a specific offerer.

#### Request

```javascript
{
  "peer_id": String // The PeerID of the peer sending this request (the answerer).
  "offerer_id": String // The PeerID of the offerer.
  "answer": { // An RTCSessionDescription of type "answer". Must correspond to the offer sent by offerer.
    "type": "answer",
    "sdp": String
  }
}
```

#### Response

```javascript
{
}
```

### GetAnswers

Used by an offerer to receive up to `max_count` pending answers.

#### Request

```javascript
{
  "peer_id": String, // The PeerID of the peer sending this request (the offerer).
  "max_count": Number // The maximum number of answers to be returned.
}
```

#### Response

```javascript
{
  "answers": [ // An array of RTCSessionDescriptions of type "answer".
    {
      "type": "answer",
      "sdp": String
    }
  ]
}
```

## Statefulness and Timeouts

The API above implicitly requires the signaler to maintain some state
about pending offers and answers. When an answer or offer is sent to the
signaler, it will need to store them until the corresponding peer requests them
via `GetAnswers` or `GetOffers` requests. The timeline of an answer/offer
handshake is as follows:

1. The offerer sends a `SendOffer` request.
1. The signaler stores the offer, which is considered "pending".
1. The answerer sends a `GetOffers` request and receives the offer.
1. After the offer has been received, it is no longer pending and the signaler may safely delete it.
1. The answerer sends a `SendAnswer` request.
1. The signaler stores the answer, which is considered "pending".
1. The offerer receives a the answer via a `GetAnswers` request.
1. After the answer has been received, it is no longer pending and the signaler may safely delete it.

In order to avoid filling up storage space with pending answers and offers, the
signaler should delete any pending answers or offers that have not been
received after 60 seconds. Clients which communicate with the signaler
can also drop a peer and update their internal state if they don't receive an
answer within 60 seconds.
