# Standard Traceability

| Decision | Basis | Repository evidence |
|---|---|---|
| Architecture-description terminology | ISO/IEC/IEEE 42010:2022 | PRD, architecture, ADR 0001 |
| UUIDv7 identity | RFC 9562 | defaults, database checks, and canonical-reference schema |
| Structured service events | CloudEvents 1.0.2 | AsyncAPI, outbox, and projection receipt |
| Provenance references | W3C PROV-O | evidence model and ADR 0007 |
| Data-lineage interoperability | OpenLineage | external projection boundary; not yet implemented |
| Bitemporal facts | Product audit requirement | revision, relation, lifecycle, and identity intervals |
| Concurrent interval integrity | PostgreSQL range and exclusion constraints | migration 0005 and PostgreSQL acceptance |
| Tenant data isolation | PostgreSQL row-level security | forced policies and non-superuser acceptance |
