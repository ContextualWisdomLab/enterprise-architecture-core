# ADR 0002: Target-state, capability, and transformation decision records

**Status:** Accepted

## Context

Operators need durable records for target-state architecture, business capability, and transformation work. Those records must stay in this plane so specialist products are not forced to become enterprise-architecture systems of record.

The current TOGAF Standard is **The TOGAF® Standard, 10th Edition** (document C220), a standard of The Open Group. The official catalog records Technical Corrigendum 1 applied in May 2025 and lists the edition as adopted, US ISBN 1-947754-90-4, published 19 May 2025 (The Open Group, 2025). The standard is divided into TOGAF Fundamental Content and TOGAF Series Guides. Fundamental Content includes Introduction and Core Concepts, the Architecture Development Method (ADM), ADM Techniques, Applying the ADM, Architecture Content, and Enterprise Architecture Capability and Governance. Series Guides listed on the same official catalog include Business Capabilities, Version 2; Business Capability Planning; Digital Technology Adoption: A Guide to Readiness Assessment and Roadmap Development; and Microservices Architecture (MSA) (The Open Group, 2025).

This plane uses that official edition. It does not invent a private TOGAF variant, and it does not treat withdrawn or unofficial copies as current.

## Decision

Target-state, capability, and transformation decision records in Enterprise Architecture Core are grounded in the current TOGAF Standard, 10th Edition (C220), including Technical Corrigendum 1 as published by The Open Group.

- **Target-state** records express intended architecture content for an agreed scope and time horizon.
- **Capability** records express business capabilities and capability-planning decisions.
- **Transformation** records express roadmap, work-package, and change-decision content that moves from baseline toward target.

The official Open Group catalog URL is the citation path. Hosts consume the resulting decision records through contracts published by this repository. Alternate official locators are in [docs/REFERENCES.md](../REFERENCES.md).

## Consequences

- ADM-aligned content (baseline, target, gap, roadmap) lives here as decision records, not as copies of Orgmetra employment rows or fast-mlsirm numerical kernels.
- Capability language follows the official TOGAF capability Series Guides listed on C220. This plane does not redefine capability ownership for HRIS or psychometric computation.
- Transformation records may reference foreign systems by canonical identifier. They do not require those systems’ source trees to be present.
- Operators evaluate this plane against the official TOGAF Standard catalog entry, not against unofficial summaries.

## References

The Open Group. (2025). *The TOGAF® Standard, 10th Edition* (C220). https://publications.opengroup.org/c220
