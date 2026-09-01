"""Canonical repository-owner regressions for ecosystem projections."""

import json

import pytest

from ea_core_foundation import ContractValidationError, validate_connector_catalog


def test_connector_catalog_rejects_unqualified_repository_owner(
    repository_root,
) -> None:
    """Repository drill-down identities must include the owning CWL organization."""

    document = json.loads(
        (repository_root / "contracts/connectors/ecosystem.json").read_text(
            encoding="utf-8"
        )
    )
    connector = next(
        connector
        for connector in document["connectors"]
        if connector["connector_name"] == "semantic_data_portal"
    )
    connector["owner_repository"] = "semantic-data-portal"
    with pytest.raises(
        ContractValidationError,
        match="canonical ContextualWisdomLab repository",
    ):
        validate_connector_catalog(document)
