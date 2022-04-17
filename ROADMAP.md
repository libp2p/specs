# Roadmap

The libp2p project is creating a set of modular, loosely-coupled building blocks
(based on a shared core) for modern peer-to-peer networking. Our goal is to
enable a new generation of decentralized applications in which network nodes are
full peers, providing and consuming data, and routing traffic for one another,
all without the need for centralized infrastructure points or reliance on
third-party ownership of data.

**Table of Contents**

- [Roadmap](#roadmap)
    - [Visionary](#visionary)
        - [🖧 Decentralizing networks](#🖧-decentralizing-networks)
        - [🤫 A spyproof libp2p](#🤫-a-spyproof-libp2p)
        - [📱 libp2p in mobile devices](#📱-libp2p-in-mobile-devices)
        - [💡 libp2p in IoT](#💡-libp2p-in-iot)
        - [🎓 libp2p as a platform for Networks Research & Innovation](#🎓-libp2p-as-a-platform-for-networks-research--innovation)
        - [🚑 Self-healing networks](#🚑-self-healing-networks)
        - [📮 Offline message queue / postbox](#📮-offline-message-queue--postbox)
        - [🤖 libp2p as a WASM library](#🤖-libp2p-as-a-wasm-library)
    - [Evolve](#evolve)
        - [🕸 Unprecedented global connectivity](#🕸-unprecedented-global-connectivity)
        - [✈️ WebTransport](#✈️-webtransport)
        - [⏱ Full Observability](#⏱-full-observability)
        - [🧪 Automated compatibility testing](#🧪-automated-compatibility-testing)
        - [🤝 Low latency, efficient connection handshake](#🤝-low-latency-efficient-connection-handshake)
        - [🛣️ Peer Routing Records](#🛣️-peer-routing-records)
        - [🗣️ Polite peering](#🗣️-polite-peering)
        - [🧱 Composable routing](#🧱-composable-routing)
        - [💣 Attack resistance, threat models and security](#💣-attack-resistance-threat-models-and-security)
        - [📈 Proving we are scalable and interoperable](#📈-proving-we-are-scalable-and-interoperable)
        - [🌐 Browser use cases](#🌐-browser-use-cases)
        - [🌡️ Opt-in telemetry protocol](#🌡️-opt-in-telemetry-protocol)
        - [📩 Message-oriented transports](#📩-message-oriented-transports)
        - [☎️ Reducing the dial fail rate](#️-reducing-the-dial-fail-rate)
        - [🔀 Peer exchange protocol](#🔀-peer-exchange-protocol)
        - [🏹 RPC and other common node communication patterns](#🏹-rpc-and-other-common-node-communication-patterns)

## Visionary

**Our long term roadmap**.

This is the stuff that moves libp2p from "a networking toolbox to build P2P
applications" to the thing that fundamentally reshapes the architecture of the
Internet; our dreams and aspirations, the North star we should always keep in
sight; this is what motivates us and it's speaks intimately to our mission
statement; the libp2p analogy of IPFS working on Mars

### 🖧 Decentralizing networks

**What?** Interacting and transacting with the *person next to me* should not
require me to resort to the Internet, make use of centralised services run by
corporations, expose myself to censorship, and lose self-agency over my data.

This theme covers a number of related topics: mesh networking, community
networks, sneaker nets, isolated networks in libp2p.

An undertaking like this touches upon many surfaces of the system, e.g.
implementing new transports (Bluetooth, software defined radio,
ultrasonic data \[Chirp\], Wi-Fi direct, QR, Ethernet, 802.11s, etc.),
new discovery mechanisms (local peer exchange, social peer
advertisement, etc.), packet-switched routing, and more.

But it's not just about connectivity. In this new reality, nodes can
come and go easily. As a result, new requirements will emerge, such as
supporting *roaming* (the ability for a user to switch networks without
dropping ongoing sessions) and *resilient state and connectivity*, to
buffer data (potentially via a store-and-forward architecture) so that a
node disconnecting intermittently can get up to speed when they come
back online.

For certain applications, we might want to take compensatory actions
after a grace period, such as rebalancing data across nodes. And this
requires us to think about group membership, partitioning, consensus,
etc. This is just an initial train of thought, and there's a lot more
ground to cover.

**Why?** The IPFS roadmap tackles mesh networks, isolated networks,
sneaker nets, and making IPFS work in Mars where general
connectedness to the Internet does not exist. *The network should pave
the way for IPFS to evolve in that direction.*

### 🤫 A spyproof libp2p

**What?** Supporting transports like cjdns, I2P and Tor (see
[OpenBazaar/go-onion-transport](https://github.com/OpenBazaar/go-onion-transport))
helps create resilient, privacy-centric communications, and moves the needle
forward towards censorship-resistant networks. As an intermediary step, we
should improve our existing transport stack, e.g. preventing downgrade attacks
when securing connections.

### 📱 libp2p in mobile devices

**What?** First-class integration of libp2p in mobile devices is a prerequisite
for the class of offline-first use cases we are targeting.

This implies building/supporting Java/Kotlin and Swift implementations -- either
fully-fledged or trimmed-down versions that do the minimum necessary or wrap
existing implementations like nim-libp2p or rust-libp2p.

**Why?** Bringing libp2p natively to mobile devices is an enabler for
offline-first use cases.

### 💡 libp2p in IoT

**What?** Distinct from consumer mobile devices like smartphones, IoT
devices like embedded sensors are a potential use case for libp2p. These
devices are typically more resource constrained and may have
intermittent connectivity. They also tend to do minimal processing
locally, but transmit frequently to a cloud where data analysis occurs.

**Why?** IoT can greatly benefit from peer-to-peer networking. Supporting IoT
environments with libp2p greatly expands libp2p's userbase on the one side and
on the other enables existing libp2p deployments to interconnect with said IoT
devices.

### 🎓 libp2p as a platform for Networks Research & Innovation

**What?** Academics should be able to use libp2p as a playground for
their research. Amongst other points, this encompasses:

1.  Building a public utility p2p network that academics can deploy
    their algorithms and solutions onto, to trial them on a large
    scale, or test their hypothesis on.

2.  *Packaging P2P prior art in composable building blocks,* to allow
    researchers to focus on the problem at hand, without having to
    reinvent the wheel.

3.  Providing modelling tools, data collection hooks, sampling
    strategies, etc. to facilitate research practices.

4.  Making libp2p stable and dependable enough so researchers are
    satisfied with the *rigor* of studies built on libp2p.

This goal has parallels with the TestLab endeavour.

**Why?** To contribute back to the p2p research community; to harness
the work taking place at research facilities by implementing the
research outputs on libp2p.

### 🚑 Self-healing networks

**What?** A number of nodes in the network take on important assistive
roles, e.g. bootstrap, DHT boosters, relay, network, etc. However:

1. relying on static IPs or DNS entries exposes us to centralisation,
   and is fragile.

2. the network grows and shrinks dynamically, so we should scale these
   nodes accordingly.

3. these nodes are easy to attack directly, and such attacks can harm
   the network; currently we have no resilience plan.

4. routing/connectivity between nodes could be compromised by network
   attacks, or censorship.

In the long term, we aim to build a resilient, self-healing network that
scales dynamically based in response to traffic volume, disasters, and
network conditions.

**Why?** To get closer to the dream of unstoppable, intelligent,
adaptive networks.

### 📮 Offline message queue / postbox

**What?** Providing solutions to store data for nodes that have gone
offline temporarily. Payloads can be pubsub messages, DHT provider
records, or even RPC calls. In traditional MQ systems, this property is
typically termed "reliability".

Several ideas have been floated within the libp2p community:

- Third-party postbox nodes that are incentivised to buffer data between nodes A
  and B, when either is unavailable.

- Store-and-forward architectures.

And there's probably many more to explore. When reasoning about these
methods, we should keep in mind aspects like replication, storage,
liveness, byzantine fault tolerance, etc. Depending on the mechanism,
the challenges may even align with those of Filecoin.

**Why?** It's an enabler for offline-first scenarios, low quality connections,
roaming, etc.

**Links:**

-   https://github.com/libp2p/notes/issues/2

### 🤖 libp2p as a WASM library

**What?** This point encompasses two things:

1. Preparing [existing
   implementations](https://github.com/libp2p/rust-libp2p/issues/23) to run in
   WASM environments (mainly the browser).

2. Evaluating if it's feasible to build a canonical implementation of
   libp2p, that is maintained in a single language, compiling down to
   WebAssembly so that it can be used from any other programming
   language -- as long as the user is building a WASM application.
   (The feasibility of this idea is unknown as this time;
   particularly the VM doesn't expose a socket API, but the
   Emscripten SDK emulates IP sockets over WebSockets.)

**Why?** Aside from targeting WASM use cases, having one canonical
implementation of libp2p that can *run anywhere* could help focus the
team's time on building new features, instead of keeping a multitude of
implementations across different languages in sync, i.e. create more
value and impact. WASM also presents a huge vector for making libp2p the
de-facto networking stack, for cases where WASM is a suitable deployment
model.

**Links:**

- [WASM support in rust-libp2p](https://github.com/libp2p/rust-libp2p/issues/23).

## Evolve

**Our short-term roadmap**.

This is the stuff pushing the existing libp2p stack forward.

### 🕸 Unprecedented global connectivity

**Status**: In progress

**What?** A DHT crawl measurements (Nov 22nd 2019) showed that out
of 4344 peers, 2754 were undialable (\~63%). This evidence correlates
with feedback from the IPFS and Filecoin teams.

We need to implement additional mechanisms for Firewall and NAT traversal to
have the highest probability of being able to establish a direct connection.
Mechanisms we wish to add include:

- Project Flare stack (via *Circuit Relay v2*, *Direct Connection Upgrade
  through Relay*, *AutoNAT*, *Stream Migration*, ...)

- WebRTC

**Why?** Good connectivity is the bread-and-butter of libp2p. Focusing
on solving these issues will bring more stability and robustness to the
rest of the system.

**Links:**

- [Hole punching long-term
  vision](https://github.com/mxinden/specs/blob/hole-punching/connections/hole-punching.md).

- [NAT traversal tracking issue](https://github.com/libp2p/specs/issues/312).

- [WebRTC tracking issue](https://github.com/libp2p/specs/issues/220)


### ✈️ WebTransport

**Status**: In progress

**What?** WebTransport is a browser-API offering low-latency, bidirectional
client-server messaging running on top of QUIC. The browser API allows the
establishment of connections to servers that don't have a TLS certificate
signed by a certificate authority if the hash of the certificate is known in
advance.

**Why?** This allows libp2p nodes running in the browser (using js-libp2p) to
connect to the rest of the libp2p network.

**Links:**

- [IETF draft](https://datatracker.ietf.org/doc/draft-ietf-webtrans-http3/)
- [W3C Browser API](https://w3c.github.io/webtransport/)
- [libp2p spec discussion](https://github.com/libp2p/specs/pull/404)
- [webtransport-go](https://github.com/marten-seemann/webtransport-go/)

### ⏱ Full Observability

**What?** libp2p should expose a wide set of metrics, making it easy to
monitor the system.

Metrics should include:
- Transport metrics (TCP, QUIC, security protocols, stream multiplexers)
- Swarm metrics
- other subsystems (AutoNAT, AutoRelay, Hole Punching)

**Why?** A system that cannot be monitored will misbehave - sooner or later.

**Links:**

- [go-libp2p discussion](https://github.com/libp2p/go-libp2p/issues/1356)

### 🧪 Automated compatibility testing

**Status**: In progress

**What?** There are more than 6 implementations of the [libp2p specification] in
different languages. We need to ensure compatibility of all combinations of these
implementations. Given the number of libp2p implementations and the amount of
libp2p protocols, verifying compatibility on a continuous basis can only be
tackled in an automated fashion.

**Why?** Automated compatibility testing allows us to move fast with confidence
and will increase trust in the libp2p project as a whole.

We can build on top of the [testground project]. Multiple of the so called
testground _test plans_ are already in place for the go-libp2p implementation in
the [libp2p test-plans repository].

**Links:**

- [First proof of concept](https://github.com/libp2p/test-plans/pull/20)

### 🤝 Low latency, efficient connection handshake

**High priority for: IPFS**

**What?** Establishing a connection and performing the initial handshake
should be as cheap and fast as possible. Supporting things like
*selective* stream opening, *preemption*, *speculative* negotiation,
*upfront* negotiation, protocol table *pinning*, etc. may enable us to
achieve lower latencies when establishing connections, and even the
0-RTT holy grail in some cases. These features are being discussed in
the *Protocol Select* protocol design.

**Why?** Multistream 1.0 is chatty and naïve. Streams are essential to
libp2p, and negotiating them is currently inefficient in a number of
scenarios. Also, bootstrapping a multiplexed connection is currently
guesswork (we test protocols one by one, incurring in significant
ping-pong).

**Links:**

- [Protocol Select specification](https://github.com/libp2p/specs/pull/349)

### 🛣️ Peer Routing Records

**What?** Methods such as DHT traversal depend on potentially untrustworthy
third parties to relay address information. Peer Routing Records provide a means
of distributing verifiable address records, which we can prove originated from
the addressed peer itself.

**Why?** Being able to prove the authenticity of addresses discovered through
some mechanism prevents address spoofing as well as attacks enabled through
address spoofing.

Peer Routing Records are defined in [RFC 0003]. They are used in combination
with Signed Envelopes which are defined in [RFC 0002]. While the specification
work is done, existing discovery mechanisms such as the Kademlia DHT need to
support advertising signed Peer Routing Records.

[RFC 0003]: https://github.com/libp2p/specs/blob/master/RFC/0003-routing-records.md
[RFC 0002]: https://github.com/libp2p/specs/blob/master/RFC/0002-signed-envelopes.md

### 🗣️ Polite peering

**What?** Peers don't behave well with one another. They do not send DISCONNECT
messages reporting the reason (e.g. rate limiting) for disconnection, they do
not warn when they're about to close a connection, they don't give peers a
chance to keep important connections open, etc.

**Why?** Peers act haphazardly when observed from the outside, leading e.g. to
unnecessary connection churn. They do not have the means to act more
collaboratively. We are lacking a wire protocol that governs the connection
between two peers.

### 🧱 Composable routing

**What?** The composable routing framework has four "pillars**:

* Routing syntax and language

  The routing syntax is a common data model (with a user-facing syntactic
  representation) for communicating routing-related information (requests and
  responses). The [implementation of the routing
  syntax](https://github.com/libp2p/go-routing-language/tree/master/syntax)
  provides serialization and pretty printing of routing expressions.

* Routing interface

  A routing system processes routing requests and returns routing responses.
  Routing requests and responses have semantics, which are unlike those of a
  traditional request/response protocols, that implement function call arguments
  and return values.

* Smart Records

  Smart Records (SR) is a technology that enables multiple decentralized parties
  and protocols to randevouz and share information on a topic. Specifically, SR
  is a key-value store service, which facilitates conflict-free updates to
  values by multiple writers.

* Subnets

  At present, there is a single DHT network which spans across all IPFS nodes.
  We would like to introduce a general standard for the co-existence of multiple
  network instances with individual discovery, membership and content routing
  semantics.

**Why?** Enable interoperability of protocols and nodes with different versions
and capabilities, developed by independent teams or organizations. As a
consequence, it also enables middleware components (like caching, batching,
predictive fetching, and so on** and the co-existence of different content
finding protocols and subnetworks.

**Links:**

- [Tracking issue](https://github.com/libp2p/specs/issues/343)

### 💣 Attack resistance, threat models and security

**What?** This is an overarching element of the roadmap, and it affects
everything else. Activities under this endeavour include:

1. *Past and present.* Pragmatically analysing and profiling the
   exposure of each component against a taxonomy of attacks and
   threat models, e.g. DDoS, byzantine, sybil, poisoning, eclipse,
   flooding, etc.

2. *Past and present.* Establishing a plan to mitigate all identified
   attack vectors, and delivering on it.

3. *Future.* Setting up an ongoing process to assess the security
   implications of all future pull requests (e.g. checklists for code
   reviews).

4. We may even decide to hire a specialist in the team.

5. Different kinds of simulations.

**Why?** As more projects entrust libp2p to take care of their
networking requirements, the more we have at stake (reputationally), and
the higher the incentive for attackers to find ways to disrupt libp2p
networks.

**Links:**

- [A Taxonomy of Attack Methods on Peer-to-Peer
  Networks](http://www.dcs.gla.ac.uk/~sadekf/P2PSecTaxonomy.pdf).

- [Attacks Against Peer-to-peer Networks and
  Countermeasures](https://pdfs.semanticscholar.org/8d9f/e736de5c987f9139061b77c6bcd0c99deb27.pdf).

- [A Survey of Peer-to-Peer Network Security
  Issues](https://www.cse.wustl.edu/~jain/cse571-07/ftp/p2p/).

- [Low-Resource Eclipse Attacks on Ethereum's Peer-to-Peer
  Network](https://eprint.iacr.org/2018/236.pdf).

- [Ethereum Serenity research: Sybil-like attacks at the p2p
  level](https://github.com/ethresearch/p2p/issues/6).

### 📈 Proving we are scalable and interoperable

**What?** Proving the scalability of libp2p at orders of magnitude
10\^4, 10\^6, and more, across all native implementations of libp2p.
Conducting these tests in a lab setting requires solving problems like
cluster operation, code instrumentation and metrics collection at scale.

But some magnitudes are cost-ineffective to test in a dedicated
infrastructure. We might have to resort to capturing empirical evidence
from live networks. [This ties in with the opt-in telemetry
protocol](#opt-in-telemetry-protocol) and the extension of
IPTB into IPTL (TestLab).

And we cannot forget negative testing. This includes chaos engineering
(*libp2p chaos monkey* idea), orchestrated attacks and theoretical
simulations.

Example targets/KPIs:

- DHT lookups return the correct value in \<= N seconds in a 10\^9
  node network.

- Pubsub messages reach all subscribers in \<= N seconds in a 10\^9
  node network where M% subscribe to the topic

- Network survives and re-balances following the churn of N% nodes, at
  M node/s departure/arrival rate, measured by ...

**Why?** To gain confidence that the technology that we're building is a
rock-solid foundation for the future of P2P networks; to quantitatively
measure the impact of our changes on the large scale; to combat the
perception in some circles that libp2p is "immature".

### 🌐 Browser use cases

**What?** This spans a number of concerns. First, we should improve
developer experience and make libp2p more accessible in browser
environments. This entails reducing footprint (e.g. bundle size) and
creating examples and documentation on how to bundle js-libp2p with
popular frontend tooling (webpack, parcel, etc.). Developers should be
able to cherry-pick the features to incorporate in their bundle, and
tree-shaking should produce good results.

In terms of transports, hardening our WebRTC support and enabling it by
default will bring a huge boost to general browser connectivity.

Targeting the [WASM runtime](#libp2p-as-a-wasm-library)
deserves a special mention, as we're likely to see more user interest in
this area. Finally, we should continue supporting the
[TCP](https://github.com/mozilla/libdweb/issues/5) and
[UDP](https://github.com/mozilla/libdweb/issues/4) socket
advances made by Mozilla's
[libdweb](https://github.com/mozilla/libdweb/) team.

**Why?** Browsers are and will continue to be the most used computer interface.
Not fully supporting the browser platform will hurt most of the projects betting
on libp2p.

### 🌡️ Opt-in telemetry protocol

**What?** By developing a *decentralized* telemetry protocol that nodes can opt
into, we could build a world-wide real-time visualisation of our global libp2p
network, à la [Torflow](https://torflow.uncharted.software), [Kaspersky's
Cybermap](https://cybermap.kaspersky.com/), or [Checkpoint's
Threatmap](https://threatmap.checkpoint.com/).

This might surface interesting facts about the backbone of the Internet;
perhaps even correlations with the [Submarine Cable
Map](https://www.submarinecablemap.com/). Imagine [RIPE
Atlas](https://atlas.ripe.net/results/maps/network-coverage/)
but for libp2p networks.

Nodes could probe and collect stats about the connections it maintains
with other peers: latency, traceroute, IP address, etc., publishing raw
data on a global pubsub channel like a heartbeat, where a webapp is
listening over a websockets channel.

**Why?** To gain real-time insight into the global libp2p deployment.

### 📩 Message-oriented transports

**What?** The data layer of the libp2p API is geared towards streams,
and does not support message orientation. The notion of messages [has
been discussed](https://github.com/libp2p/specs/issues/71)
in the past, and there is even a [draft proposal for a multigram
protocol](https://github.com/multiformats/multigram/tree/draft1).

Progressing with this work entails designing the abstractions, and
implementing, at least, a UDP transport, [as the community has
demanded](https://github.com/libp2p/go-libp2p/issues/353).

**Why?** Current the libp2p API precludes us from modelling
message-oriented transports like UDP or Bluetooth.

### ☎️ Reducing the dial fail rate

**What?** Reducing the dial fail rate implies improvements in several
areas.

-  **Outbound dials:** We should strategise dials based on context, or based on
   a heuristic determined by the application. For example, apps designed for
   local exchange of data will naturally prefer to try local/physical endpoints
   over public ones first. We may want to dial relay addresses last, dial newer
   addresses first, etc.

   Users should also have the capability to customise how addresses are
   resolved, how dials are throttled, how connections are selected if multiple
   dials succeeded, etc. In a nutshell, the dialing behaviour should be fully
   customisable per host.

-  **Context-sensitive advertisement of self-addresses:** private
   addresses should not leak into public DHTs, both for connectivity
   and security reasons (cf. IPFS DHT pollution in 2016). Similarly,
   local discovery mechanisms should only transmit private addresses.
   The DHT topology question becomes relevant to define scopes (e.g.
   federated/concentric/shared DHTs for different scopes). Also, when
   dealing with multi-layer NATs, there may be better routes between
   peers behind regional or ISP NATs other than their public
   endpoints.

- **Connectivity-related problems:** see [Unprecedented global
  connectivity](#unprecedented-global-connectivity) and
  [Improve NAT traversal](#improve-nat-traversal).

**Why?** Dialing is a crucial function of our system and using a
non-deterministic, scattershot approach is inefficient both in regards to the
number of failed dial attempts and the increased _time to first byte_.

**Links:**

- [Reliable dialing](https://github.com/libp2p/libp2p/issues/27).

### 🔀 Peer exchange protocol

Copied and adapted from:
[https://github.com/libp2p/notes/issues/3](https://github.com/libp2p/notes/issues/3)

**What?** We currently use mDNS to discover local peers but it would
also be nice if we could have a peer exchange protocol for discovering
even more local peers.

**Why?** (1) relying on the global DHT to discover local peers is problematic;
(2) ideally, we want to be able to discover all peers on the local network. In
case two devices are in the same room, they should be able to share files with
each-other directly. [This ties into offline and decentralised
networks.](#kix.xlvu7ikvo1jg)

**Links**

- https://github.com/libp2p/notes/issues/3

- https://github.com/libp2p/notes/issues/7

- https://github.com/libp2p/specs/issues/222

### 🏹 RPC and other common node communication patterns

**What?** Make it easy for developers to communicate between libp2p
nodes using development patterns that they are used to. This includes
creating libraries with the appropriate documentation and examples that
support common use cases including:

- RPCs using both primitive and non-primitive data types

- Peer service discovery and version compatibility

- Streaming blocks of non-primitive data types

- RPCs with implicit context (e.g. if performing multiple operations
  on objID, only pass it once)

**Why?** We currently have multiple implementations and strategies for
getting libp2p nodes to communicate, however the startup cost for
developers wanting to add their own communication protocols and
endpoints is still too high. By providing simple and familiar frameworks
like RPC to developers they should be able to more efficiently develop
their projects. Additionally, easy to use high level communication
frameworks should allow developers not very familiar with low-level
networking to get started with libp2p.

**Links**

- See Rust's [libp2p-request-response] as one possible communication pattern
  abstraction.

[libp2p-request-response]: https://docs.rs/libp2p-request-response/0.11.0/libp2p_request_response/
[libp2p specification]: https://github.com/libp2p/specs/
[testground project]: https://github.com/testground/testground
[libp2p test-plans repository]: https://github.com/libp2p/test-plans
