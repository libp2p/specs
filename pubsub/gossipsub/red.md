# gossipsub v1.1: Functional Extension for Validation Queue Protection

| Lifecycle Stage | Maturity                  | Status | Latest Revision |
|-----------------|---------------------------|--------|-----------------|
| 1A              | Working Draft             | Active | r1, 2020-09-05  |

Authors: [@vyzo]

Interest Group: [@yusefnapora], [@raulk], [@whyrusleeping], [@Stebalien], [@daviddias], [@protolambda], [@djrtwo], [@dryajov], [@mpetrunic], [@AgeManning], [@Nashatyrev], [@mhchia]

[@whyrusleeping]: https://github.com/whyrusleeping
[@yusefnapora]: https://github.com/yusefnapora
[@raulk]: https://github.com/raulk
[@vyzo]: https://github.com/vyzo
[@Stebalien]: https://github.com/Stebalien
[@daviddias]: https://github.com/daviddias
[@protolambda]: https://github.com/protolambda
[@djrtwo]: https://github.com/djrtwo
[@dryajov]: https://github.com/dryajov
[@mpetrunic]: https://github.com/mpetrunic
[@AgeManning]: https://github.com/AgeManning
[@Nashatyrev]: https://github.com/Nashatyrev
[@mhchia]: https://github.com/mhchia

See the [lifecycle document][lifecycle-spec] for context about maturity level and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

---

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
- [Overview](#overview)
- [Validation Queue Protection](#validation-queue-protection)
- [Random Early Drop Algorithm](#random-early-drop-algorithm)
- [RED Parameters](#red-parameters)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Overview

This document specifies an extension to [gossipsub v1.1](gossipsub-v1.1.md) intended to
provide a circuit breaker so that routers can withstand concerted attacks targetting the
validation queue with a flood of spam.
This extension does not modify the protocol in any way and works in conjuction with the defensive
mechanisms of gossipsub v1.1.

## Validation Queue Protection

An important aspect of gossipsub is the reliance on validators to signal acceptance of incoming
messages from the application to the router. The validation is asynchronous, with a typical
implementation strategy that uses of a front-end queue and a limit to the number of ongoing validations.
This creates a potential target for attacks, as an attacker can overload the queue by brute force,
sending spam messages at a very high rate. The effect would be that legitimate messages get dropped
by the validation front end, resulting in denial of service.

In order to protect the system from this class of attacks, gossipsub v1.1 incorporates a circuit
breaker that sits before the validation queue and can make informed decisions on whether to
push a message into the validation queue. This defensive mechanism kicks in when the system detects
an elevated rate of dropped messages, and makes decisions on whether to accept incoming messages for
validation based on the statistical performance of peers in the origin IP address. The decision is
probabilistic and implements a Random Early Drop (RED) strategy that drops messages with a probability
that depends on the acceptance rates for messages from the origin IP. This strategy can neuter
attacks on the validation queue, because messages are no longer dropped indiscriminately in a drop-tail
fashion.

## Random Early Drop Algorithm

The algorithm has two aspects:
- The decision on whether to trigger RED.
- The decision on whether to drop a message from an origin IP address.

In order to trigger RED, the circuit breaker maintains the following queue statistics:
- a _decaying_ counter for the number of message validations.
- a _decaying_ counter for the number of dropped messages.

The decision on triggering RED is based on comparing the ratio of dropped messages to validations.
If the ratio exceeds an application configured threshold, then the RED algorithm
triggers and a decision on whether to accept the message for validation is made based on origin IP
statistics. There is also a quiet period, such that if no messages have been dropped for a while, the
circuit breaker turns back off.

In order to make the actual RED decision, the circuit breaker maintains the following statistics per
IP:
- a _decaying_ counter for the number of accepted messages.
- a _decaying_ counter for the number of duplicate messages, mixed with a weight `W_duplicate`.
- a _decaying_ counter for the number of ignored messages, mixed with a weight `W_ignored`.
- a _decaying_ counter for the number of rejected messages, mixed with a weight `W_rejected`.

The router generates a random float `r` and accepts the message if and only if
```
r < (1 + accepted) / (1 + accepted + W_duplicate * duplicate + W_ignored * ignored + W_rejected * rejected)
```

The number of accepted messages is biased by 1 so that a single negative event cannot sinkhole an IP.
It also always gives a chance for a message to be accepted, albeit with sharply decreasing probability
as negative events accumulate.

All the counters decay linearly with an application configured decay factor, so that the sytem adapts
to varying network conditions.

Also note that per IP statistics are retained for a configured period of time after disconnection, so
that an attacker cannot easily clear traces of misbehaviour by disconnecting.

Finally, the circuit breaker should allow the application to configure per topic accepted delivery
weights, so that deliveries in priority topics can be given more weight.
If a topic is not configured, then its delivery weight is 1.

## RED Parameters

The circuit breaker utilizes the following application configured parameters:

| Parameter | Purpose | Default |
|-----------|---------|---------|
| `ActivationThreshold` | dropped to validated message ratio threshold for triggering the circuit breaker | `0.33` |
| `GlobalDecayCoefficient` | linear decay coefficient for global stats | computed such that the counter decays to 1% after 2 minutes |
| `SourceDecayCoefficient` | linear decay coefficient for per IP stats | computed such that the counter decays to 1% after 1 hour |
| `QuietInterval` | interval of no dropped message events before turning off the circuit breaker | 1 minute |
| `W_duplicate` | counter mixin weight for duplicate messages | `0.125` |
| `W_ignore` | counter mixin weight for ignored messages | `1.0` |
| `W_reject` | coutner mixin weight for rejected messages | `16.0` |
| `RetentionPeriod` | duration of stats retention after disconnection | 6 hours |

With the default parameters, we are rapidly penalising rejections, mildly penalising ignored messages,
and softly weighting duplicate messages because they occur normally for mesh peers.
The result is that clearly misbehaving peers whose messages lead to outright rejections, will make up
for a substantial part of the decision to break the circuit, while underperforming peers will also
factor in, but with less force.
