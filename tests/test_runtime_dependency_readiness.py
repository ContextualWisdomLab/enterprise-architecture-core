"""Fail-closed runtime dependency readiness tests."""

from importlib.metadata import PackageNotFoundError
from subprocess import CompletedProcess
from typing import Any

from ea_core_foundation.service import (
    SUPPORTED_CONTEXT_CONTRACT_VERSION,
    build_database_readiness_probe,
    probe_context_contract,
)


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
        "postgresql://ea_runtime:secret-value@127.0.0.1:54328/ea_core",
        runner=runner,
        base_environment={},
    )

    assert probe() is True
    assert "secret-value" not in " ".join(captured["args"])
    assert captured["env"]["PGPASSWORD"] == "secret-value"
    assert captured["env"]["PGUSER"] == "ea_runtime"
    assert captured["env"]["PGDATABASE"] == "ea_core"
    command = captured["args"][captured["args"].index("--command") + 1]
    assert "architecture_core" in command
    assert "has_table_privilege" in command


def test_database_probe_fails_closed_for_missing_config_and_probe_errors() -> None:
    """Missing DSN, missing psql, timeout, or a false query result is not ready."""

    assert build_database_readiness_probe(None)() is False

    def missing_psql(args: list[str], **kwargs: Any) -> CompletedProcess[str]:
        del args, kwargs
        raise FileNotFoundError("psql")

    assert (
        build_database_readiness_probe(
            "postgresql://ea_runtime:secret@127.0.0.1:54328/ea_core",
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
            "postgresql://ea_runtime:secret@127.0.0.1:54328/ea_core",
            runner=false_result,
            base_environment={},
        )()
        is False
    )
