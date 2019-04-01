# proposal: connection manager v2

Revision: r0; 2019-04-01 author: @raulk

_NOTE: code listings are Go-style pseudo-code_

**Contents**

{{TOC}}

## motivation

Resource management is an essential, cross-cutting concern for all libp2p
components. Physical resources subject to management include file descriptor
usage, bandwidth, memory, cpu, etc. Management can take place in a reactive or
proactive fashion. While hard limit enforcement can be delegated to the
environment, judicious resource usage/pressure remains a responsiblity of
libp2p itself.

Generally speaking, we consider the responsibilities of resource management to
include at least:

* global resource pool modelling.
* declaration and management of usage quotas.
* quota usage supervision and regulation, either:
    * proactively: by having consumers check out resources when needed, and
      returning them when done.
    * reactively: by monitoring usage and taking compensating and rebalancing
      actions upon breach of quota.
* optimal resource control decision-taking.
* resource allocation observability.

In libp2p, the primary object of resource management is the libp2p
_Connection_: it's the main driver behind consumption of physical resources
within the libp2p networking stack.

## scope and rationale

This spec focuses on **connection management** as an instrument for attaining
effective resource management.

The variable we seek to control and optimise is *connection count*. Keeping
*connection count* in check is critical for various reasons:

1. avoiding file descriptor exhaustion.
2. averting router overload.
3. balancing network bandwidth allocation (avoiding starvation).

Future versions of this spec could introduce new variables to optimise for. In
fact, we believe there is room to evolve the connection manager into a
fully-fledged *traffic shaper*.

### a brief review of history

Prior to introducing any notion of connection management, libp2p nodes would
not restrict the amount of connections they established with peers in any
manner.

As a result, libp2p would readily send routers into overdrive, causing silent
connection droppage, router freeze, unannounced reboots, TCP RST storms,
amongst other issues. This matter became so infamous it received a name:
"killing the routers" [1].

We introduced connection manager v1 as the minimal working solution to curtail
this issue. While it accomplished its purpose, the lack of a bounded scoring
domain, connection locking, whitelisting, and others features, ended up
causing a number of downstream problems.

Version 2 proposed herein offers richer semantics and new algorithmic
approaches to fix those issues.

Note that, in the future, we expect the connection manager v2 to devolve onto
more pervasive and proactive resource management checkpoints and techniques
across the libp2p stack.

## high-level description of connmgr v2

This section provides a high-level walkthrough of the concepts and semantics
of connection manager v2, in a narrative style. We delve into the details of
each element in subsequent sections.

In connection manager v2, protocols enroll with the connection manager (from
now on, *connmgr* — refers to the construct, not the spec), and they request a
*quota allocation* of the *global share*. The quota can be specified in
absolute or relative terms (e.g. connection range 10-50, or connection range
5%-10%). The connmgr can accept these terms or propose alternative ones, in
which case the protocol is expected to adjust to the proposed boundaries.

The *global share* can be set programmatically, or can be inferred via
*environment sensing*. A hybrid of both is possible, where an initial limit is
set, and it's adjusted adaptively based on signals received from the
environment.

*Scoring* of connections and streams is overhauled in connection manager v2.
Protocols register Scorer functions when they enroll with the connmgr. During
a *regulation round*, the connmgr invokes the individual scorers to decide
which connections to prune.

*Regulation rounds* execute an *arbitration algorithm*. The connmgr finds the
most offending protocols and its streams, and decides which connections to
kill based on a tally of scores across using those connections.

Regulation kicks in reactively, upon certain system conditions becoming true
(e.g. connection count beyond a threshold, new connection spike, too many
failed dials, etc.) The triggering criteria is configurable.

Protocols can now *lock* streams temporarily, and the connmgr may accept or
deny the request. During the lifetime of a lock, the connection containing the
stream is protected from pruning. Locks may be revoked early by notifying the
holder through a callback function.

Many protocols have bursting behaviour, e.g. the DHT. *Bursting* is now
modelled explicitly. A *Burst* is a transaction-like object on which streams
are enlisted. It conveys high preference for pruning all stream/connections
within it once the *Burst* is over. The connmgr visits recently-closed Bursts
first during its *regulation rounds*.

## quota allocation

TK

## protocol enrollment

TK

## stream scoring

TK

## locking

TK

## bursting

TK

## regulation procedure

TK

## environment sensing

TK

## observability

TK
