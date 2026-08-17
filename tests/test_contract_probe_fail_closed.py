"""Fail-closed regressions for Context Graph dependency discovery."""

from ea_core_foundation.service import probe_context_contract


def test_context_contract_probe_fails_closed_on_metadata_reader_exception() -> None:
    """Broken package metadata must not crash the process-only health surface."""

    def broken_version_reader(_: str) -> str:
        raise RuntimeError("metadata backend unavailable")

    assert probe_context_contract(version_reader=broken_version_reader) is False
