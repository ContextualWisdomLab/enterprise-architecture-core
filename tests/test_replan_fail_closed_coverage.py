"""Fail-closed regression coverage for governed target-state replanning."""

from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

import ea_core_foundation.validation as base_validation
import ea_core_foundation.validation_data_management_recheck as recheck_validation
import ea_core_foundation.validation_data_management_recheck_status as status_validation
import ea_core_foundation.validation_replan as replan_validation
from ea_core_foundation.authorization import AuthorizationContext
from ea_core_foundation.replan import (
    build_target_state_replan_writer,
    parse_target_state_replan_request,
)
from ea_core_foundation.service import PlannerExecutionError, PlannerRequestError
from tests.test_target_state_replan_api import (
    _PATH,
    _PREDECESSOR_ID,
    _REPLACEMENT_ID,
    _context,
    _payload,
    _receipt,
)
from tests.test_target_state_replan_runtime import _post, _start_server, _stop_server


@pytest.mark.parametrize(
    ("field_name", "invalid_value", "message"),
    [
        ("transformation_code", "Bad-Code", "transformation_code"),
        ("transformation_code", "a" * 129, "transformation_code"),
        ("transformation_title", "", "transformation_title"),
        ("transformation_title", "t" * 513, "transformation_title"),
        ("transformation_description", "", "transformation_description"),
        ("transformation_description", "d" * 4097, "transformation_description"),
        ("decision_reason_text", "", "decision_reason_text"),
        ("decision_reason_text", "r" * 4097, "decision_reason_text"),
    ],
)
def test_replan_request_rejects_out_of_contract_meaning(
    field_name: str,
    invalid_value: str,
    message: str,
) -> None:
    """Bounded human-authored replacement meaning fails before database execution."""

    with pytest.raises(PlannerRequestError, match=message):
        parse_target_state_replan_request(
            _PATH,
            _payload(**{field_name: invalid_value}),
        )


@pytest.mark.parametrize(
    "path",
    [
        (
            "/v1/not-architecture-transformations/"
            "0196e010-1111-7111-8111-111111111191/replan"
        ),
        f"/v1/architecture-transformations/{_PREDECESSOR_ID}/replan/extra",
        "/v1/architecture-transformations//replan",
        (
            "/v1/architecture-transformations/"
            f"{_PREDECESSOR_ID}/nested/replan"
        ),
    ],
)
def test_replan_request_rejects_malformed_route_shapes(path: str) -> None:
    """Only one canonical predecessor identifier may occupy the command route."""

    with pytest.raises(PlannerRequestError):
        parse_target_state_replan_request(path, _payload())


def test_replan_request_rejects_non_string_wire_members() -> None:
    """The JSON boundary never coerces typed Python values into wire strings."""

    with pytest.raises(PlannerRequestError, match="JSON strings"):
        parse_target_state_replan_request(
            _PATH,
            _payload(decision_request_id=123),
        )


def test_replan_writer_rejects_unsafe_dsn_and_oversized_verified_actor() -> None:
    """Unsafe connection configuration and unbounded identity context fail closed."""

    request = parse_target_state_replan_request(_PATH, _payload())
    unavailable = build_target_state_replan_writer("sqlite:///tmp/ea-core.db")
    with pytest.raises(PlannerExecutionError, match="unavailable"):
        unavailable(_context(), request)

    oversized_context = AuthorizationContext(
        tenant_record_id=_context().tenant_record_id,
        role_code="ea_target_state_replanner",
        subject_id="s" * 2050,
        issuer_uri="https://id.example/realms/cwl",
    )
    writer = build_target_state_replan_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=lambda command, **kwargs: pytest.fail("psql must not run"),
    )
    with pytest.raises(PlannerExecutionError, match="actor reference is too long"):
        writer(oversized_context, request)


@pytest.mark.parametrize(
    "failure",
    [
        OSError("psql missing"),
        subprocess.TimeoutExpired(["psql"], 10),
    ],
)
def test_replan_writer_translates_process_failures(failure: BaseException) -> None:
    """Transport/process failures remain explicit retryable command failures."""

    def runner(command, **kwargs):
        del command, kwargs
        raise failure

    writer = build_target_state_replan_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=runner,
    )
    with pytest.raises(PlannerExecutionError, match="database command failed"):
        writer(_context(), parse_target_state_replan_request(_PATH, _payload()))


@pytest.mark.parametrize(
    "result",
    [
        SimpleNamespace(returncode=1, stdout="", stderr="database error"),
        SimpleNamespace(returncode=0, stdout="not-json", stderr=""),
        SimpleNamespace(returncode=0, stdout="[]", stderr=""),
    ],
)
def test_replan_writer_rejects_failed_or_malformed_database_responses(
    result: SimpleNamespace,
) -> None:
    """A successful command boundary requires one well-formed receipt object."""

    writer = build_target_state_replan_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=lambda command, **kwargs: result,
    )
    with pytest.raises(PlannerExecutionError):
        writer(_context(), parse_target_state_replan_request(_PATH, _payload()))


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("transformation_replan_record_id", "not-a-uuid"),
        ("transformation_history_record_id", "not-a-uuid"),
        ("outbox_event_id", "not-a-uuid"),
        ("replan_recorded_at", "not-a-timestamp"),
        ("predecessor_architecture_transformation_id", _REPLACEMENT_ID),
        ("replacement_architecture_transformation_id", _PREDECESSOR_ID),
        ("decision_request_id", _REPLACEMENT_ID),
        ("replayed", "false"),
        ("next_action", "start_transformation"),
    ],
)
def test_replan_writer_binds_every_receipt_identity_and_action(
    field_name: str,
    invalid_value: object,
) -> None:
    """Database success cannot acknowledge another decision, object, or next action."""

    result = SimpleNamespace(
        returncode=0,
        stdout=json.dumps(_receipt(**{field_name: invalid_value})),
        stderr="",
    )
    writer = build_target_state_replan_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=lambda command, **kwargs: result,
    )
    with pytest.raises(PlannerExecutionError, match="invalid replan receipt"):
        writer(_context(), parse_target_state_replan_request(_PATH, _payload()))


