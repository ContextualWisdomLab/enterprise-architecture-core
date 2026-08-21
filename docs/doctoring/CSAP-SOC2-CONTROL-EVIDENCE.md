# CSAP and SOC 2 control evidence pack

**Status:** preparation evidence only<br>
**Snapshot:** 2026-08-21<br>
**Scope:** Enterprise Architecture Core repository and its proposed runtime boundary

This is a control crosswalk and evidence index. It is not a CSAP certificate,
SOC 2 report, audit opinion, or claim of compliance. CSAP certification is an
external assessment of a cloud service against the applicable Korean security
certification criteria. A SOC 2 report is an attestation engagement against
the applicable AICPA Trust Services Criteria. Neither outcome can be created
by this file.

## Evidence vocabulary

| State | Meaning | Buyer interpretation |
| --- | --- | --- |
| `observed` | Reproduced on the protected branch or an authenticated live service at the recorded snapshot | Evidence exists for that exact boundary only |
| `candidate` | Reproduced on an unmerged pull-request head | Not integrated, released, or available to a buyer |
| `planned` | Required evidence or control is not present in the inspected boundary | Open acceptance work |
| `exception` | A known failure, stale result, or ownership dependency prevents a positive claim | Remediation or an explicit risk decision is required |

The pack uses `candidate` for implementation-branch evidence even when the
local test is green. A green local test, a draft pull request, or a scheduled
workflow is not a protected integration or certification result.

## Boundary and control ownership

| Boundary | Owner in this pack | Evidence responsibility | Cadence |
| --- | --- | --- | --- |
| Architecture decisions, schema, and decision APIs | EA Core maintainers | ADRs, migrations, contract tests, authorization tests | Every change and release candidate |
| Build, dependency, SBOM, and release provenance | Repository release owner | Protected workflow results, signed attestations, immutable artifact digests | Every release candidate and release |
| Runtime availability and incident response | Runtime operator | Authenticated health/readiness, logs, incident record, recovery exercise | Deploy, incident, and scheduled exercise |
| Customer identity and external source truth | Owning identity or source product | Signed receipt, authority, tenant, replay, and deletion evidence | Every inbound integration and source change |
| CSAP/SOC 2 assessment | Independent assessor and service management | Formal scope, period, population, samples, exceptions, and report/certificate | Assessment-defined period |

No personal names, credentials, customer identifiers, or production data are
stored in this public evidence pack. The control owner is a role, not an
individual attribution.

## Crosswalk

The mappings below are deliberately outcome-oriented. NIST CSF 2.0 is a risk
management taxonomy, not a certification checklist. AICPA TSC is the criteria
source for an eventual SOC 2 engagement. The CSAP column identifies the
relevant control area at a preparation level; the applicable service type,
grade, and assessment scope must be confirmed before an application.

