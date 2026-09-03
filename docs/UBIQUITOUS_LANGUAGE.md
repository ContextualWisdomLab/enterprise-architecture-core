# Ubiquitous Language

These terms are the domain language for the Enterprise Architecture Decision Plane. API, SQL, events, tests and buyer-facing explanations should use them consistently. External product concepts are translated through an Anti-Corruption Layer rather than copied wholesale into the EA model.

| Term | Meaning |
| --- | --- |
| Business Capability | A stable statement of what the enterprise must be able to do, independent of a particular application implementation. |
| Application | A software system or product that realizes/supports capabilities and participates in typed architecture relations. |
| Interface | An owned EA representation of an application/system interaction point. It is not a physical database schema. |
| Technology Component | A technology used by an application or architecture element, separate from a particular version/provider lifecycle record. |
| Technology Version | A versioned technology fact with lifecycle/effective-time semantics used for impact and target-state decisions. |
| Technology Provider | The provider/vendor context for a technology component/version. |
| Organization Context | The organizational owner, stakeholder or operating context used in EA decisions. It is not authentication identity by itself. |
| Architecture Relation | A typed, tenant-safe relation between EA objects with explicit temporal and truth-origin semantics. |
| Lifecycle | The effective state/history of an architecture object or technology version, including time-sensitive risk such as EOL. |
| Truth Origin | The epistemic status of evidence: authoritative, observed, inferred, proposed, superseded or rejected as applicable. No ingestion path silently promotes inferred/proposed evidence. |
| Valid Time | When an architecture fact is asserted to hold in the real world. |
| System Time | When a fact/version is recorded by the EA system. It is distinct from Valid Time. |
| Portfolio Assessment | A versioned EA evaluation used to support a portfolio decision. It can consume accepted evidence but remains an EA-owned decision artifact. |
| Objective | An intended architecture/business outcome that can be advanced by initiatives. |
| Initiative | A governed body of work intended to move architecture toward an objective/target state. |
| Milestone | A versioned checkpoint within an initiative/transformation plan. |
| Scenario Baseline | An immutable starting architecture snapshot/reference used by scenario projection. |
| Scenario Delta | An ordered proposed change applied deterministically to a Scenario Baseline. It does not mutate the baseline. |
| Scenario Projection | The deterministic candidate state produced from an immutable baseline plus ordered deltas. |
| Transformation | An approved/executed architecture change whose history is retained rather than hard-deleted. |
| Evidence Receipt | A durable record binding an EA projection/decision input to the exact upstream evidence identity and truth/provenance context. |
| Projection Receipt | The admission identity retained with an admitted Context Assertion projection: source authority, CloudEvent identity (`id`, `source`, `type`, `subject`, `time`, `dataschema`), exact schema/profile/admission versions and provenance. It proves what was admitted without transferring source authority to EA. |
| Cross-Domain Projection | The minimum normalized EA-side representation of foreign evidence required for EA decisions. Projection is not a duplicate system of record. |
| Impact Path | The explainable chain from a triggering technology/lifecycle change through affected applications/capabilities and accepted external evidence to a decision/action. |
| Remediation Initiative | An initiative created or selected to mitigate an identified architecture/technology risk. |
| Target-State Plan | A proposed, evidence-backed sequence of architecture actions leading from current state to a candidate target state. |
| Approval | An explicit authorized state transition that accepts a proposal/plan; reading or proposing does not imply approval. |
| Verification | Evidence-backed confirmation that an approved target-state action achieved the required condition. |
| Recheck / Reverification | A later evidence refresh that preserves prior history and can change the current decision state only through the defined command/invariant. |
| Replan | Creation of a revised plan after new evidence or failed verification, preserving the causation/history of the prior plan. |
| Transactional Outbox | The same-transaction record of domain events emitted from an authoritative state change. |
| Inbox / Replay Receipt | Idempotency evidence used to prevent duplicate external event effects while retaining replay/audit history. |
| Anti-Corruption Layer | Translation at a context boundary that preserves EA semantics and prevents foreign product/domain models from becoming EA's internal model by convenience. |
| Noema Projection | A receipt-bound architecture projection of Noema deployable/runtime/service/API/worker capability identity, infrastructure technology/provider/version, lifecycle, ownership, architecture-risk context, remediation or transformation. It never transfers Agent Runtime, Workflow/Task, Tool/Capability, State/Checkpoint, Policy/Approval, Observability or Recovery truth to EA. |
| Quarantine Sandbox Runtime | The independent reusable hostile-workload isolation product that owns sandbox lifecycle/resource enforcement/cleanup/attestation and artifact-analysis evidence. It is not the owner of caller authorization, maliciousness verdicts, incidents or EA architecture decisions. |
| Application-Service Lease | A caller-scoped request/lease boundary through which contextual-orchestrator may run an application service in the Quarantine Sandbox Runtime. The caller's policy, application selection and secrets remain outside the runtime. |
| Artifact-Analysis Evidence | Evidence produced by Quarantine Sandbox Runtime analysis of a hostile or unknown artifact. Wardnet may consume it for SOC policy/verdict decisions; the evidence itself is not an authoritative EA malware verdict or risk score. |
| Architecture Risk Context | Architecture-relevant risk context about a runtime/backend/technology that may inform an EA decision with explicit source, truth status, time and provenance. It is distinct from a product-specific security verdict or scanner risk score. |

## Data/AI evidence language

Names such as data product, catalog asset, lineage, output port, glossary term and trust/certification belong primarily to the Data/AI Context. EA may store receipt-bound references/projections needed for an architecture assessment, improvement dependency or impact path, but must retain source ownership and truth origin. `data_management_*` projections in the current stack therefore describe EA decision evidence and remediation state, not a replacement catalog system of record.

## Agent runtime projection language

Noema remains authoritative for Agent tasks/results/reasoning, tool payloads, workflow execution state, approval decisions, checkpoint/prompt content, model output and user business data. EA may receive only the architecture-relevant projection named above, through released Context Graph admission with a Projection Receipt. A Noema event or model-backed result cannot become authoritative EA truth by ingestion; direct database access and source copying remain outside the integration model.

## Isolation and security evidence language

Quarantine runtime technology/provider/version/lifecycle, ownership, remediation/transformation and attestation provenance may be projected as EA context only through a released compatible Context Graph contract. Every admitted Context Assertion projection retains a Projection Receipt, so a later EA decision can identify the source authority, exact CloudEvent, schema/profile/admission version and provenance used at admission. Sandbox internals stay in `quarantine-sandbox-runtime`; caller authorization/application selection stays in `contextual-orchestrator`; maliciousness verdicts, incidents and quarantine/block policy stay in Wardnet. Direct database access or source copying across these contexts is not part of the model.

## Naming and path discipline

New code should be named for the bounded context or domain responsibility it serves. Do not add catch-all `utils`, `helpers`, `common`, `shared`, `core`, `models`, `services`, `misc` or `legacy` buckets. Historical `src/ea_core_foundation`, `service.py`, `runtime.py` and broad validation modules are tracked DDD debt; they are not examples for new placement. Correct them only after consumer/import/API/event/database/test compatibility is mapped and a coherent bounded slice can move without destructive history rewriting.
