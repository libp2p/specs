# libp2p specification framework – lifecycle: maturity level and status

> Author: @raulk

> Revision: r0, 2019-05-21

## Prelude

Our goal is to design a framework to foster rapid and incremental libp2p
specification development, aiming to reduce the barrier to entry for new
ideas, increasing the throughput of ideation and crystallization of
breakthrough novel proposals, promoting their evolution and adoption within
the ecosystem, while maximising consensus through a common policy for
progression across lifecycle stages.

This document defines the policies that regulate specification lifecycle. Our
ideas are partially inspired in the W3C Process [0].

## Definitions

We employ two axes to describe the stage of a specification within its
lifecycle:

  * Maturity level: classifies the specification in terms of completeness,
    demonstrability of implementation, community acceptance, and level of
    technical detail.

    We characterize specifications along a three-level, progressive scale:

      * `Level 1: Working Draft`
      * `Level 2: Candidate Recommendation`
      * `Level 3: Recommendation`

  * Status: classifies the operativeness of the specification.

      * `Active`
      * `Deprecated`
      * `Terminated`

Not all statuses are relevant to all maturity levels. This matrix defines the
applicability:

|                               | **Active** | **Deprecated** | **Terminated** |
| ----------------------------: | :--------: | :------------: | :------------: |
| **Working Draft**             |     ✔      |                |        ✔       |
| **Candidate Recommendation**  |     ✔      |        ✔       |                |
| **Recommendation**            |     ✔      |        ✔       |                |

To abbreviate the lifecycle stage of a specification, we combine the maturity
level and status in a two character string:

```
<maturity level>    ::= "1" | "2" | "3"
<status>            ::= "A" | "D" | "T"
<lifecycle stage>   ::= <maturity level> <status>
// example: 1A (Working Draft / Active), 2D (Candidate Recommendation / Deprecated).
```

## Maturity levels

### Level 1: Working Draft

The specification of the system, process, protocol or item is under
development.

This level is lightweight and mostly self-directed by the author. We aim to
reduce the barrier to entry, and it's designed to allow for iterative
experimentation, discovery and pivoting.

We don't enforce a hard template in an attempt to enhance author's
expressability and creativity.

We enter this level by posting an `Initial Working Draft` that covers:

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
more than 5 working days. Should there be no defects in form, content or
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

A `Working Draft` can be in either `Active` or `Terminated` status.

### Level 2: Candidate Recommendation

The changes proposed in the specification are considered plausible and
desirable.

The specification document itself is technically complete. It defines wire
level formats for interoperability, error codes, algorithms, data structures,
heuristics, behaviours, etc., in a way that it is sufficient to enable
contributors to develop an interoperable implementation.

There is at least ONE implementation conforming to the specification. That
implementation serves as the _Reference Implementation_.

The promotion from a `Working Draft` to a `Candidate Recommendation` is done
via a *Pull Request* that is reviewed by the _Interest Group_, allowing 10
working days to elapse to collect feedback from the libp2p community at large.

A `Candidate Recommendation` can be in either `Active` or `Deprecated` status.

### Level 3: Recommendation

There are at least TWO implementations conforming to the specification, with
demonstrated cross-interoperability. This is the supreme stage in the
lifecycle of a specification.

The promotion from a `Candidate Recommendation` to a `Recommendation` is done
via a *Pull Request* that is reviewed by the _Interest Group_, allowing 10
working days to elapse to collect feedback from the libp2p community at large.

A `Recommendation` can be in either `Active` or `Deprecated` status.

## Status

### Active

The specification is actively being worked on (`Working Draft`), or it is
actively encouraged for adoption by implementers (`Candidate Recommendation`,
`Recommendation`).

This is the entry status for all `Initial Working Drafts`, and is the default
status until some event triggers deprecation or termination.

### Deprecated

The specification is no longer applicable and the community actively
discourages new implementations from being built, unless requirements for
backwards-compatibility are in force.

Transition to this stage is usually triggered when a new version of a related
specification superseding this one reaches the `Candidate Recommendation`
stage.

The transition from the `Active` status to the `Deprecated` status is
performed via a *Pull Request* that is reviewed by the _Interest Group_,
allowing 5 working days to elapse to collect feedback from the libp2p
community at large.

### Terminated

A specification in `Working Draft` maturity level aged without ammassing
consensus in a timely fashion, and it was therefore terminated by the
procedure below.

Procedure for termination: In order to motivate accountability, efficiency and
order, a specification that stays on the `Working Draft` maturity level for
over 4 months of its initial approval will be transitioned to the `Terminated`
status automatically.

The author or _Interest Group_ can request extensions up to 2 times (making
for a cumulative runway 12 months), and will be granted by consensus if
there's evidence of progress and continued author commitment. We consider this
an implicit checkpoint to resolve issues that prevent the specification from
making progress.

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
