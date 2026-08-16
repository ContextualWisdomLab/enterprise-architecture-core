# ADR 0008: Represent target architecture as scenario deltas

- **Status:** Accepted
- **Date:** 2026-08-16

## Decision

A scenario records an immutable baseline cutoff and an ordered sequence of
changes rather than copying the entire architecture graph.

## Consequence

Current truth remains untouched while alternative target states can be compared
deterministically.
