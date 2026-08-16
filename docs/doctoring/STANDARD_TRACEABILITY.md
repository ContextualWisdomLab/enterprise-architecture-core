# Standard Traceability

| Decision | Basis | Repository evidence |
|---|---|---|
| Architecture-description terminology and viewpoints | ISO/IEC/IEEE 42010:2022 | PRD, architecture, ADR 0001 |
| UUIDv7 identity | RFC 9562 | UUID defaults/checks, canonical reference projection, PostgreSQL acceptance |
| Canonical JSON contract dialect | JSON Schema Draft 2020-12 | downstream Context Graph dependency boundary; conformance consumption remains gated on its immutable release |
| Structured service events | CloudEvents 1.0.2 | AsyncAPI, transactional outbox, projection receipt; shared envelope consumption remains gated on Context Graph release |
| HTTP API description | OpenAPI 3.2.0 and RFC 9110 | `contracts/openapi.json` health/ready process surface, stdlib server, and repository validator |
| Information-security management | ISO/IEC 27001:2022 and SOC 2 Trust Services Criteria | purpose-bound access, tenant isolation, evidence, and operability controls |
| Privacy information management | ISO/IEC 27701:2019 | accountability identifiers remain visible to authorized reviewers; raw personal attributes stay in Keyverse |
| Message API description | AsyncAPI 3.1.0 | `contracts/asyncapi.json` and repository validator |
| Provenance references | W3C PROV-O plus Context Graph provenance schema | `evidence_record`, canonical reference/digest constraints, same-tenant evidence-URI guard, authoritative/observed evidence constraints in migration 0008, PostgreSQL hostile-input acceptance |
| External subject identity | OpenID Connect Core 1.0 (`iss`, `sub`) plus Keyverse boundary | issuer-qualified `identity_link`, validity exclusion, issuer acceptance tests |
| Data-lineage interoperability | OpenLineage | external projection boundary; ingestion is planned and explicitly not shipped by this foundation |
| Bitemporal facts | Product audit requirement plus PostgreSQL temporal/range semantics | revision, relation, lifecycle, and identity valid/system intervals |
| Concurrent interval integrity | PostgreSQL 18 exclusion constraints | migration 0005 and PostgreSQL overlap acceptance |
| Tenant data isolation | PostgreSQL 18 row-level security | forced policies and non-superuser runtime acceptance; documented as defense-in-depth, not caller-authentication |
| Database readiness connection policy | PostgreSQL 18 libpq connection parameters and environment variables | DSN-to-libpq translation preserves supported TLS, channel-binding, host-selection and session-target parameters; unknown or duplicate parameters fail closed; password remains outside argv |
| Accessible future decision surfaces | WCAG 2.2 | UI is not shipped by this foundation; future graph/matrix/timeline work requires accessible exact-value alternatives |
