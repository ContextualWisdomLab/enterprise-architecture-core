"""Regression tests for passwordless libpq readiness configuration."""

from subprocess import CompletedProcess
from typing import Any

from ea_core_foundation.service import build_database_readiness_probe


def test_database_probe_allows_passfile_auth_without_inline_password() -> None:
    """A libpq passfile is valid authentication and must not require PGPASSWORD."""

    captured: dict[str, Any] = {}

    def runner(args: list[str], **kwargs: Any) -> CompletedProcess[str]:
        captured.update(kwargs)
        return CompletedProcess(args, 0, stdout="t\n", stderr="")

    probe = build_database_readiness_probe(
        "postgresql://ea_runtime@db.example/ea_core"
        "?passfile=%2Frun%2Fsecrets%2Fpgpass&require_auth=scram-sha-256",
        runner=runner,
        base_environment={},
    )

    assert probe() is True
    assert "PGPASSWORD" not in captured["env"]
    assert captured["env"]["PGPASSFILE"] == "/run/secrets/pgpass"
    assert captured["env"]["PGREQUIREAUTH"] == "scram-sha-256"


def test_database_probe_allows_default_socket_without_host_or_password() -> None:
    """libpq may use its default Unix socket and a passfile when URI fields are omitted."""

    captured: dict[str, Any] = {}

    def runner(args: list[str], **kwargs: Any) -> CompletedProcess[str]:
        captured.update(kwargs)
        return CompletedProcess(args, 0, stdout="t\n", stderr="")

    probe = build_database_readiness_probe(
        "postgresql:///ea_core?user=ea_runtime&passfile=%2Frun%2Fsecrets%2Fpgpass",
        runner=runner,
        base_environment={},
    )

    assert probe() is True
    assert "PGHOST" not in captured["env"]
    assert "PGPASSWORD" not in captured["env"]
    assert captured["env"]["PGUSER"] == "ea_runtime"
    assert captured["env"]["PGDATABASE"] == "ea_core"
    assert captured["env"]["PGPASSFILE"] == "/run/secrets/pgpass"
