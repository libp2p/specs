# libp2p specification framework – the five-stage maturity process

> Author: @raulk

> Revision: r0, 2019-05-21

## Prelude

This document establishes a framework to foster rapid and incremental libp2p
specification development, aiming to reduce the barrier to entry for new
ideas, increasing the throughput of breakthrough creative proposals, promoting
their evolution and adoption within the community, while maximising consensus
around a common lifecycle and criteria for progression across stages.

We propose a five-stage process to classify the maturity of a specification in
terms of completeness, demonstrability of implementation, community
acceptance, and level of technical detail. It is somewhat inspired in the W3C
Process [0].

  1. `Working Draft`
  2. `Candidate Recommendation`
  3. `Recommendation`
  4. `Deprecated`
  5. `Abandoned Draft`

## Stage 1: Working draft

The specification of the system, process, protocol or item is under active
development. This stage is lightweight and mostly self-directed by the author.
We aim to reduce the barrier to entry, and it's designed to allow for
iterative experimentation, discovery and pivoting.

We don't enforce a hard template in an attempt to enhance author
expressability and creativity.

We enter this stage by posting an `Initial Working Draft` that covers:
  * context: what is the current situation or a brief overview of the
    environment the specification targets.
  * motivation: why this specification is relevant, and how it advances the
    status quo.
  * scope and rationale: what areas of the technical system the specification
    impacts.
  * goals: what we expect to achieve (positively and negatively) as a result
    of implementing the specification.
  * expected feature set: a summary/enumeration of features the spec provides.
  * tentative technical directions: how are we planning to materialise the
    specification in terms of system design.

Upon submission of an `Initial Working Draft`, a minimum of three (3) libp2p
contributors are required to express interest and commitment to shepherd and
advise the author(s) throughout the specification process.

The resulting group will constitute the _Interest Group_, formed by consensus,
barring blocking, binding community feedback. We encourage the _Interest
Group_ to be heterogeneous yet relevant, and hold representation for libp2p
implementation teams across various languages.

The _Interest Group_ will be responsible for expediently awarding the review
approvals or feedback necessary to transition the specification across stages.

The `Initial Working Draft` shall be reviewed by the _Interest Group_ in no
more than 3 working days. Should there be no defects in form, content or
serious technical soundness issues, the `Initial Working Draft` will be
accepted and merged.

Ideas deemed controversial or breaking, and those that garner subjective
opposition, will still be accepted in order to give them a venue to grow,
mature and iterate.

Once the `Initial Working Draft` is merged, the author may continue revising
and evolving their specification by self-approving their own *Pull Requests*.

To facilitate open progress tracking and observability, as the `Working Draft`
evolves, the author(s) SHOULD assemble a checklist of items that are pending
specification, explicitly stating which items are compulsory for promoting the
spec to a `Candidate Recommendation`.

As a `Working Draft` evolves and shows promise to exit this stage towards a
`Candidate Recommendation`, the _Interest Group_ shall be expanded by two (2)
additional members, comprising a total of five (5).

We MAY use GitHub's
[`CODEOWNERS`](https://help.github.com/en/articles/about-code-owners) feature
to enforce per-spec approval policies automatically.

## Stage 2: Candidate Recommendation

The changes requested by the specification are considered plausible and
desirable.

The specification document itself is technically complete. It defines wire
level formats for interoperability, error codes, algorithms, data structures,
heuristics, behaviours, etc., in a way that it is sufficient to enable
contributors to develop an interoperable implementation.

There is at least ONE implementation conforming to the specification. That
implementation serves as the Reference Implementation.

The promotion from a `Working Draft` to a `Candidate Recommendation` is done
via a *Pull Request* that is reviewed by the _Interest Group_, allowing a
minimum of 8 working days to elapse to collect feedback from the libp2p
community at large.

## Stage 3: Recommendation

There are at least TWO implementations conforming to the specification, with
demonstrated cross-interoperability. This is the supreme stage in the
lifecycle of a specification.

The promotion from a `Candidate Recommendation` to a `Recommendation` is done
via a *Pull Request* that is reviewed by the _Interest Group_, allowing a
minimum of 8 working days to elapse to collect feedback from the libp2p
community at large.

## Stage 4: Deprecated

The specification is no longer applicable and the community actively
discourages new implementations.

Transition to this stage is usually the result of a new version of the
specification reaching the `Candidate Recommendation` stage.

The transition from a `Candidate Recommendation` or a `Recommendation` stage
to the `Deprecated` stage is performed via a *Pull Request* that is reviewed
by the _Interest Group_, allowing a minimum of 5 working days to elapse to
collect feedback from the libp2p community at large.

## Stage 5: Abandoned Draft

In order to motivate accountability, efficiency and order, a specification
that stays in the `Working Draft` stage for over 4 months of its initial
approval will automatically transition to the `Abandoned Draft` stage.

Extensions can be requested up to 2 times (making for a cumulative runway 12
months), and will only be granted by consensus if there's evidence of progress
and continued author commitment.

---

## Interest Group membership changes

Changes in the membership of an _Interest Group_ are possible at any time.

While we don't maintain a comprehensive enumeration of reasons, common sense
applies.

They include events like waning dedication/commitment of members, changes in
technical relevance, or violations of the [community code of
conduct](https://github.com/ipfs/community/blob/master/code-of-conduct.md).

## References

[0] W3.org. (2019). World Wide Web Consortium Process Document. [online]
Available at: https://www.w3.org/2019/Process-20190301/ [Accessed 21 May
2019].