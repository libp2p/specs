# gossipsub v1.3: Choke extensions to improve network efficiency

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r0, 2025-05-23  |

Authors: [@marcopolo]

Interest Group: TOOD

[@marcopolo]: https://github.com/marcopolo

See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Overview

This document specifies two new control messages, `Choke` and `Unchoke`, which
control whether mesh peers eagerly or lazily push messages to each other. A peer
is considered choked from the perspective of another peer if it has received a
`Choke` message from that peer. A choked peer is unchoked if it has received an
`Unchoke` message from that peer, or if it leaves that peer's mesh. Peers are
initially unchoked when grafted to a mesh

If there are no choked peers in the mesh, this version of gossipsub behaves
identically as the previous version of gossipsub. If the mesh only has choked
peers, this version behaves the identically as the previous version with an
additional network round trip of latency to fetch the message payload.

When choking is used well, messages arrive without extra delay and without
excessive duplicates. The graph of unchoked peers naturally evolves to utilize
better network paths.

## Prior work

- [Plumtree](https://www.dpss.inesc-id.pt/~ler/reports/srds07.pdf)
- [Episub](https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/episub.md)
- [Gossipsub extension for epidemic meshes](https://github.com/libp2p/specs/pull/413/files)

## Future sections:

TODO
- Piggybacking control messages
- Applicability to large messages (don't do this for small messages)
- Recommendations to implementations
  - Choke strategies
  - Scoring function changes
  - limiting concurrent IWANTs for the same message id

## Security Considerations

In the worst case, this introduces an extra round trip to propagate a message at
each hop. If an attacker could force the whole network to choke honest peers,
the time to dissemenate a message to all honest peers would increase by
$average_round_trip_between_honest_peers \times hops_to_reach_all_nodes$. Where
`hops_to_reach_all_nodes` is related to the network size and the mesh degree
$\log_{D}(\text{network_size})$. This attack requires significant setup, and
would only work once per setup as a peer will unchoke the honest node after
receiving the new message. The malicious nodes may also be downscored for their
misbehavior.
