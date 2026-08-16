"""Documentation baseline tests."""

from pathlib import Path

_REQUIRED_DOCUMENTS = (
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "CHANGELOG.md",
    "SECURITY.md",
    "docs/PRD.md",
    "docs/TRD.md",
    "docs/ARCHITECTURE.md",
    "docs/DATA_MODEL.md",
    "docs/API_CONTRACT.md",
    "docs/TEST_STRATEGY.md",
    "docs/OPERABILITY.md",
    "docs/SECURITY.md",
    "docs/doctoring/REFERENCES.md",
    "docs/doctoring/STANDARD_TRACEABILITY.md",
    "docs/doctoring/PRODUCT_CAPABILITY_CROSSWALK.md",
)


def test_required_documents_exist_without_placeholders(repository_root: Path) -> None:
    """The first review contains a complete non-placeholder document baseline."""

    for relative_path in _REQUIRED_DOCUMENTS:
        document_path = repository_root / relative_path
        assert document_path.is_file(), relative_path
        document_text = document_path.read_text(encoding="utf-8")
        assert "TBD" not in document_text
        assert "TODO" not in document_text
        assert len(document_text.strip()) >= 100


def test_all_adrs_are_accepted_and_dated(repository_root: Path) -> None:
    """Every initial architecture decision is explicit and reviewable."""

    adr_paths = sorted((repository_root / "docs/adr").glob("*.md"))
    assert len(adr_paths) == 10
    for adr_path in adr_paths:
        adr_text = adr_path.read_text(encoding="utf-8")
        assert "- **Status:** Accepted" in adr_text
        assert "- **Date:** 2026-08-16" in adr_text
        assert "## Decision" in adr_text
        assert "## Consequence" in adr_text
