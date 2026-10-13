# Enterprise Architecture Core Foundation Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or
> superpowers:executing-plans and complete each checkbox with fresh evidence.

**Goal:** Create independently reviewable Enterprise Architecture Decision Plane increments.

**Architecture:** PostgreSQL owns normalized authoritative facts; OpenAPI and AsyncAPI define service/event contracts; Python validation makes repository invariants executable. Neighbor CWL products integrate only through published contracts and remain separate authorities.

**Tech Stack:** PostgreSQL 18, Python 3.11-3.14, JSON contracts, pytest, coverage.py, uv.

### Task 1: Product boundary and decisions

- [x] Document owning and non-owning responsibilities.
- [x] Record accepted architecture decisions and keep the ADR set code-current.
- [x] Add APA 7th references and standard traceability.

### Task 2: Normalized database contract

- [x] Add capability, application, interface, technology, lifecycle, evidence, identity-link, outbox, and receipt tables.
- [x] Add normalized framework, scale, dimension, cycle, and object-assessment tables in the independently reviewed portfolio-assessment milestone.
- [x] Add normalized strategy objective, remediation initiative, objective-contribution link, and initiative-milestone tables in the strategy-execution milestone.
- [ ] Add immutable-baseline scenario, ordered scenario-delta, approved transformation, and transformation-history tables in a later independently reviewed milestone.
- [x] Enforce descriptive two-or-more-word snake-case database object names.
- [x] Preserve valid time, system-recorded time, truth origin, provenance, and tenant isolation.

### Task 3: API and event baseline

- [x] Add truthful OpenAPI 3.2.0 health/readiness process surface.
- [x] Add Keyverse OIDC verification contract without publishing unimplemented domain commands.
- [x] Add AsyncAPI 3.1.0 CloudEvents publishers.
- [ ] Add cross-domain impact/query command surfaces only after protected identity, authorization, and scenario semantics are executable.

### Task 4: Executable quality gates

- [x] Add deterministic repository validation.
- [x] Add positive and negative unit tests.
- [x] Run compile, tests, and 100% statement/branch coverage on owned Python production code.
- [x] Establish real PostgreSQL clean-install, RLS, temporal, evidence, and migration-upgrade acceptance through migration 0010.
- [ ] Re-prove hosted Python 3.11-3.14 coverage, PostgreSQL 18.4 clean install and 0010->0011 upgrade, runtime RLS, package, SBOM, and runtime-readiness evidence on the exact final strategy-execution head before marking that PR review-ready.
- [ ] After each parent PR integrates, retarget/revalidate descendants against the new live protected base; never transfer predecessor-head evidence.
