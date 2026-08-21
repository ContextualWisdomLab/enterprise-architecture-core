"""Protect CI workflows from committing reusable database credentials."""

import re
from pathlib import Path

WORKFLOW_ROOT = Path(__file__).parents[1] / ".github" / "workflows"
FORBIDDEN_PATTERNS = (
    re.compile(r"ea_(?:test|owner_test|runtime_test)_password"),
    re.compile(r"wrong-" + r"test-" + r"password"),
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

    for pattern in FORBIDDEN_PATTERNS:
        assert pattern.search(workflow_text) is None
    assert workflow_text.count('openssl rand -hex 32') >= 2
    assert 'printf \'EA_OWNER_PASSWORD=%s\\n\'' in workflow_text
    assert 'printf \'EA_RUNTIME_PASSWORD=%s\\n\'' in workflow_text


def test_migration_service_uses_run_bound_authentication() -> None:
    """Keep CI authentication unique to one disposable workflow execution."""

    workflow_text = (WORKFLOW_ROOT / "ci.yml").read_text(encoding="utf-8")

    run_bound_password = "${{ github.run_id }}-${{ github.run_attempt }}"
    assert f"POSTGRES_PASSWORD: {run_bound_password}" in workflow_text
    assert workflow_text.count(f"PGPASSWORD: {run_bound_password}") >= 6
