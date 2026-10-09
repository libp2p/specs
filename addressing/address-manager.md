# Address Manager

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r0, 2026-09-01  |

Authors: [@gmelodie]

Interest Group: TBD

[@gmelodie]: https://github.com/gmelodie

See the [lifecycle document][lifecycle-spec] for context about the maturity
level and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Table of Contents

- [Overview](#overview)
- [Terminology](#terminology)
- [Candidate model](#candidate-model)
  - [Sources](#sources)
  - [States](#states)
- [Address discovery](#address-discovery)
  - [Listen addresses and wildcard expansion](#listen-addresses-and-wildcard-expansion)
  - [Mappers](#mappers)
  - [Feeders](#feeders)
  - [Identify observations](#identify-observations)
  - [Explicitly announced addresses](#explicitly-announced-addresses)
- [Reachability confirmation](#reachability-confirmation)
  - [Verifier interface](#verifier-interface)
  - [Verification runs](#verification-runs)
  - [Verdict handling](#verdict-handling)
  - [AutoNAT v2 verifier](#autonat-v2-verifier)
- [The announce set](#the-announce-set)
- [Node-level reachability summary](#node-level-reachability-summary)
- [Lifecycle](#lifecycle)
- [Security considerations](#security-considerations)
- [Relation to other specs](#relation-to-other-specs)
- [Implementation status](#implementation-status)

## Overview

A libp2p node learns its own addresses from several independent sources: the
listen addresses that it binds, a port mapping from UPnP or NAT-PMP, a relay
reservation, an Identify observation, and the configuration of the host
operator. No source alone proves that a remote peer can dial the address. Today
each source lives in its own component, each one rewrites the announce list,
and the answers of AutoNAT per address collapse into one flag for the node.

This document specifies an **Address Manager**: one component at host level
that

1. owns every address that the node announces (the *announce path*),
2. separates *address discovery*, which is always on, from *reachability
   confirmation*, which is optional, and
3. delegates confirmation to a replaceable **Verifier** that works on one
   address at a time. The reference verifier uses AutoNAT v2.

Without a verifier, the address manager announces every candidate that it
discovers, thus a node that disables AutoNAT keeps the behaviour of today.

This document defines no message and no wire format, thus a node that adopts it
stays compatible with a node that does not. go-libp2p made the same split: it
moved its observed address manager into an [address pipeline][go-addrs-manager]
that also tracks [reachability][go-reachability].

## Terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be
interpreted as described in [RFC 2119].

[RFC 2119]: https://www.ietf.org/rfc/rfc2119.txt

- **Host**: the component that owns the transports, the services and the
  announce path. go-libp2p calls it the host, nim-libp2p calls it the switch,
  and rust-libp2p calls it the swarm.
- **Address manager**: the component that this document specifies. A host owns
  one of them.
- **Host operator**: the person who deploys and configures the node, and not a
  component. A value that "the host operator configures" comes from the
  configuration of the node, and not from the network.
- **Candidate**: an address that can make the node reachable, with its origin
  and with what the node knows about its reachability. The address manager
  holds the candidates in one table, and it announces from that table only.
- **Source**: the component or the mechanism that produces a candidate.
- **Mapper**: a function that transforms the current list of addresses into a
  new list of addresses (the existing `AddressMapper` concept).
- **Address policy**: the allow list, the deny list and the announce filters
  that the host operator configures. The address manager holds this policy.
- **Feeder**: a component that adds, updates or removes a candidate directly.
  It does not use the mapper chain.
- **Verifier**: a component that asks the network if one candidate is
  reachable.
- **Announce set**: the addresses that the node publishes in Identify, in
  signed peer records and in any other advertisement.
- **Observation**: the address that a remote peer reports in its Identify
  message. It is the address that the peer saw when the local node connected.
  An observation is not a candidate: it enters a separate ring, and the address
  manager derives candidates from that ring only when the host operator enables
  the derivation (see [Identify observations](#identify-observations)).

The names of the operations below (`add`, `verify`, `candidates` and the
others) show the behaviour, and they are not normative.

## Candidate model

The address manager keeps one candidate at most per multiaddress:

```
Candidate {
  address: MultiAddress
  sources: set<Source>   // every source currently producing this address
  state:   State
}
```

`sources` is a set, and not a single value. A port mapper and an Identify
observation often produce the same external address, and the address manager
MUST keep that address as one candidate. It removes a candidate when the last
source withdraws it.

Implementations MAY attach more data to a candidate, such as the time of the
last verification, a TTL or the dial-back peer.

### Sources

| Source       | Meaning                                                                     |
| ------------ | --------------------------------------------------------------------------- |
| `Listen`     | An address that the node binds, after wildcard expansion.                   |
| `Announced`  | A complete address that the host operator configures. It replaces the announce set. |
| `Upnp`       | An external mapping from UPnP.                                              |
| `NatPmp`     | An external mapping from NAT-PMP or PCP.                                    |
| `PortMapped` | An external mapping from a port mapper that does not report its protocol.   |
| `PublicIp`   | A public IP that the host operator gives to the port mapper. The port mapper builds an address from that IP and the mapped port. |
| `Circuit`    | A `/p2p-circuit` address from a relay reservation.                          |
| `Autonat`    | An address from the mapper of an AutoNAT service: a listen address that carries the observed external IP. |
| `Identify`   | A guess from Identify observations (see [Identify observations](#identify-observations)). |

Each source is **locally trusted** or **remote-derived**. The node itself
produces a locally trusted address, or a mechanism that the host operator
enables produces it: `Listen`, `Announced`, `Upnp`, `NatPmp`, `PortMapped`,
`PublicIp` and `Circuit`. A remote-derived address carries an IP that a remote
peer chose: `Identify`, and also `Autonat`, which puts that same observed IP
into a listen address. Implementations MAY add a source, and they MUST classify
each new one: a source whose value depends on a report from a remote peer is
remote-derived.

A candidate is **remote-only** when all of its sources are remote-derived. The
rules below apply to a remote-only candidate, thus a different label on an
observed IP MUST NOT relax them.

### States

| State         | Meaning                                                                    |
| ------------- | -------------------------------------------------------------------------- |
| `Unverified`  | No verifier gives a verdict on this address. This is the default.          |
| `Confirmed`   | A verifier proves that a remote peer can dial this address.                |
| `Unreachable` | A verifier proves that a remote peer cannot dial this address.             |

A candidate enters the table as `Unverified`. Only a verdict from a verifier
changes the state. A new source on a candidate MUST NOT change its state.

The state holds the latest verdict, and not a history of verdicts. Two verdicts
on one address disagree when the network changes or when a prover lies, and the
most recent one wins. Two rules limit the damage: a `Confirmed` verdict needs
proof that the dial-back arrived (see [AutoNAT v2
verifier](#autonat-v2-verifier)), and an `Unreachable` verdict on an announced
public address needs two peers (see [Verdict handling](#verdict-handling)).

## Address discovery

Discovery is always on, and it runs again each time that the host asks for new
addresses: a listen address changes, a service starts or stops, or a mapping
refreshes.

Each run follows this order:

1. The address manager expands the wildcards in the listen addresses. This step
   is not a mapper, and it runs first, thus each mapper sees a concrete
   address.
2. The address manager runs the registered mappers as a chain, in the order of
   registration, on the expanded listen addresses.
3. The address manager withdraws each `(address, source)` pair that the chain
   no longer produces.
4. The address manager adds the addresses that the host operator announces,
   with the source `Announced`.

Two inputs stay outside this order. A feeder acts at any time. Identify puts an
observation in the ring at any time, and the address manager derives candidates
from that ring in a verification run (see [Verification
runs](#verification-runs)).

### Listen addresses and wildcard expansion

Every listen address that the node binds enters the table with source `Listen`.

The address manager MUST expand a wildcard listen address (`/ip4/0.0.0.0/...`,
`/ip6/::/...`) into one address per network interface that matches and that is
up or loopback. It MUST keep the port and all trailing protocols (`/quic-v1`,
`/ws`, `/tls/ws`, and others). If the socket of an IPv6 wildcard accepts both
families, it MUST also expand that wildcard to the IPv4 interfaces. If the
socket carries the `IPV6_V6ONLY` option, it accepts IPv6 only, and the address
manager MUST NOT add an IPv4 address for it. An address that is not a wildcard
stays as it is.

### Mappers

Some components already implement an `AddressMapper`: port mapping, AutoRelay
and AutoNAT. Each one registers its mapper with the address manager, and gives
the `Source` that the output of the mapper carries:

```
addMapper(mapper: AddressMapper, source: Source)
removeMapper(mapper: AddressMapper)
```

Each address that a mapper outputs, and that was not in its input, becomes a
candidate with the `source` of that mapper.

The address manager MUST record which addresses the chain produced on the last
run, and which source produced each one. On the next run it MUST withdraw each
`(address, source)` pair that the chain no longer produces: it removes that
source from the candidate, and it deletes a candidate that has no source left.
A port mapper thus rewrites an address on refresh, and a lost relay reservation
drops its circuit address, without either component knowing about candidates.

Withdrawal removes only the sources that the chain produced. A candidate keeps
the source of a feeder that added it directly.

### Feeders

A component that does not fit the mapper shape uses the direct entry points:

```
add(address, source)   -> bool   // true when the candidate is new
update(address, state) -> bool   // true when the candidate exists
remove(address)        -> bool   // true when the candidate existed
```

`add` on a candidate that exists only adds the source. `remove` deletes the
candidate, whatever the number of its sources. A feeder that shares an address
with a mapper SHOULD let the mapper withdraw it.

### Identify observations

Identify gives each `observedAddr` that it receives to the address manager,
with the peer that reports it:

```
addObservation(observed, reporter) -> bool
```

The address manager MUST reject an observation that no remote peer can see for
the local node: an address without an IP and a transport, a relayed address,
and a wildcard or multicast IP. It accepts a loopback address and a private
address, because a peer on the same host or on the same LAN did reach the node
there.

Each accepted observation enters a ring of `maxSize` entries (RECOMMENDED
default 10) that evicts the oldest. The ring MUST hold one entry at most per
peer that reports, thus a new observation replaces the entry of its own peer.

From the ring the address manager derives the *most observed* address per IP
family: the IP (or the IP with its transport and port) that at least `minCount`
distinct peers report (RECOMMENDED default 3). Below the threshold a family has
no most observed address. This gives two queries:

- `mostObservedAddrs()`: the most observed `ip4/.../port` address and the most
  observed `ip6/.../port` address.
- `externalAddrFor(listenAddr)`: `listenAddr` that carries the most observed IP
  of its family, or `listenAddr` as it is.

To make candidates from observations is OPTIONAL, and it is off by default.
When it is on, each verification run adds each `externalAddrFor(listenAddr)`
that differs from its listen address, and each address from
`mostObservedAddrs()`, with the source `Identify`.

A verifier that finds a remote-only candidate `Unreachable` removes it (see
[Verdict handling](#verdict-handling)) and quarantines the address, thus the
next runs do not add it again. The quarantine MUST expire (RECOMMENDED: after a
fixed number of verification runs, default 12), thus a wrong verdict heals. The
address manager MUST cap the quarantine at `maxQuarantine` entries (RECOMMENDED
default 10), and it MUST evict the oldest entry when the quarantine is full.

### Explicitly announced addresses

An address that the host operator configures (`announcedAddrs`) enters the
table with source `Announced`, and the address manager verifies it like each
other candidate. A verdict on such an address changes the confirmed addresses
and the reachability summary, and never the announce set.

If the host operator configures one announced address or more, the announce set
MUST be exactly that list, after the policy filter. The mapper chain still runs,
thus the node establishes its port mappings and its relay reservations.

## Reachability confirmation

Confirmation is optional, and it needs a registered verifier. The address
manager holds at most one verifier, thus two verifiers never give a verdict on
the same address. Without a verifier, each candidate keeps the state
`Unverified`, and the address manager does not contact the network.

### Verifier interface

```
verify(address) -> Verdict          // asynchronous, cancellable
```

The address manager asks a verifier about one address at a time. The verifier
returns one of three verdicts:

- `Confirmed` when a remote peer proves that it dialed the address,
- `Unreachable` when a remote peer proves that it could not dial the address,
- `Undecided` when it concludes nothing: there is no suitable peer, a timeout
  occurs, the answer is ambiguous, the peer does not support the transport, or
  the node reaches a resource limit.

`Undecided` MUST leave the current state as it is. A verifier MUST be
cancellable, and a verification that the address manager cancels MUST NOT
change a state.

The host MAY replace or remove the verifier while the node runs. The address
manager MUST cancel each verification that is in flight before it installs the
next verifier, and it MUST drop a verdict that the replaced verifier returns
after that point.

When the host removes the verifier, verification stops. The address manager
keeps the states that it already assigned, until the chain withdraws the
candidate or the address manager stops.

### Verification runs

The address manager runs verification on a heartbeat with the period
`verifyInterval` (RECOMMENDED default 5 minutes). Each run does these steps:

1. It expires each quarantined guess whose term is complete.
2. It derives the `Identify` candidates from the observation ring, when this is
   on.
3. It selects the candidates to verify. A candidate qualifies when the address
   policy accepts it and when it is **not** relayed, because no AutoNAT server
   dials back a circuit address.
4. It verifies them one at a time, and it takes the candidate whose last
   verification is the oldest first. A candidate that no verifier saw counts as
   the oldest. It stops when all are done, or when it spends `verifyTimeout`,
   the budget of the run (RECOMMENDED default 2 minutes). The next run starts
   with the candidates that this run did not reach.
5. It applies the verdicts. If a state changes, it computes the announce set
   again, and it triggers the address-change notification of the host.
6. It computes the [reachability summary](#node-level-reachability-summary)
   again, and it notifies the observers when the summary changes. It does this
   also when no verdict arrives, because a withdrawal can change the summary.

A run MUST NOT verify in a fixed table order. The budget of a run is often
smaller than the table, and a fixed order then never reaches the tail.

Two runs MUST NOT overlap. The address manager ignores a request to run now
while a run is in progress, and the run in progress keeps the dial-backs that
it awaits. A caller MAY request an immediate run (`triggerVerification`), and
an implementation SHOULD request one when a new peer becomes available and the
summary is `Unknown`. A change to the verifier or to the interval restarts the
heartbeat, thus the change applies now and not at the next wake-up.

An implementation SHOULD limit the number of dial requests in flight, and it
MUST NOT send a second request for an address that already has one in flight.

### Verdict handling

`applyVerdict(address, state)`:

- If the candidate no longer exists, because the chain withdrew it during the
  run, the address manager drops the verdict.
- If the candidate is remote-only and the verdict is `Unreachable`, the address
  manager removes the candidate and quarantines the address (see above).
- In the other cases, the address manager updates the state. Confirmation
  changes only the state, and it never removes a candidate.

A `Confirmed` verdict proves itself, because the verifier saw the dial-back
arrive. An `Unreachable` verdict is only the word of the peer that the verifier
asked, and it removes an address from the announce set, thus one hostile prover
can hide an address that works. Before the address manager marks a locally
trusted public candidate `Unreachable`, it SHOULD get that verdict from two
different peers. After a single refutation the state stays as it is, and the
next run asks another peer. A remote-only candidate needs no second peer,
because the address manager never announced it.

Later runs heal a wrong verdict of either type.

### AutoNAT v2 verifier

The reference verifier uses [AutoNAT v2][autonat-v2]:

1. If the host has no free slot for an incoming connection, the verifier MUST
   refuse to verify, and it returns `Undecided`. A dial-back that succeeds
   needs one such slot.
2. It selects a random peer among the peers that the local node dialed on an
   outbound connection. That peer MUST hold no inbound connection to the local
   node, because a peer that already reached the node proves nothing about a
   new dial. If there is no such peer, the verifier returns `Undecided`.
3. It sends one `DialRequest` that carries exactly the one candidate. AutoNAT
   v2 gives the client no way to learn the timeout of the server, thus the
   client MUST apply a timeout of its own (RECOMMENDED default 30 seconds).
4. It maps the response. `OK` becomes `Confirmed`, but only if the dial-back
   nonce of that request arrived on the address under test. An `OK` without the
   matching nonce MUST give `Undecided`, because a server that lies can answer
   `OK` for an address that it never dialed. A dial error (`E_DIAL_ERROR`,
   `E_DIAL_BACK_ERROR`) becomes `Unreachable`. A refusal, a timeout, a
   transport that the peer does not support, and each protocol error give
   `Undecided`.

An implementation MAY put guesses of lower priority in the same request as the
address under test, because AutoNAT v2 permits it. It MUST then attribute the
verdict to the address that the server reports as dialed.

[autonat-v2]: https://github.com/libp2p/specs/blob/master/autonat/autonat-v2.md

## The announce set

The address manager installs itself as the first `AddressMapper` of the
`PeerInfo` of the host, and it resolves the announce set in one pass:

1. It runs [address discovery](#address-discovery).
2. If the host operator configures announced addresses, it returns them and it
   stops.
3. If not, it takes each candidate from the chain and then each candidate from
   a feeder, and it removes the duplicates. It keeps an address when:
   - the state is `Confirmed`; or
   - the state is `Unverified` and the candidate is not remote-only; or
   - the state is `Unreachable` and the address is **not** public. A remote
     peer that fails to dial a LAN address proves nothing for the peers on that
     LAN.

   It drops an address that is a *redundant relay*: a `/p2p-circuit` address
   whose IP family already has one `Confirmed` public candidate that is not
   relayed. A confirmed private address does not count, because it proves only
   LAN reachability.
4. It applies the address policy to the result. It applies the same policy when
   it selects the candidates of a verification run, thus it never gives a
   filtered address to a verifier.

A public address with the state `Unreachable` stays in the table, thus the
address manager verifies it again and the address can heal. It does not
announce that address.

The host MUST notify the address observers (identify-push, the refresh of the
signed peer record) when the announce set changes. The host SHOULD group the
notifications of a short window (RECOMMENDED default 1 second) into one.

Queries:

- `candidates()`: the full table, for diagnostics and for advanced consumers.
- `confirmedAddrs()`: the addresses with the state `Confirmed`. A consumer that
  needs the detail per family, such as hole punching or AutoRelay, SHOULD use
  this query and not the summary below.

The result of `confirmedAddrs()` is empty while no verifier runs. The address
manager MUST let a consumer tell that case apart from an empty result under a
running verifier. A consumer MUST read the first case as "no information", and
not as "the node is not reachable", and it SHOULD fall back to the announce
set.

## Node-level reachability summary

For a consumer that needs one flag, the address manager computes a read-only
summary from the states of the addresses. It never stores the summary as truth:

| Condition                                                                | Summary        |
| ------------------------------------------------------------------------ | -------------- |
| any candidate is `Confirmed`                                             | `Reachable`    |
| else any candidate is `Unreachable`, or a remote-only guess is quarantined | `NotReachable` |
| else                                                                     | `Unknown`      |

A quarantined guess is evidence: it is no longer a candidate, but it did record
a dial-back that failed.

The address manager notifies its reachability observers from the verification
heartbeat, each time that the summary differs from the last value that it
notified. More than one component consumes this summary, thus the address
manager MUST accept more than one observer, and it MUST record the new value
before it calls the first one. An AutoNAT service that computed its own
confidence from a window of verdicts SHOULD now pass this summary to its
observers.

## Lifecycle

The host owns the address manager. It constructs the address manager before
Identify, and it passes the address manager to Identify by reference.

- **start**: the host binds its transports, installs the mapper of the address
  manager on its `PeerInfo`, starts the address manager, and then starts the
  services. Each service registers its mappers, its feeders and its verifier
  when it starts.
- **stop**: each service unregisters when it stops. The host then stops the
  address manager, which cancels the heartbeat and each verification in flight,
  clears the observations, the candidates, the records of the chain, the
  mappers, the reachability observers and the quarantine, and removes its
  mapper from `PeerInfo`. A call to stop MUST be safe before start, and it MUST
  be safe more than one time. A mapper that an owner registers before stop is
  gone after stop, and the owner registers it again on its next start.
- `addObservation` on an address manager that stopped returns false, and it
  records nothing.

The thresholds (`maxSize`, `maxQuarantine`, `minCount`) and the times of the
verification (`verifyInterval`, `verifyTimeout`) are configuration of the host.
A value below 1 MUST become 1.

## Security considerations

- **An attacker controls the observations.** A remote peer selects what it
  reports as `observedAddr`. One peer holds one ring slot and counts one time
  towards `minCount`, thus an attacker needs `minCount` distinct peer
  identities that the node dialed or accepted. Sybil identities are cheap in
  libp2p, thus this raises the cost of the attack and does not remove it. What
  keeps an unproven guess out of the announce set is the rule that a
  remote-only candidate waits for a verifier.
- **Cost of a guess that succeeds.** A guess that passes the threshold costs
  the node one dial request per run, until a verdict arrives. The derivation
  produces one address at most per listen address, plus one per IP family, thus
  the requests per run grow with the listen addresses and not with the hostile
  peers. An implementation SHOULD cap the remote-only candidates that it
  verifies in one run.
- **Growth of the table.** Each set that remote input fills has a limit: the
  ring holds `maxSize` entries, one per peer; the quarantine holds
  `maxQuarantine` entries; the derivation gives one candidate per listen
  address per family.
- **Amplification of the verification.** The address manager asks for a
  dial-back only to an address that it believes is its own. It sends one
  address per request, one request at a time, inside the budget of the run, and
  it refuses when it has no free slot for an incoming connection. The defences
  on the AutoNAT v2 server stay in force.
- **Choice of the prover.** A peer that already holds an inbound connection
  gives a positive answer that proves nothing, thus the reference verifier
  excludes it. Each other peer is arbitrary, thus the verifier accepts
  `Confirmed` only against the dial-back nonce, and it needs a second peer for
  `Unreachable` on an announced address.
- **A working address that an attacker hides.** An `Unreachable` verdict
  removes a public address from the announce set, thus a hostile prover that
  answers `E_DIAL_ERROR` can hide the node. Two peers must agree, and the
  address manager verifies again at each `verifyInterval`. This limits the
  attack to an attacker that controls a large part of the peers that the node
  dials.
- **Announcement of an unreachable address.** The node keeps a private address
  with the state `Unreachable` in the announce set. This is the design: the
  peer that the verifier asked was never a valid prover for that address.

## Relation to other specs

- [Identify][identify]: the only source of observations. It also consumes the
  announce set, for `listenAddrs` and for identify-push.
- [AutoNAT v2][autonat-v2]: the transport of the reference verifier.
- [Circuit Relay v2][relay-v2]: the source of the `Circuit` candidates.
- [Signed peer records][peer-records]: the node builds them again when the
  announce set changes.

[identify]: https://github.com/libp2p/specs/blob/master/identify/README.md
[relay-v2]: https://github.com/libp2p/specs/blob/master/relay/circuit-v2.md
[peer-records]: https://github.com/libp2p/specs/blob/master/RFC/0003-routing-records.md
[go-addrs-manager]: https://github.com/libp2p/go-libp2p/blob/master/p2p/host/basic/addrs_manager.go
[go-reachability]: https://github.com/libp2p/go-libp2p/blob/master/p2p/host/basic/addrs_reachability_tracker.go

## Implementation status

nim-libp2p ([roadmap item][roadmap]):

- [vacp2p/nim-libp2p#2924](https://github.com/vacp2p/nim-libp2p/pull/2924): the
  switch owns the observed address manager
- [vacp2p/nim-libp2p#2928](https://github.com/vacp2p/nim-libp2p/pull/2928): the
  address manager owns every announced address
- [vacp2p/nim-libp2p#2934](https://github.com/vacp2p/nim-libp2p/pull/2934): a
  verifier confirms candidates on a heartbeat
- [vacp2p/nim-libp2p#2953](https://github.com/vacp2p/nim-libp2p/pull/2953): the
  address manager registers the verifier, and the consumers move to it

[roadmap]: https://roadmap.vac.dev/p2p/ift/2026q3-nimlibp2p-addr-manager
