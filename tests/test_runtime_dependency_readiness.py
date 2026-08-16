"""Fail-closed runtime dependency readiness tests."""

from importlib.metadata import PackageNotFoundError
from subprocess import CompletedProcess
from typing import Any

from ea_core_foundation.service import (
    SUPPORTED_CONTEXT_CONTRACT_VERSION,
    build_database_readiness_probe,
    build_readiness_report,
    probe_context_contract,
)

_VALID_DSN = "postgresql://ea_runtime:test-pass@127.0.0.1:54328/ea_core"


def test_context_contract_probe_requires_the_exact_installed_distribution() -> None:
    """Absent or mismatched contract packages must never claim readiness."""

    def absent_version(_: str) -> str:
        raise PackageNotFoundError

    assert probe_context_contract(version_reader=absent_version) is False
    assert probe_context_contract(version_reader=lambda _: "9.9.9") is False
    assert (
        probe_context_contract(
            version_reader=lambda _: SUPPORTED_CONTEXT_CONTRACT_VERSION
        )
        is True
    )


def test_database_probe_uses_runtime_role_without_exposing_dsn_password() -> None:
    """Prove schema access while the runtime role keeps application tables denied."""

    captured: dict[str, Any] = {}

    def runner(args: list[str], **kwargs: Any) -> CompletedProcess[str]:
        captured["args"] = args
        captured.update(kwargs)
        return CompletedProcess(args, 0, stdout="t\n", stderr="")

    probe = build_database_readiness_probe(
        _VALID_DSN,
        runner=runner,
        base_environment={},
    )

    assert probe() is True
    assert "test-pass" not in " ".join(captured["args"])
    assert captured["env"]["PGPASSWORD"] == "test-pass"
    assert captured["env"]["PGUSER"] == "ea_runtime"
    assert captured["env"]["PGDATABASE"] == "ea_core"
    assert captured["env"]["PGPORT"] == "54328"
    command = captured["args"][captured["args"].index("--command") + 1]
    assert "architecture_core" in command
    assert "has_table_privilege" in command


def test_database_probe_preserves_supported_libpq_query_semantics() -> None:
    """TLS and target-host policy in the application DSN reach libpq unchanged."""

    captured: dict[str, Any] = {}

    def runner(args: list[str], **kwargs: Any) -> CompletedProcess[str]:
        captured["args"] = args
        captured.update(kwargs)
        return CompletedProcess(args, 0, stdout="t\n", stderr="")

    dsn = (
        f"{_VALID_DSN}?sslmode=verify-full"
        "&sslrootcert=%2Frun%2Fsecrets%2Froot.crt"
        "&target_session_attrs=read-write"
        "&channel_binding=require"
    )
    probe = build_database_readiness_probe(
        dsn,
        runner=runner,
        base_environment={},
    )

    assert probe() is True
    assert captured["env"]["PGSSLMODE"] == "verify-full"
    assert captured["env"]["PGSSLROOTCERT"] == "/run/secrets/root.crt"
    assert captured["env"]["PGTARGETSESSIONATTRS"] == "read-write"
    assert captured["env"]["PGCHANNELBINDING"] == "require"
    assert "test-pass" not in " ".join(captured["args"])


def test_database_probe_preserves_multi_host_order_and_ports() -> None:
    """PostgreSQL URI failover topology must reach libpq without being collapsed."""

    captured: dict[str, Any] = {}

    def runner(args: list[str], **kwargs: Any) -> CompletedProcess[str]:
        captured.update(kwargs)
        return CompletedProcess(args, 0, stdout="t\n", stderr="")

    dsn = (
        "postgresql://ea_runtime:test-pass@"
        "db-a.example:5432,db-b.example:5433/ea_core"
        "?target_session_attrs=read-write"
    )
    probe = build_database_readiness_probe(
        dsn,
        runner=runner,
        base_environment={},
    )

    assert probe() is True
    assert captured["env"]["PGHOST"] == "db-a.example,db-b.example"
    assert captured["env"]["PGPORT"] == "5432,5433"
    assert captured["env"]["PGTARGETSESSIONATTRS"] == "read-write"


def test_database_probe_preserves_empty_multi_host_slot() -> None:
    """An empty failover host item retains libpq's documented default-host slot."""

    captured: dict[str, Any] = {}

    def runner(args: list[str], **kwargs: Any) -> CompletedProcess[str]:
        captured.update(kwargs)
        return CompletedProcess(args, 0, stdout="t\n", stderr="")

    probe = build_database_readiness_probe(
        "postgresql://ea_runtime:test-pass@db-a.example:5432,:5433/ea_core",
        runner=runner,
        base_environment={},
    )

    assert probe() is True
    assert captured["env"]["PGHOST"] == "db-a.example,"
    assert captured["env"]["PGPORT"] == "5432,5433"


def test_database_probe_decodes_unix_socket_host_without_password_leak() -> None:
    """A percent-encoded absolute socket directory remains a socket connection."""

    captured: dict[str, Any] = {}

    def runner(args: list[str], **kwargs: Any) -> CompletedProcess[str]:
        captured["args"] = args
        captured.update(kwargs)
        return CompletedProcess(args, 0, stdout="t\n", stderr="")

    dsn = (
        "postgresql://ea_runtime:test-pass@"
        "%2Fvar%2Frun%2Fpostgresql/ea_core"
    )
    probe = build_database_readiness_probe(
        dsn,
        runner=runner,
        base_environment={},
    )

    assert probe() is True
    assert captured["env"]["PGHOST"] == "/var/run/postgresql"
    assert captured["env"]["PGUSER"] == "ea_runtime"
    assert captured["env"]["PGPASSWORD"] == "test-pass"
    assert "test-pass" not in " ".join(captured["args"])


