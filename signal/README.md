# WebRTC Signal Protocol

Author: Alex Browne (@albrow)

Revision: DRAFT; 2019-03-18

This specification describes a protocol for establishing a WebRTC connection
between two peers via a "Signaling Server".

## Motivation

A standard protocol for WebRTC Signaling can be used to develop a WebRTC
transport. Such a transport can be used to faciliate connections between two
browser peers without relying on a relay or any other third-party (They only
need to rely on the Signaling Server to establish the initial connection).

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
communicated to peers using a third-party called a Signaling Server.

## Identity and Authenticity

Each peer that communicates with the Signaling Server is identified by a PeerID.
Messages sent to the Signaling Server are signed with a private key
corresponding to that PeerID. This prevents tampering and impersontation. In
other words, it ensures that a peer can only be connected to the peer that they
intended to connect to.

## Peer Discovery

This document does not specify how peers should discover one another and is
designed to be compatible with any peer discovery mechanism. Here are the
requirements for the WebRTC signaling protocol described in this document:

1. A peer knows the PeerID of the peer it wants to connect to.
2. Both peers agree to use the same Signaling Server.

It is possible for a Signaling Server itself to implement peer discovery (e.g.,
using the Rendezvous Protocol), but this is not a strict requirement.

## Signaling Server API

The Signaling Server uses a simple HTTP API with support for long-polling. The
HTTP endpoints for the server are as follows:

### POST /send_offer

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

### POST /get_offers

Used by an answerer to receive up to `max_count` pending offers.

This endpoint supports long-polling and the request may be kept alive until at
least one answer is available. The server may, at its discretion, decide to
close the request by returning an empty array of answers if no answers are
available after a certain amount of time has passed.

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

### POST /send_answer

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

### POST /get_answers

Used by an offerer to receive up to `max_count` pending answers.

This endpoint supports long-polling and the request may be kept alive until at
least one answer is available. The server may, at its discretion, decide to
close the request by returning an empty array of answers if no answers are
available after a certain amount of time has passed.

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

The HTTP API above implicitly requires the Signaling Server to maintain some
state about pending offers and answers. When an answer or offer is sent to the
server, it will need to store them (typically in a database) until the
corresponding peer requests them via the `/get_answers` or `/get_offers`
endpoint. The timeline of an answer/offer handshake is as follows:

1. The offerer sends a `/create_offer` request.
1. The Signaling Server stores the offer, which is considered "pending".
1. The answerer polls the `/get_offers` endpoint and receives the offer.
1. After the offer has been received, it is no longer pending and the Signaling Server may safely delete it.
1. The answerer sends a `/create_answer` request.
1. The Signaling Server stores the answer, which is considered "pending".
1. The offerer receives a the answer via the `/get_answers` endpoint.
1. After the answer has been received, it is no longer pending and the Signaling Server may safely delete it.

In order to avoid filling up storage space with pending answers and offers, the
Signaling Server should delete any pending answers or offers that have not been
received after 60 seconds. Clients which communicate with the Signaling Server
will also understand that if they don't see a response from a specific peer (via
the `/get_offers` or `/get_answers` endpoint) within 60 seconds, the
answer/offer has timed out.
