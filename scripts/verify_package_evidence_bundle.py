#!/usr/bin/env python3
"""Verify downloaded package evidence before protected-main attestation."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import sys
from pathlib import Path

from strict_json_identity import load_strict_json, read_stable_regular_file

_SBOM_NAME = "enterprise-architecture-core.spdx.json"
_CHECKSUM_NAME = "SHA256SUMS"
_SPDX_CONTEXT = "https://spdx.org/rdf/3.0.1/spdx-context.jsonld"
_CHECKSUM_PATTERN = re.compile(r"^([0-9a-f]{64})  ([^\s]+)$")


def _stable_sha256(path: Path, *, label: str) -> str:
    """Hash one stable regular file without following a replacement symlink."""
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise OSError(f"platform lacks O_NOFOLLOW for {label}")
    descriptor = os.open(path, os.O_RDONLY | nofollow)
    try:
        opened_stat = os.fstat(descriptor)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise ValueError(f"{label} is not a regular file: {path}")
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        path_stat = os.stat(path, follow_symlinks=False)
        if not stat.S_ISREG(path_stat.st_mode):
            raise ValueError(f"{label} path stopped being regular: {path}")
        if (opened_stat.st_dev, opened_stat.st_ino) != (
            path_stat.st_dev,
            path_stat.st_ino,
        ):
            raise ValueError(f"{label} path changed while being read: {path}")
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def _require_bundle_shape(evidence_dir: Path) -> tuple[Path, Path, Path, Path]:
    """Return the four exact evidence paths after rejecting mixed bundle shapes."""
    if evidence_dir.is_symlink():
        raise ValueError(f"evidence directory must not be a symlink: {evidence_dir}")
    if not evidence_dir.is_dir():
        raise ValueError(f"evidence directory does not exist: {evidence_dir}")

    entries = list(evidence_dir.iterdir())
    symlinks = [entry.name for entry in entries if entry.is_symlink()]
    if symlinks:
        names = ", ".join(sorted(symlinks))
        raise ValueError(f"package evidence contains symlink entries: {names}")

    wheels = [entry for entry in entries if entry.name.endswith(".whl")]
    sdists = [entry for entry in entries if entry.name.endswith(".tar.gz")]
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("expected exactly one wheel and one source distribution")

    wheel = wheels[0]
    sdist = sdists[0]
    sbom = evidence_dir / _SBOM_NAME
    checksums = evidence_dir / _CHECKSUM_NAME
    expected_names = {wheel.name, sdist.name, sbom.name, checksums.name}
    actual_names = {entry.name for entry in entries}
    if actual_names != expected_names:
        unexpected = sorted(actual_names - expected_names)
        missing = sorted(expected_names - actual_names)
        detail = f"unexpected={unexpected}, missing={missing}"
        raise ValueError(f"package evidence bundle has non-canonical contents: {detail}")

    for path, label in (
        (wheel, "wheel evidence"),
        (sdist, "source-distribution evidence"),
        (sbom, "SPDX evidence"),
        (checksums, "checksum evidence"),
    ):
        path_stat = os.stat(path, follow_symlinks=False)
        if not stat.S_ISREG(path_stat.st_mode):
            raise ValueError(f"{label} is not a regular file: {path}")
    return wheel, sdist, sbom, checksums


def _parse_checksums(data: bytes, expected_names: set[str]) -> dict[str, str]:
    """Parse an exact checksum manifest with one entry for every evidence file."""
    text = data.decode("utf-8")
    lines = text.splitlines()
    if len(lines) != len(expected_names):
        raise ValueError("checksum manifest must contain exactly three entries")

    parsed: dict[str, str] = {}
    for line in lines:
        match = _CHECKSUM_PATTERN.fullmatch(line)
        if match is None:
            raise ValueError("checksum manifest contains a malformed entry")
        digest, name = match.groups()
        if Path(name).name != name or "/" in name or "\\" in name:
            raise ValueError("checksum manifest contains a non-basename path")
        if name in parsed:
            raise ValueError(f"checksum manifest repeats evidence name: {name}")
        parsed[name] = digest
    if set(parsed) != expected_names:
        raise ValueError("checksum manifest names do not match package evidence")
    return parsed


def _require_spdx_301(sbom_path: Path) -> None:
    """Require the retained canonical SPDX 3.0.1 package-evidence shape."""
    data = read_stable_regular_file(sbom_path, label="SPDX evidence")
    sbom = load_strict_json(data)
    if not isinstance(sbom, dict):
        raise ValueError("SPDX evidence must be a JSON object")
    if sbom.get("@context") != _SPDX_CONTEXT:
        raise ValueError("SPDX evidence does not use the canonical SPDX 3.0.1 context")
    graph = sbom.get("@graph")
    if not isinstance(graph, list) or not graph:
        raise ValueError("SPDX evidence must contain a non-empty @graph")
    has_creation_info = any(
        isinstance(item, dict)
        and item.get("type") == "CreationInfo"
        and item.get("specVersion") == "3.0.1"
        for item in graph
    )
    if not has_creation_info:
        raise ValueError("SPDX evidence is missing SPDX 3.0.1 CreationInfo")
    has_package = any(
        isinstance(item, dict) and item.get("type") == "software_Package"
        for item in graph
    )
    if not has_package:
        raise ValueError("SPDX evidence is missing a software_Package element")


def verify_package_evidence_bundle(evidence_dir: Path) -> None:
    """Fail closed unless downloaded package evidence is internally coherent."""
    wheel, sdist, sbom, checksum_path = _require_bundle_shape(evidence_dir)
    expected_names = {wheel.name, sdist.name, sbom.name}
    checksum_bytes = read_stable_regular_file(
        checksum_path,
        label="checksum evidence",
    )
    expected_digests = _parse_checksums(checksum_bytes, expected_names)
    for artifact, label in (
        (wheel, "wheel evidence"),
        (sdist, "source-distribution evidence"),
        (sbom, "SPDX evidence"),
    ):
        actual_digest = _stable_sha256(artifact, label=label)
        if actual_digest != expected_digests[artifact.name]:
            raise ValueError(f"checksum mismatch for package evidence: {artifact.name}")
    _require_spdx_301(sbom)


def main(argv: list[str]) -> int:
    """Run downloaded package-evidence admission as a command-line gate."""
    if len(argv) != 2:
        print("usage: verify_package_evidence_bundle.py EVIDENCE_DIR", file=sys.stderr)
        return 2
    try:
        verify_package_evidence_bundle(Path(argv[1]))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"package evidence admission failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
