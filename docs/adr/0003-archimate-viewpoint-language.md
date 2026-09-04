# ADR 0003: ArchiMate 4 viewpoint language

**Status:** Accepted

## Context

ISO/IEC/IEEE 42010:2022 requires architecture viewpoints and model kinds so an architecture description can address stakeholder concerns (International Organization for Standardization, International Electrotechnical Commission, & Institute of Electrical and Electronics Engineers, 2022). This plane needs a shared viewpoint and modeling language without taking ownership of employment truth or psychometric kernels.

The current ArchiMate standard is **ArchiMate® 4 Specification** (document C260), a standard of The Open Group, published 27 April 2026, US ISBN 1-957866-75-8, status adopted. The official catalog records that C260 supersedes C226 (The Open Group, 2026). No DOI is published for C260; the canonical locator is the official Open Group catalog URL.

ArchiMate 4 remains an open modeling language for describing, analyzing, and visualizing relationships among business domains. Relative to 3.2, the official catalog records that the term *layer* is replaced by *domain*, behavior elements are merged across former layers, and several 3.2 elements (including gap) are removed (The Open Group, 2026).

ArchiMate® 3.2 Specification (C226, 19 October 2022) is the superseded 3.x edition (The Open Group, 2022). It is interoperability context for existing 3.2 models and tools. It is not the governing current standard.

Viewpoint models must preserve authority boundaries: Orgmetra owns employment truth; fast-mlsirm owns psychometric numerical kernels.

## Decision

Enterprise Architecture Core uses the current ArchiMate® 4 Specification (C260) as its viewpoint and model-kind language for architecture descriptions.

- Viewpoints may show business, application, technology, motivation, and implementation-and-migration concerns, expressed in ArchiMate 4 domain terms.
- Elements that represent people, employment, jobs, positions, or assignments are references to Orgmetra. This plane does not become the HRIS.
- Elements that represent psychometric estimation, item-response kernels, or recovery diagnostics are references to fast-mlsirm. This plane does not reimplement those kernels.
- Hosts with existing ArchiMate 3.2 artifacts may map those models for interchange. New decision records in this plane use ArchiMate 4.

## Consequences

- Architecture views in this plane share one current viewpoint vocabulary: ArchiMate 4.
- A viewpoint that includes Orgmetra or fast-mlsirm does not transfer write authority to this plane.
- Hosts consume viewpoint contracts published here. They do not need an ArchiMate tool checkout of a sibling repository.
- Superseded 3.2 language is not treated as current requirements.

## References

International Organization for Standardization, International Electrotechnical Commission, & Institute of Electrical and Electronics Engineers. (2022). *Software, systems and enterprise — Architecture description* (ISO/IEC/IEEE Standard No. 42010:2022). https://doi.org/10.1109/IEEESTD.2022.9938446

The Open Group. (2022). *ArchiMate® 3.2 Specification* (C226). https://publications.opengroup.org/c226

The Open Group. (2026). *ArchiMate® 4 Specification* (C260). https://publications.opengroup.org/standards/archimate/c260
