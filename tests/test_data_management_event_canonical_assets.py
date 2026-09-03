"""Canonical Context Graph asset-reference regressions for data-management events."""

from copy import deepcopy

import pytest

from ea_core_foundation import ContractValidationError, validate_asyncapi_document

_CANONICAL_ASSET_SCHEMA = (
    "https://schemas.contextualwisdomlab.org/context/"
    "canonical-asset-uri.v1.schema.json"
)
_CANONICAL_ASSET_FIELDS = (
    ("DataManagementImprovementInitiativeCreated", "assessment_result_uri"),
    ("DataManagementEvidenceAccepted", "evidence_uri"),
)


def _event_data_properties(document, message_name: str) -> dict:
    """Return the event-specific data-property registry for one message."""

    return document["components"]["messages"][message_name]["payload"]["schema"][
        "allOf"
    ][1]["properties"]["data"]["properties"]


@pytest.mark.parametrize(("message_name", "field_name"), _CANONICAL_ASSET_FIELDS)
def test_foreign_data_context_asset_fields_use_canonical_contract(
    asyncapi_document,
    message_name: str,
    field_name: str,
) -> None:
    """Foreign Data Context identities must use the shared canonical asset schema."""

    properties = _event_data_properties(asyncapi_document, message_name)
    assert properties[field_name] == {"$ref": _CANONICAL_ASSET_SCHEMA}


@pytest.mark.parametrize(("message_name", "field_name"), _CANONICAL_ASSET_FIELDS)
def test_validator_rejects_loose_foreign_asset_strings(
    asyncapi_document,
    message_name: str,
    field_name: str,
) -> None:
    """A bounded arbitrary string must not replace canonical foreign identity."""

    changed = deepcopy(asyncapi_document)
    properties = _event_data_properties(changed, message_name)
    properties[field_name] = {"type": "string", "minLength": 1, "maxLength": 2048}

    with pytest.raises(
        ContractValidationError,
        match="must reference the Context Graph canonical asset URI schema",
    ):
        validate_asyncapi_document(changed)
