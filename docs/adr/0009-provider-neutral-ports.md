# ADR 0009: Keep external EA and catalog integrations behind ports

- **Status:** Accepted
- **Date:** 2026-08-16

## Decision

Atlan, SAP LeanIX, GitHub, and other providers are adapters to versioned ports.
Their proprietary schemas are not the canonical internal model.

## Consequence

CWL-native and customer-standard deployments can coexist without changing
domain logic.
