"""Guard Context Assertion migrations against invented admission evidence."""

import re
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("migration_name", "identity_columns"),
    [
        (
            "0053_context_assertion_projection_contract_identity.sql",
            ("context_profile_id", "context_profile_version", "admission_version"),
        ),
        (
            "0054_context_assertion_projection_schema_version.sql",
            ("context_schema_version",),
        ),
        (
            "0055_context_assertion_projection_message_profile.sql",
            ("message_profile_id", "message_profile_version"),
        ),
    ],
)
def test_context_assertion_identity_migrations_never_backfill_admission_evidence(
    repository_root: Path,
    migration_name: str,
    identity_columns: tuple[str, ...],
) -> None:
    """Provisional rows cannot be promoted to exact released-contract evidence."""

    migration_path = repository_root / "database/migrations" / migration_name
    migration_sql = migration_path.read_text(encoding="utf-8")
    normalized_sql = " ".join(migration_sql.split())

    empty_table_guard = (
        "IF EXISTS ( SELECT 1 FROM "
        "architecture_core.context_assertion_projection_receipt ) THEN"
    )
    assert empty_table_guard in normalized_sql, (
        f"{migration_name} must fail closed when provisional Context Assertion "
        "receipts already exist; their exact schema/profile/admission identity "
        "must come from re-admission, not migration inference"
    )

    for identity_column in identity_columns:
        synthetic_default = re.compile(
            rf"ADD COLUMN {re.escape(identity_column)}\\b[^;]*\\bDEFAULT\\b",
            flags=re.IGNORECASE,
        )
        assert synthetic_default.search(normalized_sql) is None, (
            f"{migration_name} must not synthesize {identity_column} for "
            "pre-existing receipts with a DDL default"
        )
