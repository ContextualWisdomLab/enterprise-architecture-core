"""Protect CI workflows from committing reusable database credentials."""

from pathlib import Path

WORKFLOW_ROOT = Path(__file__).parents[1] / ".github" / "workflows"
FORBIDDEN_LITERALS = (
    "ea_test_password",
    "ea_owner_test_password",
    "ea_runtime_test_password",
    "wrong-test-password",
)


def test_database_workflows_generate_credentials_at_runtime() -> None:
    """Require ephemeral credential generation in every database workflow."""

    workflow_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            WORKFLOW_ROOT / "ci.yml",
            WORKFLOW_ROOT / "runtime-readiness.yml",
        )
    )

    for literal in FORBIDDEN_LITERALS:
        assert literal not in workflow_text
    assert workflow_text.count('openssl rand -hex 32') >= 2
    assert 'printf \'EA_OWNER_PASSWORD=%s\\n\'' in workflow_text
    assert 'printf \'EA_RUNTIME_PASSWORD=%s\\n\'' in workflow_text


def test_migration_service_uses_disposable_trust_only() -> None:
    """Keep passwordless authentication limited to the ephemeral CI service."""

    workflow_text = (WORKFLOW_ROOT / "ci.yml").read_text(encoding="utf-8")

    assert "POSTGRES_HOST_AUTH_METHOD: trust" in workflow_text
    assert "POSTGRES_PASSWORD:" not in workflow_text
