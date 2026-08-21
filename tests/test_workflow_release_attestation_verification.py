"""Keep protected-main artifact verification on one executable, tested boundary."""

from __future__ import annotations

from pathlib import Path

_SUPPLY_CHAIN_PATH = Path(".github/workflows/supply-chain.yml")


def test_protected_main_invokes_executable_attestation_verifier() -> None:
    """Require the protected-main workflow to execute the regression-tested verifier."""
    workflow_text = _SUPPLY_CHAIN_PATH.read_text(encoding="utf-8")

    assert (
        "name: Verify protected-main provenance and SBOM attestations"
        in workflow_text
    )
    assert 'SOURCE_SHA: ${{ github.sha }}' in workflow_text
    assert 'SOURCE_REF: ${{ github.ref }}' in workflow_text
    assert 'EXPECTED_SOURCE_REF: refs/heads/main' in workflow_text
    assert (
        'SIGNER_WORKFLOW: ContextualWisdomLab/enterprise-architecture-core/'
        '.github/workflows/supply-chain.yml'
    ) in workflow_text
    assert (
        'REPOSITORY: ContextualWisdomLab/enterprise-architecture-core'
        in workflow_text
    )
    assert 'SPDX_PREDICATE: https://spdx.dev/Document/v3' in workflow_text
    assert 'EVIDENCE_DIR: evidence' in workflow_text
    assert 'VERIFICATION_DIR: attestation-verification' in workflow_text
    assert "run: bash scripts/verify_release_attestations.sh" in workflow_text


def test_protected_main_retains_exact_sha_verification_records() -> None:
    """Keep machine-readable verifier results for the exact protected-main SHA."""
    workflow_text = _SUPPLY_CHAIN_PATH.read_text(encoding="utf-8")

    assert "name: attestation-verification-${{ github.sha }}" in workflow_text
    assert "path: attestation-verification/*.json" in workflow_text
    assert "retention-days: 90" in workflow_text
