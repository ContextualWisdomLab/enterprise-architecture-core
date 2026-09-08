"""Ubiquitous-language regressions for Context Assertion projection receipts."""

from pathlib import Path


_REQUIRED_RECEIPT_LANGUAGE = (
    "event semantic profile id/version",
    "structured-message admission profile id/version",
)


def test_projection_receipt_language_distinguishes_both_profiles(repository_root: Path) -> None:
    """Written domain language must preserve both independent profile identities."""

    ubiquitous_language = (
        repository_root / "docs/UBIQUITOUS_LANGUAGE.md"
    ).read_text(encoding="utf-8")
    context_map = (repository_root / "docs/CONTEXT_MAP.md").read_text(encoding="utf-8")

    for phrase in _REQUIRED_RECEIPT_LANGUAGE:
        assert phrase in ubiquitous_language
        assert phrase in context_map
