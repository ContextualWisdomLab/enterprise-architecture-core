"""Reject same-inode mutation while retaining verified attestation bytes."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def test_verified_output_rejects_same_inode_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retained evidence must equal the exact bytes accepted from ``gh``."""
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    import verify_attestation_output as verifier

    target = tmp_path / "verified.json"
    expected = b'{"verified":true}'
    original_open = os.open
    original_write = os.write
    mutated = False

    def mutate_after_write(descriptor: int, data: bytes | memoryview) -> int:
        nonlocal mutated
        written = original_write(descriptor, data)
        if not mutated:
            mutated = True
            attacker_descriptor = original_open(target, os.O_WRONLY)
            try:
                original_write(attacker_descriptor, b"x" * written)
                os.fsync(attacker_descriptor)
            finally:
                os.close(attacker_descriptor)
        return written

    monkeypatch.setattr(os, "write", mutate_after_write)

    with pytest.raises(ValueError, match="changed while being retained"):
        verifier._write_exclusive_regular_file(target, expected)
    assert mutated
    assert not target.exists()
