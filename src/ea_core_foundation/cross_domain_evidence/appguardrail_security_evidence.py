"""AppGuardrail security-evidence anti-corruption boundary."""

from collections.abc import Mapping
from typing import Any

from .data_management_recheck_status import ContractValidationError

_CONNECTOR_NAME = "appguardrail_security_evidence"
_OWNER_REPOSITORY = "ContextualWisdomLab/appguardrail"
_ALLOWED_TRUTH_STATUSES = frozenset({"observed", "inferred"})


def validate_appguardrail_security_evidence(document: Mapping[str, Any]) -> None:
    """Keep scanner observations and analysis outside authoritative EA truth."""

    connectors = [
        connector
        for connector in document["connectors"]
        if connector.get("connector_name") == _CONNECTOR_NAME
    ]
    if len(connectors) != 1:
        raise ContractValidationError(
            "connector catalog must declare exactly one AppGuardrail "
            "security evidence boundary"
        )

    connector = connectors[0]
    if connector.get("owner_repository") != _OWNER_REPOSITORY:
        raise ContractValidationError(
            "AppGuardrail security evidence owner_repository must remain "
            "ContextualWisdomLab/appguardrail"
        )
    if connector.get("direction_code") != "inbound_evidence":
        raise ContractValidationError(
            "AppGuardrail security evidence direction_code must remain inbound_evidence"
        )
    if connector.get("exchange_kind") != "context_assertion_cloudevent":
        raise ContractValidationError(
            "AppGuardrail security evidence must use the Context Assertion "
            "CloudEvent exchange"
        )
    if connector.get("ea_core_owns") is not False:
        raise ContractValidationError(
            "AppGuardrail security evidence must remain outside EA Core ownership"
        )

    declared_statuses = connector.get("projection_truth_statuses")
    if declared_statuses is not None and (
        not isinstance(declared_statuses, list)
        or not declared_statuses
        or any(status not in _ALLOWED_TRUTH_STATUSES for status in declared_statuses)
    ):
        raise ContractValidationError(
            "AppGuardrail security evidence may project observed or inferred truth only"
        )
