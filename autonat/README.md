# NAT Discovery
> How we detect if we're behind a NAT.

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Recommendation | Active | r0, 2021-08-26  |


Authors: [@marten-seemann]

Interest Group: [@mxinden], [@vyzo], [@raulk], [@stebalien], [@willscott]

[@marten-seemann]: https://github.com/marten-seemann
[@mxinden]: https://github.com/mxinden/
[@vyzo]: https://github.com/vyzo
[@raulk]: https://github.com/raulk
[@stebalien]: https://github.com/stebalien
[@willscott]: https://github.com/willscott

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Table of Contents

TODO: fill in

## Overview

A priori, a node cannot know if it is behind a NAT / firewall or if it is publicly reachable.
Knowing its NAT status is essential for the node to be well-behaved in the
network: A node that's behind a NAT doesn't need to advertise its (undiable)
addresses to the rest of the network, preventing superfluous dials from other
peers. Furthermore, it might actively seek to improve its connectivity by
finding a relay server, which would allow other peers to establish a relayed
connection.

To determine if it is located behind a NAT, nodes use the `autonat` protocol.
Using this protocol, the node requests other peers to dial its presumed public
addresses. If a couple of these dial attempts succeed, the node can be reasonably
certain that it is not located behind a NAT. Likewise, if a couple of these dial
attempts fail, this is a strong indicator that a NAT is blocking incoming
connections.

## AutoNAT Protocol

The AutoNAT Protocol uses the Protocol ID `/libp2p/autonat/1.0.0`. The node
wishing to determine its NAT status opens a stream using this protocol ID, and
then sends a `Dial` message. The `Dial` message contains a list of multiaddresses.
Upon receiving this message, the peer starts to dial these addresses. It MAY
dial all of them in parallel. The peer MAY use a different IP and peer ID than
it uses for its regular libp2p connection to perform these dial backs.

In order to prevent attacks like the one described in [RFC 3489, Section
12.1.1](https://www.rfc-editor.org/rfc/rfc3489#section-12.1.1) (see excerpt
below), implementations MUST NOT dial any multiaddress unless it is based on the
IP address the requesting node is observed as.

> RFC 3489 12.1.1 Attack I: DDOS Against a Target
>
> In this case, the attacker provides a large number of clients with the same
> faked MAPPED-ADDRESS that points to the intended target. This will trick all
> the STUN clients into thinking that their addresses are equal to that of the
> target. The clients then hand out that address in order to receive traffic on
> it (for example, in SIP or H.323 messages). However, all of that traffic
> becomes focused at the intended target. The attack can provide substantial
> amplification, especially when used with clients that are using STUN to enable
> multimedia applications.

If all dials fail, the receiver sends a `DialResponse` message with the
`ResponseStatus` `E_DIAL_ERROR`. If at least one of the dials complete
successfully, it sends a `DialResponse` with the `ResponseStatus` `OK`. It
SHOULD include the address it successfully dialed in its response.

```proto
syntax = "proto2";

message Message {
  enum MessageType {
    DIAL          = 0;
    DIAL_RESPONSE = 1;
  }

  enum ResponseStatus {
    OK               = 0;
    E_DIAL_ERROR     = 100;
    E_DIAL_REFUSED   = 101;
    E_BAD_REQUEST    = 200;
    E_INTERNAL_ERROR = 300;
  }

  message PeerInfo {
    optional bytes id = 1;
    repeated bytes addrs = 2;
  }

  message Dial {
    optional PeerInfo peer = 1;
  }

  message DialResponse {
    optional ResponseStatus status = 1;
    optional string statusText = 2;
    optional bytes addr = 3;
  }

  optional MessageType type = 1;
  optional Dial dial = 2;
  optional DialResponse dialResponse = 3;
}
```

The initiator uses the responses obtained from multiple peers to determine its
NAT status. If more than 3 peers report a successfully dialed address, the node
SHOULD assume that it is not located behind a NAT and publicly accessible. On
the other hand, if more than 3 peers report unsuccessful dials, the node SHOULD
assume that it is not publicly accessible.
Nodes are encouraged to periodically re-check their status, especially after
changing their set of addresses they're listening on.

## Security Considerations

Note that in the current iteration of this protocol, a node doesn't check if
a peer's report of a successful dial is accurate. This might be solved in a
future iteration of this protocol, see
https://github.com/libp2p/go-libp2p-autonat/issues/10 for a detailed discussion.
