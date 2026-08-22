"""Executable conformance for libpq connection-parameter environment mapping."""

from ea_core_foundation.service import _postgres_environment


def test_sslsni_uses_postgresql_documented_environment_variable() -> None:
    """The libpq ``sslsni`` URI parameter must map to PostgreSQL's ``PGSSLSNI``."""

    environment = _postgres_environment(
        "postgresql://ea_runtime@db.example/ea_core?sslsni=0",
        {},
    )

    assert environment is not None
    assert environment["PGSSLSNI"] == "0"
    assert "PGSSNI" not in environment
