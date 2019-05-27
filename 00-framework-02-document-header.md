# Document Header for libp2p Specs

> A standard document header to indicate spec maturity, status & ownership

| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r0, 2019-05-27  |

Authors: [@yusefnapora]

Interest Group: TBD

[@yusefnapora]: https://github.com/yusefnapora

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Motivation

The [maturity and lifecycle spec][lifecycle-spec] defines levels of maturity for
libp2p specs, as well as the states that a spec can be in at a given time. It
also introduces the notion of an `Interest Group`, which is a set of libp2p
community members that have expressed interest in the spec and are willing to
help move it forward in its evolution.

This document defines a header format to convey this key status information in
an easy-to-read manner.

## Example 

```markdown
# Spec title

> An optional one-liner summary of the spec

| Lifecycle Stage | Maturity                 | Status | Latest Revision |
|-----------------|--------------------------|--------|-----------------|
| 2A              | Candidate Recommendation | Active | r0, 2019-05-27  |


Authors: [@author1], [@author2]

Interest Group: [@interested1], [@interested2]

[@author1]: https://github.com/author1
[@author2]: https://github.com/author2
[@interested1]: https://github.com/interested1
[@interested2]: https://github.com/interested2

See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md
```

## Format

### Title and Short Intro

Each spec begins with its title, formatted as an H1 markdown header. 

The title can optionally be followed by a short block-quote introducing the
spec, which should be a maximum of one or two lines.

### Status Table

The main status information is contained in a markdown table, using the [table
syntax][gfm-tables] supported by [Github Flavored Markdown][gfm-spec].

The status table consists of a single row, with a header containing the field
names. 

Example:

```markdown
| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | r0, 2019-05-27  |
```

The following fields are all required:

- `Lifecycle Stage`
  - The [abbreviated lifecycle stage][abbrev-stage-definition] that the spec is
    currently in. This must match the `Maturity` and `Status` fields.
- `Maturity`
  - The full name of the maturity level that the spec is currently in.
  - Valid values are: `Working Draft`, `Candidate Recommenation`,
    `Recommendation`
- `Status`
  - The full name of the status that the spec is currently in.
  - For `Candidate Recommendation` or `Recommendation` specs, valid values are
    `Active` and `Deprecated`
  - For `Working Draft` specs, valid values are: `Active` and `Terminated`
- `Latest Revision`
  - A revision number and date to indicate when the spec was last modified,
    separated by a comma.
  - Revision numbers start with lowercase `r` followed by an integer, which gets
    bumped whenever the spec is modified by merging a new PR.
  - Revision numbers start at `r0` when the spec is first merged.
  - Dates are formatted according to [ISO 8601](https://xkcd.com/1179/)

### Authors and Interest Group

After the status table, spec Authors and Interest Group members are listed.

Authors and Interest Group members are referenced by their Github handles
(with a leading `@` symbol), and are presented as a comma-separated list of links
to Github profiles.

To make the list readable in the markdown source, we use the [shortcut reference
link syntax][gfm-shortcut-refs], which allows us to wrap the author name in
square brackets in the list and define the link target below. For example:

```markdown
Authors: [@author1], [@author2]

Interest Group: [@interested1], [@interested2]

[@author1]: https://github.com/author1
[@author2]: https://github.com/author2
[@interested1]: https://github.com/interested1
[@interested2]: https://github.com/interested2
```

The Authors and Interest Group lists must be separated by a newline, which
causes them to render as distinct paragraphs.

When proposing a new `Working Draft` where the Interest Group is unknown, use
`TBD` to indicate that the group is To Be Determined:

```markdown
Interest Group: TBD
```

### Link to Lifecycle Doc

Finally, the header should contain a link to the [lifecycle
spec][lifecycle-spec] so that readers can get up to speed on the definitions
used in the header. To avoid having to keep track of relative paths within the
specs repo, an absolute URL is preferred when linking to the specs document.

Here's an example that can be copy/pasted directly:

```markdown
See the [lifecycle document][lifecycle-spec] for context about maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md
```

[abbrev-stage-definition]: ./00-framework-01-spec-lifecycle.md#abbreviations
[gfm-tables]: https://help.github.com/en/articles/organizing-information-with-tables
[gfm-spec]: https://github.github.com/gfm/
[gfm-shortcut-refs]: https://github.github.com/gfm/#shortcut-reference-link
