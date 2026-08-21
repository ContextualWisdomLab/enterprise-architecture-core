# ADR 0006: Security-control evidence boundary

**Status:** Accepted

## Context

The product baseline identifies CSAP/SOC 2 readiness as a buyer gap. The
repository has implementation-candidate security, runtime, database, and
supply-chain evidence, but the protected `develop` branch remains the
initialization baseline and no CSAP certificate, SOC 2 report, production
attestation, or independent audit result is observed. A standards citation or
green local test cannot close that gap.

NIST CSF 2.0 provides a flexible cybersecurity-risk outcome taxonomy. The AICPA
2017 Trust Services Criteria with revised 2022 points of focus provides criteria
for a later attestation engagement. The Korean CSAP rule defines a formal cloud
security certification and assessment boundary. These sources inform the
crosswalk; they do not make this repository certified.

## Decision

Maintain one preparation-level crosswalk at
[`docs/doctoring/CSAP-SOC2-CONTROL-EVIDENCE.md`](../doctoring/CSAP-SOC2-CONTROL-EVIDENCE.md).

The crosswalk MUST:

1. separate `observed`, `candidate`, `planned`, and `exception` evidence;
2. identify the service boundary, role owner, evidence locator, cadence, and
   next acceptance for each control area;
3. preserve foreign-system authority for identity, customer data, and external
   lifecycle sources;
4. require current protected/released/live evidence before making a buyer-facing
   control claim; and
5. state explicitly that certification and attestation require the applicable
   external assessor, scope, period, population, and report or certificate.

The first implementation remains documentation-only. Existing tests, database
constraints, workflow gates, release attestation checks, and runtime probes are
the evidence mechanisms to reuse. No new security platform, UI, connector, or
dependency is introduced by this decision.

## Consequences

- Buyers receive a traceable preparation packet without a false certification
  claim.
- Missing operational, production, and independent-assessment evidence remains
  visible as work rather than being hidden behind a maturity label.
- A protected merge or release must refresh the exact evidence packet because
  candidate evidence does not transfer automatically across heads.
- A future assessment can add its formal scope and sampling records without
  changing the product architecture boundary.

## References

Association of International Certified Professional Accountants. (2023).
*2017 Trust Services Criteria (with revised points of focus — 2022)*.
https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022

Ministry of Science and ICT. (2023). *클라우드컴퓨팅서비스 보안인증에 관한
고시* [Notice on cloud computing service security certification; 시행
2023-01-31, 과학기술정보통신부고시 제2023-4호]. 국가법령정보센터.
https://law.go.kr/LSW/admRulInfoP.do?admRulSeq=2100000218804

National Institute of Standards and Technology. (2024). *The NIST
Cybersecurity Framework (CSF) 2.0* (NIST CSWP 29).
https://doi.org/10.6028/NIST.CSWP.29
