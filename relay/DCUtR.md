# Direct Connection Upgrade through Relay

| Lifecycle Stage | Maturity      | Status | Latest Revision    |
|-----------------|---------------|--------|--------------------|
| 1A              | Working Draft | Active | r1, 2021-11-20     |

Authors: [@vyzo]

Interest Group: [@raulk], [@stebalien], [@whyrusleeping], [@mxinden], [@marten-seemann]

[@vyzo]: https://github.com/vyzo
[@raulk]: https://github.com/raulk
[@stebalien]: https://github.com/stebalien
[@whyrusleeping]: https://github.com/whyrusleeping
[@mxinden]: https://github.com/mxinden
[@marten-seemann]: https://github.com/marten-seemann

See the [lifecycle document](https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md)
for context about maturity level and spec status.

## Table of Contents

- [Direct Connection Upgrade through Relay](#direct-connection-upgrade-through-relay)
    - [Table of Contents](#table-of-contents)
    - [Introduction](#introduction)
    - [The Protocol](#the-protocol)
        - [RPC messages](#rpc-messages)
    - [FAQ](#faq)
    - [References](#references)

## Introduction

NAT traversal is a quintessential problem in peer-to-peer networks.

We currently utilize relays, which allow us to traverse NATs by using
a third party as proxy. Relays are a reliable fallback, that can
connect peers behind NAT albeit with a high-latency, low-bandwidth
connection.  Unfortunately, they are expensive to scale and maintain
if they have to carry all the NATed node traffic in the network.

It is often possible for two peers behind NAT to communicate directly by
utilizing a technique called _hole punching_[1]. The technique relies on the two
peers synchronizing and simultaneously opening connections to each other to
their predicted external address. It works well for UDP, and reasonably well for
TCP.

The problem in hole punching, apart from not working all the time, is
the need for rendezvous and synchronization. This is usually
accomplished using dedicated signaling servers [2].  However, this
introduces yet another piece of infrastructure, while still requiring
the use of relays as a fallback for the cases where a direct
connection is not possible.

In this specification, we describe a synchronization protocol for direct
connectivity with hole punching that eschews signaling servers and utilizes
existing relay connections instead. That is, peers start with a relay connection
and synchronize directly, without the use of a signaling server. If the hole
punching attempt is successful, the peers _upgrade_ their connection to a direct
connection and they can close the relay connection. If the hole punching attempt
fails, they can keep using the relay connection as they were.

## The Protocol

Consider two peers, `A` and `B`. `A` wants to connect to `B`, which is
behind a NAT and advertises relay addresses. `A` may itself be behind
a NAT or be a public node.

The protocol starts with the completion of a relay connection from `A`
to `B`.  Upon observing the new connection, the inbound peer (here `B`)
checks the addresses advertised by `A` via identify. If that set
includes public addresses, then `A` _may_ be reachable by a direct
connection, in which case `B` attempts a unilateral connection upgrade
by initiating a direct connection to `A`.

If the unilateral connection upgrade attempt fails or if `A` is itself a NATed
peer that doesn't advertise public address, then `B` initiates the direct
connection upgrade protocol as follows:
1. `B` opens a stream to `A` using the `/libp2p/dcutr` protocol.
2. `B` sends to `A` a `Connect` message containing its observed (and possibly
   predicted) addresses from identify and starts a timer to measure RTT of the
   relay connection.
3. Upon receving the `Connect`, `A` responds back with a `Connect` message
   containing its observed (and possibly predicted) addresses.
4. Upon receiving the `Connect`, `B` sends a `Sync` message and starts a timer
   for half the RTT measured from the time between sending the initial `Connect`
   and receiving the response. The purpose of the `Sync` message and `B`'s timer
   is to allow the two peers to synchronize so that they perform a simultaneous
   open that allows hole punching to succeed.
5. Simultaneous Connect. The two nodes follow the steps below in parallel for
   every address obtained from the `Connect` message:
   - For a TCP address:
      - Upon receiving the `Sync`, `A` immediately dials the address to `B`.
      - Upon expiry of the timer, `B` dials the address to `A`.
      - This will result in a TCP Simultaneous Connect. For the purpose of all
        protocols run on top of this TCP connection, `A` is assumed to be the
        client and `B` the server.
   - For a QUIC address:
      - Upon receiving the `Sync`, `A` immediately dials the address to `B`.
      - Upon expiry of the timer, `B` starts to send UDP packets filled with
        random bytes to `A`'s address. Packets should be sent repeatedly in
        random intervals between 10 and 200 ms.
      - This will result in a QUIC connection where `A` is the client and `B` is
        the server.
6. Once a single connection has been established, `A` SHOULD cancel all
   outstanding connection attempts. The peers should migrate to the established
   connection by prioritizing over the existing relay connection. All new
   streams should be opened in the direct connection, while the relay connection
   should be closed after a grace period. Existing long-lived streams
   will have to be recreated in the new connection once the relay connection is
   closed.

   On failure of all connection attempts go back to step (1). Inbound peers
   (here `B`) SHOULD retry twice (thus a total of 3 attempts) before considering
   the upgrade as failed.

### RPC messages

All RPC messages sent over a stream are prefixed with the message length in
bytes, encoded as an unsigned variable length integer as defined by the
[multiformats unsigned-varint spec][uvarint-spec].

Implementations SHOULD refuse encoded RPC messages (length prefix excluded)
larger than 4 KiB.

RPC messages conform to the following protobuf schema:

```proto
syntax = "proto2";

package holepunch.pb;

message HolePunch {
  enum Type {
    CONNECT = 100;
    SYNC = 300;
  }

  required Type type=1;

  repeated bytes ObsAddrs = 2;
}
```

`ObsAddrs` is a list of multiaddrs encoded in the binary multiaddr
representation. See [Addressing specification] for details.

## FAQ

- *Why exchange `CONNECT` and `SYNC` messages once more on each retry?*

  Doing an additional CONNECT and SYNC for each retry prevents a flawed RTT
  measurement on the first attempt to distort all following retry attempts.

## References

1. Peer-to-Peer Communication Across Network Address Translators. B. Ford and P.
   Srisuresh. https://pdos.csail.mit.edu/papers/p2pnat.pdf
2. Interactive Connectivity Establishment (ICE): A Protocol for Network Address
   Translator (NAT) Traversal for Offer/Answer Protocols. IETF RFC 5245.
   https://tools.ietf.org/html/rfc5245

[uvarint-spec]: https://github.com/multiformats/unsigned-varint
[Addressing specification]: ../addressing/README.md
