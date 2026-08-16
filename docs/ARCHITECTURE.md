# Architecture

## Bounded contexts

```text
Keyverse
   │ OIDC identity
   ▼
Enterprise Architecture Core
   │ authoritative CloudEvents
   ├────────────► Semantic Data Portal / shared graph projection
   │
   ├◄──────────── pg-erd-cloud observed schema evidence
   └◄──────────── LineageWeave inferred relation proposals
```

## Ownership

Enterprise Architecture Core owns:

- business capability;
- application and application interface;
- technology component, version, provider, and lifecycle;
- enterprise architecture relationship;
- portfolio assessment;
- objective, initiative, scenario, and transformation decision.

It does not own datasets, columns, data contracts, physical schema snapshots,
inferred narrative lineage, credentials, or project execution status.

## Write and read models

The canonical write model is normalized PostgreSQL. Commands update business
facts and insert outbox events atomically. Consumers build graph, search, or
analytics projections from the events. A projection can be deleted and rebuilt
without changing authoritative history.

## Temporal semantics

Object revisions, relationships, identity links, and lifecycle intervals carry
real-world validity and system recording intervals. Queries may therefore ask
both what was valid at a date and what the system knew at a historical cutoff.

## Scenario direction

A future target state is represented as an immutable baseline plus ordered
scenario changes. Draft scenarios never mutate current authoritative state.
Execution closes old intervals and creates new facts through normal commands.
