"""Lock protected-main attestation workflow runtime and repository identity."""

from pathlib import Path

_WORKFLOW = Path(".github/workflows/supply-chain.yml")
_SETUP_PYTHON = "actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405"


def _attestation_job() -> str:
    """Return only the protected-main attestation job source."""
    workflow = _WORKFLOW.read_text(encoding="utf-8")
    return workflow.split("  attest-protected-main:\n", 1)[1]


def test_attestation_job_pins_python_before_verifier() -> None:
    """Do not depend on the mutable ubuntu-latest ambient Python installation."""
    job = _attestation_job()
    setup_offset = job.find(_SETUP_PYTHON)
    verifier_offset = job.find("run: bash scripts/verify_release_attestations.sh")

    assert setup_offset >= 0
    assert verifier_offset >= 0
    assert setup_offset < verifier_offset
    assert 'python-version: "3.14"' in job[setup_offset:verifier_offset]


def test_attestation_identity_uses_live_github_repository_context() -> None:
    """Avoid hard-coded owner casing in OIDC signer/repository verification policy."""
    job = _attestation_job()

    assert "REPOSITORY: ${{ github.repository }}" in job
    assert (
        "SIGNER_WORKFLOW: ${{ github.repository }}/.github/workflows/supply-chain.yml"
        in job
    )
    assert "REPOSITORY: ContextualWisdomLab/" not in job
    assert "SIGNER_WORKFLOW: ContextualWisdomLab/" not in job
