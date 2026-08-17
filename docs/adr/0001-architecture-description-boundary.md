# ADR 0001: Architecture-description boundary

**Status:** Accepted

## Context

Buyers and operators need a single place that records what the CWL enterprise architecture *is described as*, without claiming to *be* the architecture of every specialist product. ISO/IEC/IEEE 42010:2022 distinguishes the architecture of an entity of interest from the architecture description (AD) that expresses that architecture. It specifies requirements for architecture descriptions, architecture description frameworks, architecture description languages, viewpoints, and model kinds. It does not specify the processes, methods, notations, or tools used to create an AD, and it does not specify requirements for the entity of interest itself (International Organization for Standardization, International Electrotechnical Commission, & Institute of Electrical and Electronics Engineers, 2022).

The final standard is **ISO/IEC/IEEE 42010:2022**, *Software, systems and enterprise — Architecture description*, published 7 November 2022, DOI [10.1109/IEEESTD.2022.9938446](https://doi.org/10.1109/IEEESTD.2022.9938446). IEEE SA records the same edition as IEEE/ISO/IEC 42010-2022, board-approved 21 September 2022, superseding 42010-2011 (Institute of Electrical and Electronics Engineers, 2022). The 2020 draft is not the final standard and is not cited here.

This plane must also keep employment truth in Orgmetra and psychometric numerical kernels in fast-mlsirm. An architecture description may *refer* to those systems. It must not absorb them.

## Decision

Enterprise Architecture Core is the CWL architecture-description and architecture-decision plane. It owns architecture descriptions, viewpoints, and model kinds for enterprise and transformation concerns. It does not own the architecture of Orgmetra, fast-mlsirm, or other specialist products, and it does not become their system of record.

Conformance language for this plane follows the final 2022 edition only. Drafts, including the 2020 draft of 42010, are not treated as published requirements.

## Consequences

- Stakeholder concerns, viewpoints, and architecture views stay explicit in this repository’s decision records.
- Descriptions may hold canonical references to foreign authorities. They do not copy foreign catalog or employment state, and they do not open foreign application tables.
- Orgmetra remains the employment-truth authority. fast-mlsirm remains the psychometric numerical-kernel authority.
- Later machine-readable contracts published from this repository express the AD boundary. They do not require sibling repository checkouts.

## References

Institute of Electrical and Electronics Engineers. (2022). *IEEE/ISO/IEC 42010-2022: IEEE/ISO/IEC international standard for software, systems and enterprise—Architecture description*. IEEE Standards Association. https://standards.ieee.org/ieee/42010/6846/

International Organization for Standardization. (2022). *ISO/IEC/IEEE 42010:2022 Software, systems and enterprise — Architecture description*. https://www.iso.org/standard/74393.html

International Organization for Standardization, International Electrotechnical Commission, & Institute of Electrical and Electronics Engineers. (2022). *Software, systems and enterprise — Architecture description* (ISO/IEC/IEEE Standard No. 42010:2022). https://doi.org/10.1109/IEEESTD.2022.9938446
