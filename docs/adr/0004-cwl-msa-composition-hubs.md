# ADR 0004: CWL MSA “따로 또 같이” and composition hubs

**Status:** Accepted

## Context

ContextualWisdomLab ships specialist products as separately deployable services. Folding those products into one repository, or requiring a host to check out siblings to call a neighbor, collapses ownership and creates a hidden monolith.

The TOGAF Standard, 10th Edition lists a Series Guide on Microservices Architecture (MSA) among the official configuration guides for the Fundamental Content (The Open Group, 2025). CWL applies that independently-deployable service idea as **따로 또 같이**: each service is designed to be operable and callable on its own, and allowed hubs may compose it through published contracts once a deployable runtime and versioned machine-readable contracts are released.

Naruon is the customer-owned mail, calendar, and file control plane. Gyeot (곁) is the on-device wellness composition hub. Both are allowed to compose this plane. Those links are supported. They are not a reason to merge repositories or to require this service to vendor either hub.

ISO/IEC/IEEE 42010:2022 likewise treats an architecture description as a work product about an entity of interest, not as a requirement that every related entity share one implementation (International Organization for Standardization, International Electrotechnical Commission, & Institute of Electrical and Electronics Engineers, 2022).

## Decision

Enterprise Architecture Core is designed to be independently operable and independently callable. At this ADR's protected-branch baseline, this repository exposes documentation only; deployment and invocation become supported shipped behavior only when this repository releases a deployable application runtime together with versioned machine-readable contracts.

1. A buyer or operator can consume the current documentation from this repository alone. Runtime use requires a released runtime and its published contracts.
2. [Naruon](https://github.com/ContextualWisdomLab/naruon) and [gyeot](https://github.com/ContextualWisdomLab/gyeot) may compose this plane as hubs once the runtime contract exists. Hub wiring lives in the hub repository.
3. When released, hosts consume contracts published by this repository. They must not be required to check out sibling CWL repositories, add those repositories as submodules, or read sibling application tables to call this plane.
4. Orgmetra remains the employment-truth authority. fast-mlsirm remains the psychometric numerical-kernel authority. Composition does not move those authorities into this plane or into a hub.

## Consequences

- The current protected baseline is documentation-only. Active feature branches or pull requests are not shipped runtime evidence.
- Once released, this repository publishes the runtime contracts hosts use. Sibling checkouts are not part of the integration path.
- Naruon and gyeot links stay in the buyer and operator README as allowed composition hubs, conditional on the corresponding released integration contract.
- After runtime release, a hub failure must not take down this plane's independent operation, and this plane's absence must not take down a hub's own product loop.
- Future API, event, and schema artifacts are released from this repository. They are not reconstructed from another product's working tree.

## References

International Organization for Standardization, International Electrotechnical Commission, & Institute of Electrical and Electronics Engineers. (2022). *Software, systems and enterprise — Architecture description* (ISO/IEC/IEEE Standard No. 42010:2022). https://doi.org/10.1109/IEEESTD.2022.9938446

The Open Group. (2025). *The TOGAF® Standard, 10th Edition* (C220). https://publications.opengroup.org/c220