def test_database_probe_preserves_query_socket_connection_form() -> None:
    """Named URI parameters can select a Unix socket without an authority host."""

    captured: dict[str, Any] = {}

    def runner(args: list[str], **kwargs: Any) -> CompletedProcess[str]:
        captured.update(kwargs)
        return CompletedProcess(args, 0, stdout="t\n", stderr="")

    dsn = (
        "postgresql:///ea_core?host=%2Fvar%2Frun%2Fpostgresql"
        "&user=ea_runtime&password=test-pass"
    )
    probe = build_database_readiness_probe(
        dsn,
        runner=runner,
        base_environment={},
    )

    assert probe() is True
    assert captured["env"]["PGHOST"] == "/var/run/postgresql"
    assert captured["env"]["PGUSER"] == "ea_runtime"
    assert captured["env"]["PGPASSWORD"] == "test-pass"
    assert captured["env"]["PGDATABASE"] == "ea_core"


def test_database_probe_preserves_named_database_and_identity_parameters() -> None:
    """Named URI parameters remain available when the hierarchical fields are absent."""

    captured: dict[str, Any] = {}

    def runner(args: list[str], **kwargs: Any) -> CompletedProcess[str]:
        captured.update(kwargs)
        return CompletedProcess(args, 0, stdout="t\n", stderr="")

    dsn = (
        "postgresql://db.example"
        "?dbname=ea_core&user=ea_runtime&password=test-pass&port=5432"
    )
    probe = build_database_readiness_probe(
        dsn,
        runner=runner,
        base_environment={},
    )

    assert probe() is True
    assert captured["env"]["PGHOST"] == "db.example"
    assert captured["env"]["PGPORT"] == "5432"
    assert captured["env"]["PGUSER"] == "ea_runtime"
    assert captured["env"]["PGPASSWORD"] == "test-pass"
    assert captured["env"]["PGDATABASE"] == "ea_core"


def test_database_probe_rejects_unpreserved_connection_parameters() -> None:
    """Unknown connection semantics fail closed instead of silently changing policy."""

    called = False

    def runner(args: list[str], **kwargs: Any) -> CompletedProcess[str]:
        nonlocal called
        del kwargs
        called = True
        return CompletedProcess(args, 0, stdout="t\n", stderr="")

    probe = build_database_readiness_probe(
        f"{_VALID_DSN}?sslmode=verify-full&future_security_mode=strict",
        runner=runner,
        base_environment={},
    )

    assert probe() is False
    assert called is False


def test_database_probe_rejects_ambiguous_duplicate_connection_parameters() -> None:
    """Duplicate connection controls cannot rely on parser-specific precedence."""

    probe = build_database_readiness_probe(
        f"{_VALID_DSN}?sslmode=require&sslmode=verify-full",
        base_environment={},
    )

    assert probe() is False


def test_database_probe_fails_closed_for_missing_or_malformed_config() -> None:
    """Missing or malformed database configuration cannot enter the serving pool."""

    assert build_database_readiness_probe(None)() is False
    assert build_database_readiness_probe("")() is False
    assert (
        build_database_readiness_probe(
            "http://ea_runtime:test-pass@127.0.0.1:5432/ea_core"
        )()
        is False
    )
    assert (
        build_database_readiness_probe(
            "postgresql://ea_runtime:test-pass@127.0.0.1:notaport/ea_core"
        )()
        is False
    )


def test_database_probe_fails_closed_for_probe_errors_and_false_results() -> None:
    """Missing psql or unsuccessful query evidence remains non-passing."""

    def missing_psql(args: list[str], **kwargs: Any) -> CompletedProcess[str]:
        del args, kwargs
        raise FileNotFoundError("psql")

    assert (
        build_database_readiness_probe(
            _VALID_DSN,
            runner=missing_psql,
            base_environment={},
        )()
        is False
    )

    def false_result(args: list[str], **kwargs: Any) -> CompletedProcess[str]:
        del kwargs
        return CompletedProcess(args, 0, stdout="f\n", stderr="")

    assert (
        build_database_readiness_probe(
            _VALID_DSN,
            runner=false_result,
            base_environment={},
        )()
        is False
    )

    def failed_command(args: list[str], **kwargs: Any) -> CompletedProcess[str]:
        del kwargs
        return CompletedProcess(args, 2, stdout="", stderr="connection failed")

    assert (
        build_database_readiness_probe(
            "postgresql://ea_runtime:test-pass@127.0.0.1/ea_core",
            runner=failed_command,
        )()
        is False
    )


def test_readiness_report_fails_closed_when_a_probe_raises() -> None:
    """Unexpected dependency-probe exceptions must produce 503 rather than 500."""

    def broken_probe() -> bool:
        raise RuntimeError("probe broke")

    report = build_readiness_report(
        contract_ready=True,
        database_probe=broken_probe,
    )
    assert report.http_status() == 503
    assert report.database_ready is False
