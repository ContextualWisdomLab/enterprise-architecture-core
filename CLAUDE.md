# Enterprise Architecture Core Development Context

Follow `AGENTS.md`, the accepted ADRs, and the central ContextualWisdomLab
`.github` governance.

Preserve these boundaries:

- `enterprise-architecture-core`: capability, application, technology,
  interface, lifecycle, assessment, objective, initiative, scenario.
- `semantic-data-portal`: Data/AI context, glossary, lineage, product contract,
  trust, and certification.
- `pg-erd-cloud`: observed physical database/schema evidence.
- `LineageWeave`: inferred or proposed lineage only.

Do not add an arbitrary meta-model editor, Cypher write API, or LLM auto-approval
path in the initial product.
