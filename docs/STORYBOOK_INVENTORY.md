# Storybook Inventory

This repository is the authoritative write-model and contract service for
enterprise architecture facts. It does not ship a visual decision-plane UI in
this release.

## Current inventory

| Surface | Status | Next action |
|---|---|---|
| Process probes (`/health`, `/ready`) | Implemented HTTP JSON | Start `ea-core` and call the probes before routing traffic |
| Domain command forms | Not shipped | Keep them out of OpenAPI until Keyverse-verified handlers exist |
| Capability, application, and technology cards | Not shipped | Build them in a presentation module that consumes this API |
| Current/target scenario canvas | Not shipped | Use scenario tables here; render later with accessible exact values |
| Design tokens | Not shipped | Define tokens in the presentation module when Storybook is introduced |

## When Storybook applies

Add Storybook and design tokens only in a presentation module that renders
repeated web objects such as inventory cards, relation chips, and evidence
status. This service remains headless so it can run alone or be imported as a
module. WCAG 2.2 exact-value alternatives are required before any graph or
timeline visualization is added.