def test_non_replan_post_delegates_to_existing_runtime() -> None:
    """Adding replanning must not capture unrelated inherited POST requests."""

    server, thread, host, port = _start_server()
    try:
        status, body = _post(
            host,
            port,
            authorization=None,
            path="/not-a-replan-command",
            payload={},
        )
    finally:
        _stop_server(server, thread)

    assert status == 405
    assert body["error_code"] == "method_not_allowed"


def _validation_fixture(tmp_path: Path, *, adr_count: int = 10) -> Path:
    """Create a minimal real filesystem boundary for repository orchestration."""

    root = tmp_path / "repository"
    (root / "database/migrations").mkdir(parents=True)
    (root / "contracts/connectors").mkdir(parents=True)
    (root / "docs/adr").mkdir(parents=True)
    (root / "database/migrations/0001_fixture_foundation.sql").write_text(
        "-- fixture migration\n",
        encoding="utf-8",
    )
    (root / "contracts/openapi.json").write_text("{}", encoding="utf-8")
    (root / "contracts/asyncapi.json").write_text("{}", encoding="utf-8")
    (root / "contracts/connectors/ecosystem.json").write_text(
        "{}",
        encoding="utf-8",
    )
    for index in range(adr_count):
        (root / f"docs/adr/{index + 1:04d}-fixture.md").write_text(
            "# Accepted fixture decision\n",
            encoding="utf-8",
        )
    return root


def _stub_base_validators(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate legacy orchestration from lower-level artifact parsing rules."""

    monkeypatch.setattr(
        base_validation,
        "validate_migration_inventory",
        lambda paths: None,
    )
    monkeypatch.setattr(
        base_validation,
        "validate_migration_sql",
        lambda text: (1, 2, 3, 4),
    )
    monkeypatch.setattr(
        base_validation,
        "validate_openapi_document",
        lambda document: 5,
    )
    monkeypatch.setattr(
        base_validation,
        "validate_openapi_runtime_surface",
        lambda document: None,
    )
    monkeypatch.setattr(
        base_validation,
        "validate_asyncapi_document",
        lambda document: 6,
    )
    monkeypatch.setattr(
        base_validation,
        "validate_connector_catalog",
        lambda document: 7,
    )


def test_base_repository_orchestration_remains_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The retained base validator still composes all repository evidence dimensions."""

    root = _validation_fixture(tmp_path)
    _stub_base_validators(monkeypatch)
    report = base_validation.validate_repository(root)
    assert (
        report.table_count,
        report.column_count,
        report.index_count,
        report.constraint_count,
        report.openapi_operation_count,
        report.asyncapi_operation_count,
        report.adr_count,
        report.connector_count,
    ) == (1, 2, 3, 4, 5, 6, 10, 7)


def test_base_repository_orchestration_fails_closed_on_missing_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The retained base boundary rejects missing contracts and ADR evidence."""

    root = _validation_fixture(tmp_path)
    _stub_base_validators(monkeypatch)
    (root / "contracts/openapi.json").unlink()
    with pytest.raises(
        base_validation.ContractValidationError,
        match="missing required file",
    ):
        base_validation.validate_repository(root)

    root = _validation_fixture(tmp_path / "short", adr_count=9)
    _stub_base_validators(monkeypatch)
    with pytest.raises(
        base_validation.ContractValidationError,
        match="at least ten ADRs",
    ):
        base_validation.validate_repository(root)


def test_replan_validation_fails_closed_on_malformed_role_configuration(
    openapi_document: dict[str, object],
) -> None:
    """A non-list Keyverse configuration cannot masquerade as the prior contract."""

    changed = deepcopy(openapi_document)
    changed["x-keyverse-contract"]["requiredConfiguration"] = {}
    without_replan = replan_validation._without_replan_role(changed)
    assert without_replan["x-keyverse-contract"]["requiredConfiguration"] == {}


def test_replan_runtime_contract_requires_both_replan_schemas(
    openapi_document: dict[str, object],
) -> None:
    """The command surface fails when either request or receipt schema is absent."""

    for schema_name in ("TargetStateReplanRequest", "TargetStateReplanReceipt"):
        changed = status_validation._without_status_openapi(
            deepcopy(openapi_document)
        )
        changed = status_validation._without_status_role(changed)
        changed = recheck_validation._without_recheck_openapi(changed)
        changed = recheck_validation._without_recheck_role(changed)
        changed["components"]["schemas"].pop(schema_name)
        with pytest.raises(
            replan_validation.ContractValidationError,
            match="missing OpenAPI schemas",
        ):
            replan_validation.validate_openapi_runtime_surface(changed)
