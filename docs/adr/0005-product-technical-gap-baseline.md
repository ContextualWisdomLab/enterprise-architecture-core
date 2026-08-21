# ADR 0005: Evidence-backed product and technical gap baseline

**Status:** Accepted

## Context

The repository distinguishes these evidence states: `protected` is an exact
head governed by branch protection; `candidate` is an unmerged implementation
branch or pull request; `integrated` is a capability present on the protected
`develop` head; `deployable` has exact package and acceptance evidence but is
not necessarily released; `released` has an immutable package and release
record; and `live` has runtime-observation evidence. These states are not
interchangeable: a protected or integrated head does not prove deployability,
release, or live operation. Treating a branch or a green check as shipped
product truth makes a buyer believe that an unmerged capability is available.
It also makes it easy to lose the next action when a base branch changes.

The architecture description must therefore record the buyer outcome, the
current implementation evidence, the open delivery dependency, and the exact
acceptance evidence for each gap. This is consistent with ISO/IEC/IEEE
42010:2022: an architecture description is a structured description of the
entity of interest and must not be confused with the entity or with an
unreleased proposal (International Organization for Standardization,
International Electrotechnical Commission, & Institute of Electrical and
Electronics Engineers, 2022).

## Decision

Maintain the living gap register at
[`docs/product-technical-gap-baseline.md`](../product-technical-gap-baseline.md).

Each entry MUST identify:

1. the buyer action that is currently blocked or enabled;
2. the exact repository, branch, contract, test, runtime, or GitHub evidence;
3. the authority owner and composition boundary;
4. the smallest next implementation slice;
5. the evidence that will move the entry to `verified`.

Branch names, pull-request checks, review status, releases, and live runtime
observations are separate evidence classes. Evidence from an old commit or a
pre-adaptation base never transfers to a new head. A green check without a
required review, a protected integration, an immutable package, and a release
record is not a shipped-product claim.

The register is a decision aid, not a backlog dump. A gap may be marked
`deferred` only when the current product boundary makes the buyer outcome
explicitly out of scope and the document names the trigger that reopens it.

## Consequences

- Buyers can distinguish what they can install and call from what is only in a
  pull request.
- Review and merge loops have a reproducible next action after each base or
  head change.
- Standards and control claims remain traceable to the authoritative
  references;
  a local test or a plausible document cannot substitute for a release or live
  authorization proof.
- A future presentation module may add Figma, Storybook, and design tokens
  without turning this headless decision plane into a monolith.

## References

International Organization for Standardization, International Electrotechnical
Commission, & Institute of Electrical and Electronics Engineers. (2022).
*Software, systems and enterprise — Architecture description* (ISO/IEC/IEEE
Standard No. 42010:2022). https://doi.org/10.1109/IEEESTD.2022.9938446
