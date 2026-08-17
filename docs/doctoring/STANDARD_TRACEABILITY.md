# Standard Traceability

| Decision | Basis | Repository evidence |
|---|---|---|
| Architecture-description terminology and viewpoints | ISO/IEC/IEEE 42010:2022 | PRD, architecture, ADR 0001 |
| UUIDv7 identity | RFC 9562 | UUID defaults/checks, canonical reference projection, PostgreSQL acceptance |
| Canonical JSON contract dialect | JSON Schema Draft 2020-12 | downstream Context Graph dependency boundary; conformance consumption remains gated on its immutable release |
| Structured service events | CloudEvents 1.0.2 | AsyncAPI, transactional outbox, projection receipt; shared envelope consumption remains gated on Context Graph release |
| HTTP API description | OpenAPI 3.2.0 and RFC 9110 | `contracts/openapi.json` health/ready process surface, stdlib server, repository validator |
| Information-security management | ISO/IEC 27001:2022 and SOC 2 Trust Services Criteria | purpose-bound access, tenant isolation, evidence, operability controls |
| Privacy information management | ISO/IEC 27701:2019 | accountability identifiers remain visible to authorized reviewers; raw personal attributes stay in Keyverse |
| Message API description | AsyncAPI 3.1.0 | `contracts/asyncapi.json` and repository validator |
| Provenance references | W3C PROV-O plus Context Graph provenance schema | `evidence_record`, digest/tenant constraints, authoritative/observed evidence guards, hostile-input PostgreSQL acceptance |
| External subject identity | OpenID Connect Core 1.0 (`iss`, `sub`) plus Keyverse boundary | issuer-qualified `identity_link`, validity exclusion, issuer acceptance tests |
| Data-lineage interoperability | OpenLineage | external projection boundary; ingestion is planned and explicitly not shipped by this foundation |
| Bitemporal facts | Architecture audit requirement plus PostgreSQL temporal/range semantics | revision, relation, lifecycle, identity, assessment, objective, initiative, link, milestone, scenario, baseline, object delta, relation delta, transformation, and transformation-history valid/system semantics; ADRs 0004, 0008, 0013, 0014, 0015 |
| Versioned portfolio assessment meaning | 3NF write-model decision plus architecture auditability requirement | ADRs 0002 and 0013, migration 0010, real PostgreSQL scale/framework/evidence acceptance |
| Versioned strategy execution meaning | ISO/IEC/IEEE 42010:2022 plus 3NF/bitemporal auditability decision | ADR 0014, migration 0011, real PostgreSQL objective/initiative/link/milestone acceptance |
| Strategy interval containment and non-overlap | PostgreSQL 18 range and exclusion semantics | migration 0011 semantic triggers and GiST exclusions; `zz_verify_strategy_execution.sql` negative and positive cases |
| Append-preserving strategy decisions | Architecture decision auditability requirement | ADR 0014; semantic-update rejection, one-time supersession tests, append-only scenario continuation |
| Immutable scenario baseline | ISO/IEC/IEEE 42010:2022 decision traceability plus bitemporal audit requirement | ADR 0008; migration 0012 stores separate real-world and system-recording cutoffs, rejects baseline mutation/hard delete, and reconstructs authoritative as-of membership |
| Deterministic ordered scenario projection | ADR 0008 plus PostgreSQL ordering/window semantics | migrations 0012-0013; `project_scenario_objects(uuid)` and `project_scenario_relations(uuid)` apply the highest active sequence per semantic target at target time; SQL acceptance proves later-delta precedence, baseline preservation, truth origin, endpoint integrity, and cross-tenant denial |
| Target-state relation endpoint integrity | ISO/IEC/IEEE 42010:2022 architecture consistency plus PostgreSQL referential/type guards | migration 0013 reuses authoritative relation typing and composes relation intent with final object presence; `zz_verify_scenario_relation_projection.sql` proves dangling requested-present edges remain auditable but not active |
| Governed transformation execution history | ISO/IEC/IEEE 42010:2022 decision traceability plus append-preserving bitemporal auditability | ADR 0015; migration 0014 binds immutable-baseline scenario + remediation initiative and exposes `project_transformation_state(uuid,timestamptz,timestamptz)`; real PostgreSQL acceptance proves independent valid/system cutoffs and immutable history |
| Truth-origin non-promotion across transformation decisions | W3C PROV-O provenance discipline plus ADR 0007 truth-status separation | migration 0014 rejects governed transformation promotion of proposed/inferred parent decisions and rejects approval/execution states on non-authoritative transformations; `zz_verify_transformation_authority_boundary.sql` is the executable regression |
| Concurrent interval integrity | PostgreSQL 18 exclusion constraints | migrations 0005, 0010, 0011, 0014 plus PostgreSQL authoritative-overlap acceptance |
| Tenant data isolation | PostgreSQL 18 row-level security | forced policies and non-superuser runtime/assessment/strategy/scenario/transformation acceptance; defense-in-depth, not caller authentication |
| Database readiness connection policy | PostgreSQL 18 libpq connection parameters and environment variables | DSN-to-libpq translation preserves supported TLS/channel-binding/host-selection/password-file/passwordless/default-socket/session-target parameters; unknown or duplicate parameters fail closed; password remains outside argv |
| Exact-head package SBOM | SPDX 3.0.1; Anchore Syft 1.51.0 | `supply-chain.yml` builds reviewed wheel/sdist, validates SPDX 3.0.1 evidence, computes SHA-256 checksums, uploads exact-head artifacts |
| Protected-main package provenance | SLSA 1.2; GitHub artifact-attestation guidance | protected-main-only attestation downloads exact-head package evidence and uses immutably pinned `actions/attest`; PR heads never inherit signed provenance claims |
| Accessible future decision surfaces | WCAG 2.2 | UI is not shipped by this milestone; future graph/matrix/timeline work requires accessible exact-value alternatives and export evidence |
