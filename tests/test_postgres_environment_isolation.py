"""Security regressions for purpose-bound libpq subprocess configuration."""

from __future__ import annotations

import subprocess
from typing import Any
from uuid import UUID

from ea_core_foundation.authorization import AuthorizationContext
from ea_core_foundation.service import (
    TargetStatePlanRequest,
    build_target_state_plan_reader,
)


def test_planner_reader_drops_ambient_libpq_authority() -> None:
    """The EA database DSN, not inherited PG* variables, defines runtime authority."""

    captured: list[dict[str, str]] = []

    def runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured.append(dict(kwargs["env"]))
        return subprocess.CompletedProcess(command, 0, stdout="[]\n", stderr="")

    reader = build_target_state_plan_reader(
        (
            "postgresql://ea_runtime:dsn-secret@db.example/ea_core"
            "?sslmode=verify-full&application_name=ea-core"
        ),
        runner=runner,
        base_environment={
            "PATH": "/usr/bin",
            "PGHOST": "ambient.example",
            "PGUSER": "postgres",
            "PGPASSWORD": "ambient-secret",
            "PGSERVICE": "privileged-service",
            "PGSERVICEFILE": "/tmp/privileged.pg_service.conf",
            "PGOPTIONS": "-c role=postgres",
            "PGSSLMODE": "disable",
        },
    )
    reader(
        AuthorizationContext(
            tenant_record_id=UUID("018f47b2-905a-7b16-bfd4-7e4f53f10e91"),
            role_code="ea_reader",
            subject_id="buyer-123",
            issuer_uri="https://id.example/realms/cwl",
        ),
        TargetStatePlanRequest.from_values(
            "0196f100-1111-7111-8111-111111111111",
            "2027-02-01T00:00:00Z",
            "2027-02-01T00:00:00Z",
            180,
        ),
    )

    environment = captured[0]
    assert environment["PATH"] == "/usr/bin"
    assert environment["PGHOST"] == "db.example"
    assert environment["PGUSER"] == "ea_runtime"
    assert environment["PGPASSWORD"] == "dsn-secret"
    assert environment["PGDATABASE"] == "ea_core"
    assert environment["PGSSLMODE"] == "verify-full"
    assert environment["PGAPPNAME"] == "ea-core"
    assert "PGSERVICE" not in environment
    assert "PGSERVICEFILE" not in environment
    assert "PGOPTIONS" not in environment
