"""Quarantine Sandbox Runtime ownership fitness checks for EA projections."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .. import validation_data_management_recheck_status as base

ContractValidationError = base.ContractValidationError

_CONNECTOR_NAME = "quarantine_sandbox_runtime"
_APPLICATION_SERVICE_RUNTIME_CONTROLS = (
    "isolation_policy_enforcement",
    "resource_bounds",
    "readiness",
    "cleanup",
    "attestation",
)


def validate_quarantine_application_service_runtime_controls(
    connector: Mapping[str, Any],
) -> None:
    """Require the reusable runtime controls that back an application-service lease."""

    if connector.get("connector_name") != _CONNECTOR_NAME:
        raise ContractValidationError(
            "quarantine application-service runtime controls require the canonical "
            "quarantine_sandbox_runtime connector"
        )
    if connector.get("application_service_runtime_controls") != list(
        _APPLICATION_SERVICE_RUNTIME_CONTROLS
    ):
        raise ContractValidationError(
            "quarantine runtime application-service runtime controls must preserve "
            "isolation policy enforcement, resource bounds, readiness, cleanup, "
            "and attestation"
        )
