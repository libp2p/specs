# Simultaneous Open for bootstrapping connections in multistream-select

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r0, 2021-05-07  |

Authors: [@vyzo]

Interest Group: [@raulk], [@stebalien]

[@vyzo]: https://github.com/vyzo
[@raulk]: https://github.com/raulk
[@stebalien]: https://github.com/stebalien

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md


## Introduction

In order to support direct connections through NATs with hole
punching, we need to account for simultaneous open. In such cases,
there is no single initiator and responder, but instead both peers act
as initiators. This breaks protocol negotiation in
multistream-select, which assumes a single initator.

This draft proposes a simple extension to the multistream protocol
negotiation in order to select a single initator when both peers are
acting as such.

## The Protocol

When a peer acting as the initiator enters protocol negotiation, it sends the
string `/libp2p/simultaneous-connect` as first protocol selector. If the other
peers is a responder or doesn't support the extension, then it responds with
`na` and protocol negotiation continues as normal.

If both peers believe they are the initiator, then they both send
`/libp2p/simultaneous-connect`. If this is the case, they enter an initiator
selection phase, where one of the peers is selected to act as the initiator. In
order to do so, they both generate a random 64-bit integer and send it as
response to the `/libp2p/simultaneous-connect` directive, prefixed with the
`select:` string. The integer is sent in its base-10 string representation. The
peer with the highest integer is selected to act as the initator and sends an
`initiator` message. The peer with the lowest integer responds with `responder`
message and both peers transition to protocol negotiation with a distinct
initiator.

Note the importance of the prefix in the random integer, as it allows
peers to match the selection token and ignore potentially pipelined
security protocol negotiation messages.

The following schematic illustrates, for the case where A's integer is
higher than B's integer:

```
A ---> B: /libp2p/simultaneous-connect
B ---> A: /libp2p/simultaneous-connect
A: generate random integer IA
B: generate random integer IB
A ---> B: select:{IA}
B ---> A: select:{IB}
A ---> B: initiator
B ---> A: responder
```

In the unlikely case where both peers selected the same integer, connection
establishment fails.

## Implementation Considerations

The protocol is simple to implement and is backwards compatible with vanilla
multistream-select. An important consideration is avoiding RTT overhead in the
common case of a single initiator. In this case, the initiator pipelines the
security protocol negotiation together with the selection, sending
`multistream,/libp2p/simultaneous-connect,secproto`. If the receiving peer is a
responder, then it replies with `multistream,na,secproto`, negotiating the
security protocol without any overhead.

If the peer is also a client, then it also sends
`multistream,/libp2p/simultaneous-connect,secproto`. On seeing the
`/libp2p/simultaneous-connect` message, both peers enter the initiator selection
protocol and ignore the `secproto` in the original packet. They can do so
because the random integer is prefixed with the `select:` string, allowing peers
to match the selection and ignore pipelined protocols.
