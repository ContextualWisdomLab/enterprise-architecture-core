# Storybook Inventory

This repository is the authoritative write-model and contract service for
enterprise architecture facts. It does not currently ship an executable visual
decision-plane UI. Every visualization below is therefore `planned_ui`, not
shipped product evidence. Documentation diagrams do not satisfy the UI delivery
gate.

## Current inventory

| Surface | Status | Next action |
|---|---|---|
| Process probes (`/health`, `/ready`) | Implemented HTTP JSON | Start `ea-core` and call the probes before routing traffic |
| Domain command forms | `planned_ui` | Keep them out of OpenAPI until Keyverse-verified handlers exist; add forms only with explicit authorized commands |
| Capability Map / Application Matrix | `planned_ui` | Render canonical object identities and relations with exact-value table/tree alternatives; coordinates stay presentation-only |
| Technology Risk / Impact Path | `planned_ui` | Distinguish direct, inferred/transitive and proposed relations with source truth, time and provenance; traversal must not depend on layout |
| Scenario Compare / Current→Target Architecture | `planned_ui` | Keep current facts separate from proposed/approved target state and derive deterministic deltas from EA domain services |
| Transformation Timeline / Roadmap | `planned_ui` | Separate effective, recorded and planned time; any future drag action must issue an explicit authorized plan command |
| Evidence Drawer | `planned_ui` | Drill down from architecture claims to canonical repository/ref/schema/version/evidence provenance without color-only truth status |
| Design tokens / Storybook | `planned_ui` | Introduce them with the first executable presentation slice and retain browser-level accessibility and interaction evidence |

## UI delivery gate

The first material UI slice activates Figma/Product Design plus Storybook and
must prove current-head browser behavior for canonical identity, relation/truth
and provenance, bitemporal current/target semantics, cycle/disconnected/partial
states, selection and drill-down, pointer/touch/keyboard interaction,
zoom/pan/filter/time-window behavior, responsive screenshots, WCAG 2.2 AA exact
value alternatives, large-data performance and lifecycle cleanup. Unsupported
items are recorded as `NOT_APPLICABLE` or `KNOWN_LIMITATION`; a failed applicable
item is not merge-ready.

Graph coordinates, viewport, selection, expanded tree state, timeline scroll and
chart pixels remain presentation state. Canonical references, relations, truth
status, lifecycle, effective/system time, evidence/provenance and architecture
decision/scenario status remain domain or contract truth and can change only
through the governed application/command boundary.
