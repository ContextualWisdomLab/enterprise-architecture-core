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
    """The readiness query proves schema presence and keeps application tables denied."""

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