| ID | NIST CSF 2.0 | AICPA TSC | CSAP preparation area | Current evidence locator | State | Exception / next acceptance |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | GV.OC, GV.RM, GV.PO | CC1, CC2 | Management system and security policy | [`docs/adr/0005-product-technical-gap-baseline.md`](../adr/0005-product-technical-gap-baseline.md), [`docs/product-technical-gap-baseline.md`](../product-technical-gap-baseline.md), ADR 0006 | `candidate` | Protected integration and a named service scope are still absent. |
| SEC-02 | ID.AM, ID.RA | CC2, CC3 | Asset, data, and risk inventory | [`docs/DATA_MODEL.md`](https://github.com/ContextualWisdomLab/enterprise-architecture-core/blob/ee9d5bcb38507b32c86486dce3480733ab72c4ce/docs/DATA_MODEL.md), [`docs/THREAT_MODEL.md`](https://github.com/ContextualWisdomLab/enterprise-architecture-core/blob/ee9d5bcb38507b32c86486dce3480733ab72c4ce/docs/THREAT_MODEL.md) on implementation candidates; migration and acceptance evidence | `candidate` | Re-run the inventory against the exact protected release and record residual risks. |
| SEC-03 | PR.AA, PR.DS | CC6, CC7 | Identity, access control, tenant separation, and data protection | Purpose-bound API and forced-RLS acceptance on implementation candidates; [`docs/SECURITY.md`](https://github.com/ContextualWisdomLab/enterprise-architecture-core/blob/ee9d5bcb38507b32c86486dce3480733ab72c4ce/docs/SECURITY.md) | `candidate` | Repeat negative authorization and direct-table-access tests after protected integration and live deployment. |
| SEC-04 | PR.PS, GV.SC | CC8, CC9 | Change, supplier, dependency, and software supply-chain control | [`.github/workflows/supply-chain.yml`](https://github.com/ContextualWisdomLab/enterprise-architecture-core/blob/ee9d5bcb38507b32c86486dce3480733ab72c4ce/.github/workflows/supply-chain.yml), [PR34 release-attestation candidate](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/34); re-fetch its exact current head, verifier source, and terminal checks before using candidate evidence | `candidate` | Protected integration, independent same-head review, signed release artifact, and verifier replay remain required. |
| SEC-05 | DE.CM, DE.AE | CC7, CC8 | Monitoring, detection, and event/log integrity | [`docs/OPERABILITY.md`](https://github.com/ContextualWisdomLab/enterprise-architecture-core/blob/ee9d5bcb38507b32c86486dce3480733ab72c4ce/docs/OPERABILITY.md), runtime-readiness workflow, health/readiness probes on implementation candidates | `candidate` | An authenticated deployed runtime and retained operational records are not observed. |
| SEC-06 | RS.MA, RS.CO, RS.AN | CC7, CC9 | Incident handling and notification | [`docs/OPERABILITY.md`](https://github.com/ContextualWisdomLab/enterprise-architecture-core/blob/ee9d5bcb38507b32c86486dce3480733ab72c4ce/docs/OPERABILITY.md), [`docs/THREAT_MODEL.md`](https://github.com/ContextualWisdomLab/enterprise-architecture-core/blob/ee9d5bcb38507b32c86486dce3480733ab72c4ce/docs/THREAT_MODEL.md) | `planned` | Exercise an incident path, preserve evidence, assign notification responsibility, and record the result. |
| SEC-07 | PR.IR, RC.RP, RC.CO | A1, CC9 | Availability, continuity, backup, and recovery | [`docs/TRD.md`](https://github.com/ContextualWisdomLab/enterprise-architecture-core/blob/ee9d5bcb38507b32c86486dce3480733ab72c4ce/docs/TRD.md), PostgreSQL migration/acceptance and runtime candidate evidence | `candidate` | Production backup/restore, recovery objective measurements, and an authorized exercise are missing. |
| SEC-08 | PR.DS, DE.CM | CC8, PI1, C1, P1 | Processing integrity, confidentiality, and privacy | Bitemporal constraints, receipt-bound truth status, tenant/RLS tests, and purpose-bound read contracts on candidate heads | `candidate` | Map retention, deletion, subject-rights, and customer-specific processing purposes before any audit scope. |
| SEC-09 | GV.SC, ID.RA | CC9, C1 | External providers and shared responsibility | [`docs/adr/0012-ecosystem-connectors.md`](https://github.com/ContextualWisdomLab/enterprise-architecture-core/blob/ee9d5bcb38507b32c86486dce3480733ab72c4ce/docs/adr/0012-ecosystem-connectors.md) on implementation candidates; connector catalog boundary | `planned` | Record each provider, service type, subprocessor, contract, responsibility split, and current assurance evidence. |
| SEC-10 | GV.OV, ID.IM | CC4, CC5 | Control operation, exception management, and improvement | This matrix plus exact-head evidence packets and the protected-merge gate | `candidate` | Add retained periodic reviews, exception approvals, and an independent assessment population. |

## Acceptance rule

This pack becomes audit-preparation evidence only when every row has:

1. a defined in-scope service, system, and period;
2. an accountable role and an approved operating procedure;
3. executable, operational, or independently retained evidence at the same
   protected/released boundary;
4. a documented exception, owner, due date, and risk decision when evidence is
   incomplete; and
5. an assessor-confirmed population and sampling method where an attestation
   or certification requires it.

Until those conditions are met, rows remain `candidate`, `planned`, or
`exception`. The repository must not publish `compliant`, `CSAP certified`, or
`SOC 2 certified` as a substitute.

## References

See [`docs/REFERENCES.md`](../REFERENCES.md) for the APA 7th bibliography and
official locators for NIST CSF 2.0, the AICPA Trust Services Criteria, and the
Korean CSAP governing rule.
