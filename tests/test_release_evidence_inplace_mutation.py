"""Reject same-inode rewrites at protected release-evidence read boundaries."""

from __future__ import annotations

import runpy
from pathlib import Path
from typing import Any

import pytest

_STRICT_SCRIPT = Path("scripts/strict_json_identity.py")
_PACKAGE_SCRIPT = Path("scripts/verify_package_evidence_bundle.py")


def _load_script(path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Load one release helper with sibling script imports available."""
    monkeypatch.syspath_prepend(str(path.parent.resolve()))
    return runpy.run_path(str(path), run_name=f"{path.stem}_under_test")


def _install_same_inode_mutation(
    module: dict[str, Any],
    path: Path,
    replacement: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> int:
    """Rewrite one path after its first descriptor read and return its inode."""
    script_os = module["os"]
    real_read = script_os.read
    original_inode = path.stat().st_ino
    mutated = False

    def mutating_read(descriptor: int, maximum_bytes: int) -> bytes:
        nonlocal mutated
        data = real_read(descriptor, maximum_bytes)
        if data and not mutated:
            path.write_bytes(replacement)
            mutated = True
        return data

    monkeypatch.setattr(script_os, "read", mutating_read)
    return original_inode


def test_strict_json_reader_rejects_same_inode_rewrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A retained SPDX snapshot cannot be accepted across an in-place rewrite."""
    path = tmp_path / "evidence.json"
    original = b'{"name":"enterprise-architecture-core"}'
    replacement = b'{"name":"enterprise-architecture-evil"}'
    assert len(original) == len(replacement)
    path.write_bytes(original)
    module = _load_script(_STRICT_SCRIPT, monkeypatch)
    original_inode = _install_same_inode_mutation(
        module,
        path,
        replacement,
        monkeypatch,
    )

    with pytest.raises(ValueError, match="changed while being read"):
        module["read_stable_regular_file"](path, label="SPDX evidence")

    assert path.stat().st_ino == original_inode


def test_package_digest_rejects_same_inode_rewrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Package SHA-256 evidence cannot be accepted across an in-place rewrite."""
    path = tmp_path / "package.whl"
    original = b"release-package-bytes"
    replacement = b"attacker-packag-bytes"
    assert len(original) == len(replacement)
    path.write_bytes(original)
    module = _load_script(_PACKAGE_SCRIPT, monkeypatch)
    original_inode = _install_same_inode_mutation(
        module,
        path,
        replacement,
        monkeypatch,
    )

    with pytest.raises(ValueError, match="changed while being read"):
        module["_stable_sha256"](path, label="wheel evidence")

    assert path.stat().st_ino == original_inode
