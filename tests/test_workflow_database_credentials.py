"""Protect CI workflows from committing or misrouting database credentials."""

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
    assert 'export EA_OWNER_PASSWORD="$owner_password"' in workflow_text
    assert 'export EA_RUNTIME_PASSWORD="$runtime_password"' in workflow_text
    assert 'printf \'EA_OWNER_PASSWORD=%s\\n\'' in workflow_text
    assert 'printf \'EA_RUNTIME_PASSWORD=%s\\n\'' in workflow_text


def test_runtime_readiness_uses_purpose_bound_passfiles() -> None:
    """Authenticate readiness through the DSN-owned passfile, not ambient PG* vars."""

    workflow_text = (WORKFLOW_ROOT / "runtime-readiness.yml").read_text(
        encoding="utf-8"
    )

    assert workflow_text.count('runtime_passfile="$RUNNER_TEMP/ea-runtime.pgpass"') == 2
    assert workflow_text.count('passfile=${runtime_passfile}') == 2
    assert (
        'printf \'127.0.0.1:54328:ea_core:ea_runtime:%s\\n\' '
        '"$EA_RUNTIME_PASSWORD" > "$runtime_passfile"' in workflow_text
    )
    assert (
        'printf \'127.0.0.1:54328:ea_core:ea_runtime:%swrong\\n\' '
        '"$EA_RUNTIME_PASSWORD" > "$runtime_passfile"' in workflow_text
    )
    assert workflow_text.count('chmod 600 "$runtime_passfile"') == 2
    assert "export PGPASSWORD=" not in workflow_text


def test_migration_service_uses_disposable_trust_only() -> None:
    """Keep passwordless authentication limited to the ephemeral CI service."""

    workflow_text = (WORKFLOW_ROOT / "ci.yml").read_text(encoding="utf-8")

    assert "POSTGRES_HOST_AUTH_METHOD: trust" in workflow_text
    assert "POSTGRES_PASSWORD:" not in workflow_text
