# Product Capability Crosswalk

| External capability pattern | Buyer problem | CWL decision | Owner | Initial evidence | Limitation |
|---|---|---|---|---|---|
| Business-capability mapping | Applications are discussed without business context | Normalize capability and application identities and relations | EA Core | SQL model and API contract | UI not implemented |
| Application portfolio | Fit, criticality, cost, and risk are inconsistent | Version assessment frameworks and scale values | EA Core | SQL assessment model | Scoring workflow not implemented |
| Technology lifecycle risk | End-of-support impact is hard to trace | Store component/version/lifecycle facts and publish changes | EA Core | lifecycle and outbox tables | Vendor lifecycle connector absent |
| Current/target architecture | Future designs overwrite current truth | Baseline plus ordered scenario deltas | EA Core | scenario tables and ADR 0008 | Projector not implemented |
| Data/AI context | EA inventory lacks dataset and model evidence | Link by canonical references; keep data context in SDP | Semantic Data Portal | architecture boundary docs | Cross-domain projector absent |
