# ADR 0003: ArchiMate 3.x viewpoint language

**Status:** Accepted

## Context

ISO/IEC/IEEE 42010:2022 requires architecture viewpoints and model kinds so an architecture description can address stakeholder concerns (International Organization for Standardization, International Electrotechnical Commission, & Institute of Electrical and Electronics Engineers, 2022). This plane needs a shared viewpoint language for business, application, technology, motivation, and implementation-and-migration views without taking ownership of employment truth or psychometric kernels.

The current ArchiMate 3.x Specification is **ArchiMate® 3.2 Specification** (document C226), a standard of The Open Group, published 19 October 2022, US ISBN 1-957866-02-4, status adopted, superseding C197 (The Open Group, 2022). The official catalog describes ArchiMate as an open modeling language for describing, analyzing, and visualizing relationships among business domains.

The Open Group later published **ArchiMate® 4 Specification** (document C260) on 27 April 2026, US ISBN 1-957866-75-8, which the official catalog records as superseding C226 (The Open Group, 2026). This ADR grounds viewpoint language in the current 3.x specification as required for this plane. ArchiMate 4 is cited only as the later official Open Group edition, not as a replacement of the 3.x grounding in this decision.

Viewpoint models must preserve authority boundaries: Orgmetra owns employment truth; fast-mlsirm owns psychometric numerical kernels.

## Decision

Enterprise Architecture Core uses the current ArchiMate 3.x Specification — ArchiMate 3.2 (C226) — as its viewpoint and model-kind language for architecture descriptions.

- Viewpoints may show business, application, technology, motivation, and implementation-and-migration concerns.
- Elements that represent people, employment, jobs, positions, or assignments are references to Orgmetra. This plane does not become the HRIS.
- Elements that represent psychometric estimation, item-response kernels, or recovery diagnostics are references to fast-mlsirm. This plane does not reimplement those kernels.
- Official The Open Group catalog URLs are the citation path for both the 3.2 grounding and the later 4 edition.

## Consequences

- Architecture views in this plane are described in ArchiMate 3.x terms so hosts share one viewpoint vocabulary.
- A viewpoint that includes Orgmetra or fast-mlsirm does not transfer write authority to this plane.
- Hosts consume viewpoint contracts published here. They do not need an ArchiMate tool checkout of a sibling repository.
- If a later increment adopts ArchiMate 4 notation, that change requires its own ADR. Until then, 3.2 remains the viewpoint language.

## References

International Organization for Standardization, International Electrotechnical Commission, & Institute of Electrical and Electronics Engineers. (2022). *Software, systems and enterprise — Architecture description* (ISO/IEC/IEEE Standard No. 42010:2022). https://doi.org/10.1109/IEEESTD.2022.9938446

The Open Group. (2022). *ArchiMate® 3.2 Specification* (C226). https://publications.opengroup.org/c226

The Open Group. (n.d.). *ArchiMate®, a standard of The Open Group*. https://publications.opengroup.org/standards/archimate

The Open Group. (2026). *ArchiMate® 4 Specification* (C260). https://publications.opengroup.org/standards/archimate/c260
