"""Keyverse issuer/subject identity-key contract tests."""

from pathlib import Path


def _migration_corpus() -> str:
    """Return all migrations in deterministic order."""
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(Path("database/migrations").glob("*.sql"))
    )


def test_identity_link_uses_openid_issuer_subject_pair() -> None:
    """OIDC subjects remain scoped by their immutable issuer identifier."""
    migrations = _migration_corpus()
    assert "issuer_uri" in migrations
    assert "identity_link_issuer_nonempty" in migrations
    assert "identity_link_issuer_subject_unique" in migrations
    assert "identity_link_issuer_subject_validity_exclude" in migrations
    assert (
        "tenant_record_id WITH =,\n"
        "        issuer_uri WITH =,\n"
        "        keyverse_subject_id WITH ="
    ) in migrations


def test_postgresql_acceptance_distinguishes_equal_subjects_by_issuer() -> None:
    """Hosted acceptance proves issuer-qualified subject behavior."""
    acceptance = Path(
        "database/tests/verify_identity_issuer.sql"
    ).read_text(encoding="utf-8")
    assert "https://keyverse.example/issuer-a" in acceptance
    assert "https://keyverse.example/issuer-b" in acceptance
    assert "same_subject" in acceptance
    assert "set_config" in acceptance
    assert "app.tenant_record_id" in acceptance
    assert "overlapping issuer-subject link was accepted" in acceptance
