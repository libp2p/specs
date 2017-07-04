# RFC: Proximity Aware Epidemic PubSub

<!-- toc -->

- [Introduction](#introduction)
- [Membership Management Protocol](#membership-management-protocol)
- [Broadcast Protocol](#broadcast-protocol)
- [Protocol Messages](#protocol-messages)

<!-- tocstop -->

## Introduction

This RFC proposes a topic pubsub protocol based on the following papers:
1. [Epidemic Broadcast Trees](http://www.gsd.inesc-id.pt/~ler/docencia/rcs1617/papers/srds07.pdf)
2. [HyParView: a membership protocol for reliable gossip-based broadcast](http://asc.di.fct.unl.pt/~jleitao/pdf/dsn07-leitao.pdf)
3. [GoCast: Gossip-enhanced Overlay Multicast for Fast and Dependable Group Communication](http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.75.4811)

The protocol implements the `Plumtree` algorithm from [1], with
membership managed using `HyParView` [2] and proximity-aware overlay
construction based on the scheme proposed in `GoCast`[3]. The marrying
of proximity awareness from `GoCast` with `Plumtree` was suggested by
the original authors of `Plumtree` in [1].

The protocol has two distinct components: the membership management
protocol (subscribe) and the brodcast protocol (publish).

The membership management protocol (Peer Sampling Service in [1])
maintains two lists of peers that are subscribed to the topic.  The
_active_ list contains peers with currently active broadcast
connections. The _passive_ list is a partial view of the overlay at
large, and is used for directing new joins, replacing failed peers in
the active list and optimizing the overlay.

The broadcast protocol lazily constructs and optimizes a multicast
tree using epidemic broadcast. The peer splits the active list into
two sets of peers: the _eager_ peers and the _lazy_ peers. The eager
peers form the edges of the multicast tree, while the lazy peers
form a gossip mesh supporting the multicast tree.

When a new message is broadcast, it is pushed to the eager
peers, while lazy peers only receive message summaries and have to
pull missing messages.  Initially, all peers in the active list are
eager forming a connected mesh.  As messages propagate, peers _prune_
eager links when receiving duplicate messages, thus constructing a
multicast tree. The tree is repaired when peers receive lazy messages
that were not propagated via eager links by _grafting_ an eagler link
on top of a lazy one.

In steady state, the protocol optimizes the multicast tree in two
ways. Whenever a message is received via both an eager link and a
lazy message summary, its hop count is compared. When the eager
transmission hop count exceeds the lazy hop count by some threshold,
then the lazy link can replace the eager link as a tree edge, reducing
latency as measured in hops.  In addition, active peers may be
periodically replaced by passive peers with better network proximity,
thus reducing propagation latency in time.

## Membership Management Protocol


## Broadcast Protocol


## Protocol Messages