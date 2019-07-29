# Simultaneous Open for multistream-select

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | DRAFT           |

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
as initiators. This is breaks protocol negotiation in
multistream-select, which assumes a single initator.

This draft proposes a simple extension to the multistream protocol
negotiation in order to select a single initator when both peers are
acting as such.

## The Protocol

When a peer acting as the initiator enters protocol negotiation, it
sends the string `iamclient` as first protocol selector. If the other
peers is a responder or doesn't support the extension, then it
responds with `na` and protocol negotiation continues as normal.

If both peers believe they are the initiator, then they both send
`iamclient`. If this is the case, they enter an initiator selection
phase, where one of the peers is selected to act as the initiator. In
order to do so, they both generate a random 256-bit integer and send
it as response to the `iamclient` directive. The peer with the highest
integer is selected to act as the initator and sends an `initiator`
message. The peer with the lowest integer responds with `responder`
message and both peers transition to protocol negotiation with a
distinct initiator.

The following schematic illustrates, for the case where A's integer is
higher than B's integer:

```
A ---> B: iamclient
B ---> A: iamclient
A: generate random integer IA
B: generate random integer IB
A ---> B: {IA}
B ---> A: {IB}
A ---> B: initiator
B ---> A: responder
```

In the unlikely case where both peers selected the same integer, they
generate a fresh one and enter another round of the protocol.

## Implementation Considerations

The protocol is simple to implement and is backwards compatible with
vanilla multistream-select.  In the common case of a single initiator,
we can ensure that there there is no latency overhead by sending the
`iamclient` message together with the multistream header.
