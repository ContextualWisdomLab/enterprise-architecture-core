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
- versioned portfolio assessment;
- objective, initiative, scenario, and transformation decision.

It does not own datasets, columns, data contracts, physical schema snapshots,
inferred narrative lineage, credentials, or project execution status.

## Write and read models

The canonical write model is normalized PostgreSQL. Inventory objects do not
carry duplicated portfolio scores: framework/version, scale/value, dimension,
cycle, and object-assessment meaning are normalized and joined at the
transactional boundary. Commands update business facts and insert outbox events
atomically. Consumers build graph, search, matrix, or analytics projections from
the events. A projection can be deleted and rebuilt without changing
authoritative history.

Append-only evidence, inbound receipts, outbox events, and transformation
history expose the same deterministic tenant-derived 16-bucket routing
contract. Their hot-write indexes and storage headroom prepare a future
partition cutover without making the current service depend on physical
partition names or weakening tenant isolation.

## Temporal and truth semantics

Object revisions, relationships, identity links, lifecycle intervals,
assessment frameworks/cycles, and object assessments carry real-world validity
and system recording semantics. Queries may therefore ask both what was valid
at a date and what the system knew at a historical cutoff. Assessment truth
uses the same explicit origin vocabulary as architecture assertions:
authoritative or observed scores require evidence, while inferred/proposed
scores remain reviewable without silently becoming authoritative.

## Process surface

The installable process binds `0.0.0.0:$PORT` and implements `GET /health`
then `GET /ready`. Domain commands stay unpublished until a purpose-bound
Keyverse boundary exists. Neighbor systems connect through
`contracts/connectors/ecosystem.json`.

## Scenario direction

A future target state is represented as an immutable baseline plus ordered
scenario changes. Draft scenarios never mutate current authoritative state.
Execution closes old intervals and creates new facts through normal commands.
