# Enterprise Architecture Core Foundation Design

## Goal

Establish a reviewable enterprise-architecture system-of-record boundary before
building runtime endpoints or user interfaces.

## Design

The canonical model is a normalized PostgreSQL schema. A small dependency-free
Python package validates repository invariants, OpenAPI, AsyncAPI, and migration
naming. Keyverse provides identity. Service changes publish through a
transactional CloudEvents outbox. Graph and search models are derived.

## Scope

This foundation includes product documents, ten ADRs, SQL migration,
OpenAPI/AsyncAPI, OIDC configuration contract, security and operability
baselines, validation code, and tests. It excludes CRUD runtime, UI, graph
projection, external product adapters, and scenario execution.
