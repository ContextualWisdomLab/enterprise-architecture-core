"""Connector direction vocabulary regressions."""

import json

import pytest

from ea_core_foundation import ContractValidationError, validate_connector_catalog


def test_connector_catalog_rejects_unknown_direction_code(repository_root) -> None:
    """A direction typo cannot bypass Context Graph contract binding."""

    document = json.loads(
        (repository_root / "contracts/connectors/ecosystem.json").read_text(
            encoding="utf-8"
        )
    )
    connector = next(
        item
        for item in document["connectors"]
        if item["connector_name"] == "semantic_data_portal"
    )
    connector["direction_code"] = "inbound_projeciton"

    with pytest.raises(
        ContractValidationError,
        match="direction_code must be one of",
    ):
        validate_connector_catalog(document)
