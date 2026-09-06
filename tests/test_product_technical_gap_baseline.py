"""Fitness checks for the code-current product and technical gap baseline."""

from pathlib import Path


def test_gap_baseline_preserves_ea_context_fabric_boundaries() -> None:
    """Keep current release, authority, and quarantine dependencies explicit."""
    baseline = Path("docs/product-technical-gap-baseline.md").read_text(encoding="utf-8")
    lower_baseline = baseline.lower()

    for token in (
        "ea decision plane",
        "protected `main`",
        "context assertion",
        "immutable release",
        "quarantine sandbox runtime",
        "malware verdict",
        "predecessor evidence",
        "cross-service sql",
    ):
        assert token in lower_baseline, token
