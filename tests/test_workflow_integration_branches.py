"""Verify repository-owned workflows preserve truthful integration evidence."""

from __future__ import annotations

import re
from pathlib import Path

_WORKFLOW_PATHS = (
    Path(".github/workflows/ci.yml"),
    Path(".github/workflows/runtime-readiness.yml"),
    Path(".github/workflows/supply-chain.yml"),
)
_PUSH_BRANCHES_PATTERN = re.compile(
    r"(?m)^  push:\n    branches: \[([^\]]+)\]$"
)
_CI_PATH = Path(".github/workflows/ci.yml")
_SUPPLY_CHAIN_PATH = Path(".github/workflows/supply-chain.yml")
_VERIFIER_PATH = Path("scripts/verify_release_attestations.sh")


def _push_branches(workflow_path: Path) -> set[str]:
    """Return the explicit push branches declared by one repository workflow."""
    workflow_text = workflow_path.read_text(encoding="utf-8")
    match = _PUSH_BRANCHES_PATTERN.search(workflow_text)
    assert match is not None, f"{workflow_path} must declare explicit push branches"
    return {
        branch.strip()
        for branch in match.group(1).split(",")
        if branch.strip()
    }


def test_repository_workflows_run_on_git_flow_integration_branches() -> None:
    """Require post-integration evidence on both develop and stable main pushes."""
    expected_branches = {"develop", "main"}
    for workflow_path in _WORKFLOW_PATHS:
        assert _push_branches(workflow_path) == expected_branches


def test_dependency_lock_name_matches_the_default_checkout_commit() -> None:
    """Do not label merge-candidate dependency bytes with the PR source-head SHA."""
    workflow_text = _CI_PATH.read_text(encoding="utf-8")

    assert "name: uv-lock-${{ github.sha }}" in workflow_text
    assert "github.event.pull_request.head.sha || github.sha" not in workflow_text


def test_package_evidence_name_matches_the_default_checkout_commit() -> None:
    """Do not label merge-candidate package bytes with the PR source-head SHA."""
    workflow_text = _SUPPLY_CHAIN_PATH.read_text(encoding="utf-8")

    assert "name: package-evidence-${{ github.sha }}" in workflow_text
    assert "github.event.pull_request.head.sha || github.sha" not in workflow_text


def test_generated_package_evidence_uses_the_release_admission_verifier() -> None:
    """Exercise strict package admission on the actual bundle before uploading it."""
    workflow_text = _SUPPLY_CHAIN_PATH.read_text(encoding="utf-8")
    checksum_marker = "- name: Validate SPDX 3.0.1 SBOM and artifact checksums"
    verify_marker = "- name: Verify generated package evidence"
    upload_marker = "- name: Upload checked-out commit package evidence"

    checksum_index = workflow_text.index(checksum_marker)
    verify_index = workflow_text.index(verify_marker)
    upload_index = workflow_text.index(upload_marker)

    assert checksum_index < verify_index < upload_index
    verification_step = workflow_text[verify_index:upload_index]
    assert "python scripts/verify_package_evidence_bundle.py dist" in verification_step


def test_protected_main_revalidates_downloaded_evidence_before_attesting() -> None:
    """Never sign downloaded package bytes before their bundle is re-admitted."""
    workflow_text = _SUPPLY_CHAIN_PATH.read_text(encoding="utf-8")
    download_marker = "- name: Download exact-head package evidence"
    verify_marker = "- name: Verify downloaded package evidence before attestation"
    attest_marker = "- name: Attest SLSA build provenance"

    download_index = workflow_text.index(download_marker)
    verify_index = workflow_text.index(verify_marker)
    attest_index = workflow_text.index(attest_marker)

    assert download_index < verify_index < attest_index
    verification_step = workflow_text[verify_index:attest_index]
    assert "python scripts/verify_package_evidence_bundle.py evidence" in verification_step


def test_spdx3_attestation_uses_canonical_sbom_without_compatibility_copy() -> None:
    """Sign the canonical SPDX 3 JSON-LD as an explicit in-toto predicate."""
    workflow_text = _SUPPLY_CHAIN_PATH.read_text(encoding="utf-8")
    attestation_step = workflow_text.split("- name: Attest SPDX 3 SBOM", maxsplit=1)[1]
    attestation_step = attestation_step.split(
        "- name: Verify protected-main provenance and SBOM attestations",
        maxsplit=1,
    )[0]

    assert "attestation.spdx.json" not in workflow_text
    assert "sbom-path:" not in attestation_step
    assert "predicate-type: https://spdx.dev/Document/v3" in attestation_step
    assert "predicate-path: evidence/enterprise-architecture-core.spdx.json" in (
        attestation_step
    )


def test_protected_main_verifies_and_retains_exact_attestations() -> None:
    """Bind provenance and SBOM attestations to one stable source/workflow identity."""
    workflow_text = _SUPPLY_CHAIN_PATH.read_text(encoding="utf-8")
    verifier_text = _VERIFIER_PATH.read_text(encoding="utf-8")

    assert (
        "name: Verify protected-main provenance and SBOM attestations" in workflow_text
    )
    assert 'SOURCE_SHA: ${{ github.sha }}' in workflow_text
    assert 'SOURCE_REF: ${{ github.ref }}' in workflow_text
    assert 'EXPECTED_SOURCE_REF: refs/heads/main' in workflow_text
    assert 'REPOSITORY: ${{ github.repository }}' in workflow_text
    assert (
        'SIGNER_WORKFLOW: ${{ github.repository }}/'
        '.github/workflows/supply-chain.yml'
    ) in workflow_text
    assert 'SPDX_PREDICATE: https://spdx.dev/Document/v3' in workflow_text
    assert '--source-digest "$SOURCE_SHA"' in verifier_text
    assert '--source-ref "$EXPECTED_SOURCE_REF"' in verifier_text
    assert '--signer-digest "$SOURCE_SHA"' in verifier_text
    assert '--signer-workflow "$SIGNER_WORKFLOW"' in verifier_text
    assert '--deny-self-hosted-runners' in verifier_text
    assert verifier_text.count('gh attestation verify "$artifact"') == 2
    assert "name: attestation-verification-${{ github.sha }}" in workflow_text
    assert "path: attestation-verification/*.json" in workflow_text
    assert "retention-days: 90" in workflow_text
