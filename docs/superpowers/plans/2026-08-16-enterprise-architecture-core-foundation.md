# Enterprise Architecture Core Foundation Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or
> superpowers:executing-plans and complete each checkbox with fresh evidence.

**Goal:** Create the first independently reviewable EA Decision Plane baseline.

**Architecture:** PostgreSQL owns normalized facts; OpenAPI and AsyncAPI define
service contracts; Python validation makes repository invariants executable.

**Tech Stack:** PostgreSQL 18, Python 3.11-3.13, JSON contracts, pytest,
coverage.py, uv.

### Task 1: Product boundary and decisions

- [x] Document owning and non-owning responsibilities.
- [x] Record ten accepted ADRs.
- [x] Add APA 7th references and standard traceability.

### Task 2: Normalized database contract

- [x] Add capability, application, interface, technology, lifecycle, evidence,
  identity-link, outbox, and receipt tables.
- [ ] Add assessment, objective, initiative, and scenario tables in later
  independently reviewed milestones.
- [x] Enforce two-word snake-case object names.
- [x] Preserve valid and system time.

### Task 3: API and event baseline

- [x] Add OpenAPI 3.1.1 command surface.
- [x] Add Keyverse OIDC verification contract.
- [x] Add AsyncAPI 3.0.0 CloudEvents publishers.

### Task 4: Executable quality gate

- [x] Add deterministic repository validation.
- [x] Add positive and negative unit tests.
- [x] Run compile, tests, and 100% statement/branch coverage locally.
- [ ] Complete hosted Ruff, PostgreSQL 18.4 migration, lock-resolution, and
  package validation before marking the PR ready for review.
