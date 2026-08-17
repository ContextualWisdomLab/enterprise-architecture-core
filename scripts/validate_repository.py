"""Validate the Enterprise Architecture Core repository foundation."""

from pathlib import Path

from ea_core_foundation import validate_repository


def main() -> int:
    """Run repository validation and print a stable summary."""

    report = validate_repository(Path(__file__).resolve().parents[1])
    print(
        "validated "
        f"{report.table_count} tables, "
        f"{report.column_count} columns, "
        f"{report.index_count} indexes, "
        f"{report.constraint_count} constraints, "
        f"{report.openapi_operation_count} OpenAPI operations, "
        f"{report.asyncapi_operation_count} AsyncAPI operations, "
        f"{report.connector_count} connectors, and "
        f"{report.adr_count} ADRs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
