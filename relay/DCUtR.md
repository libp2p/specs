# Direct Connection Upgrade through Relay

| Lifecycle Stage | Maturity      | Status | Latest Revision    |
|-----------------|---------------|--------|--------------------|
| 1A              | Working Draft | Active | DRAFT, 2019-05-29  |

Authors: [@vyzo]

Interest Group: [@raulk], [@stebalien], [@whyrusleeping]

[@vyzo]: https://github.com/vyzo
[@raulk]: https://github.com/raulk
[@stebalien]: https://github.com/stebalien
[@whyrusleeping]: https://github.com/whyrusleeping

See the [lifecycle document](https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md)
for context about maturity level and spec status.

## Introduction

NAT traversal is a quintessential problem in peer-to-peer networks.

We currently utilize relays, which allow us to traverse NATs by using
a third party as proxy. Relays are a reliable fallback, that can
connect peers behind NAT albeit with a high-latency, low-bandwidth
connection.  Unfortunately, they are expensive to scale and maintain
if they have to carry all the NATed node traffic in the network.

It is often possible for two peers behind NAT to communicate directly
by utilizing a technique called _hole punching_[1]. The technique
relies on the two peers synchronizing and simultaneously opening
connections to each other to their predicted external address. It
works well for UDP, with an estimated 80% success rate, and reasonably
well for TCP, with an estimated 60% success rate.

The problem in hole punching, apart from not working all the time, is
the need for rendezvous and synchronization. This is usually
accomplished using dedicated signaling servers [2].  However, this
introduces yet another piece of infrastructure, while still requiring
the use of relays as a fallback for the cases where a direct
connection is not possible.

In this draft, we describe a synchronization protocol for direct
connectivity with hole punching that eschews signaling servers and
utilizes existing relay connections instead.  That is, peers start
with a relay connection and synchronize directly, without the use of a
signaling server.  If the hole punching attempt is successful, the
peers _upgrade_ their connection to a direct connection and they can
close the relay connection.  If the hole punching attempt fails, they
can keep using the relay connection as they were.

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

If the unilateral connection upgrade attempt fails or if `A` is itself a NATed peer that
doesn't advertise public address, then `B` initiates the direct connection
upgrade protocol as follows:
1. `B` opens a stream to `A` using the `/libp2p/connect` protocol
2. `B` sends to `A` a `Connect` message containing its observed (and possibly predicted)
   addresses from identify and starts a timer to measure RTT of the relay connection.
3. Upon receving the `Connect`, `A` responds back with a `Connect` message containing
   its observed (and possibly predicted) addresses.
4. Upon receiving the `Connect`, `B` sends a `Sync` message and starts a timer for
   half the RTT measured from the time between sending the initial `Connect` and receiving
   the response.
5. Simultaneous Connect
   - Upon receiving the `Sync`, `A` immediately starts a direct dial to B using the addresses
     obtained from the `Connect` message.
   - Upon expiry of the timer, `B` starts a direct dial to `A` using the addresses obtained
     from the `Connect` message.

The purpose of the `Sync` message and `B`'s timer is to allow the two peers to synchronize
so that they perform a simultaneous open that allows hole punching to succeed.

If the direct connection is successful, then the peers should migrate
to it by prioritizing over the existing relay connection. All new
streams should be opened in the direct connection, while the relay
connection should be closed after a grace period.  Existing indefinite
duration streams will have to be recreated in the new connection once
the relay connection is closed.  This can be accomplised by observing
network notifications: the new direct connection will emit a new
`Connected` notification, while closing the relay connection will
sever existing streams and emit `Disconnected` notification.


### Protobuf

TBD

## Implementation Considerations

There are some difficulties regarding implementing the protocol, at least in `go-libp2p`:
- the swarm currently has no mechanism for direct dials in the presence of existing connections,
  as required by the upgrade protocol.
- the swarm has no logic for prioritizing direct connections over relay connections
- the current multistream select protocol is an interactive protocol that requires a single
  initiator, which breaks with simultaneous connect as it can result in both peers having outbound
  connections to each other.

All of these will have to be addressed in order to implement the protocol. The first two
are perhaps simple implementation details, but the multistream problem is hard to resolve.
Perhaps we will have to upgrade to `multistream-select/2.0`, which has explicit mechanisms
for handling simultaneous connect, before we can deploy the protocol.


## References

1. Peer-to-Peer Communication Across Network Address Translators. B. Ford and P. Srisuresh.
   https://pdos.csail.mit.edu/papers/p2pnat.pdf
2. Interactive Connectivity Establishment (ICE): A Protocol for Network Address Translator (NAT) Traversal for Offer/Answer Protocols. IETF RFC 5245.
   https://tools.ietf.org/html/rfc5245
