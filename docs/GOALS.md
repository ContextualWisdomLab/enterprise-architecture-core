# Goals

## Current goal

Make the foundation buyer-operable: a named `enterprise-architecture-core`
process, truthful `/health` and `/ready` contracts, a committed dependency
lock, and an explicit connector catalog for the highest-leverage owned
neighbors.

## Accepted constraints

- This repository owns architecture and transformation facts only.
- LLM or inferred proposals never become authoritative without review.
- Runtime CRUD remains unpublished until Keyverse-verified command handlers
  exist.
- Storybook and design tokens wait for a presentation module.

## Next loop

1. Keep PR #1 checks green and fold reviewed foundation integrity into main
   after branch protection exists.
2. Add purpose-bound command functions that bind verified Keyverse claims
   before any table access.
3. Publish the first transactional outbox event that validates against the
   shared Context Graph envelope.
4. Consume Semantic Data Portal, pg-erd-cloud, and LineageWeave references
   through the connector catalog without opening SQL paths.
