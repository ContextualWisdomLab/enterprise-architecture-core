#!/usr/bin/env python3
"""Fail closed unless two clean release builds emit identical package bytes."""

from __future__ import annotations

import hashlib
import os
import stat
import sys
from pathlib import Path

_CHUNK_BYTES = 1024 * 1024


def _release_artifacts(directory: Path) -> dict[str, Path]:
    """Return the exact wheel/sdist publication surface for one build directory."""
    try:
        entries = list(directory.iterdir())
    except OSError as exc:
        raise ValueError(f"unable to enumerate build directory: {directory}") from exc

    artifacts = {
        path.name: path
        for path in entries
        if path.name.endswith(".whl") or path.name.endswith(".tar.gz")
    }
    wheel_names = [name for name in artifacts if name.endswith(".whl")]
    sdist_names = [name for name in artifacts if name.endswith(".tar.gz")]
    if len(wheel_names) != 1 or len(sdist_names) != 1:
        raise ValueError(
            "each build must contain exactly one wheel and one source distribution"
        )
    return artifacts


def _stable_sha256(path: Path) -> str:
    """Hash one unchanged regular file without following a path substitution."""
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise OSError(f"platform lacks O_NOFOLLOW for release artifact: {path}")

    before = os.stat(path, follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode):
        raise ValueError(f"release artifact is not a regular file: {path}")

    descriptor = os.open(path, os.O_RDONLY | nofollow)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError(f"release artifact is not a regular file: {path}")
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise ValueError(f"release artifact changed before hashing: {path}")

        digest = hashlib.sha256()
        while True:
            chunk = os.read(descriptor, _CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)

        after_open = os.fstat(descriptor)
        after_path = os.stat(path, follow_symlinks=False)
        stable_identity = (opened.st_dev, opened.st_ino) == (
            after_open.st_dev,
            after_open.st_ino,
        ) == (after_path.st_dev, after_path.st_ino)
        stable_metadata = (
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_ctime_ns,
        ) == (
            after_open.st_size,
            after_open.st_mtime_ns,
            after_open.st_ctime_ns,
        ) == (
            after_path.st_size,
            after_path.st_mtime_ns,
            after_path.st_ctime_ns,
        )
        if not stat.S_ISREG(after_path.st_mode) or not stable_identity or not stable_metadata:
            raise ValueError(f"release artifact changed while hashing: {path}")
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def verify_reproducible_builds(first: Path, second: Path) -> None:
    """Require exact artifact names and byte digests across two clean builds."""
    first_artifacts = _release_artifacts(first)
    second_artifacts = _release_artifacts(second)
    if set(first_artifacts) != set(second_artifacts):
        raise ValueError("release artifact names differ between clean builds")

    for name in sorted(first_artifacts):
        first_digest = _stable_sha256(first_artifacts[name])
        second_digest = _stable_sha256(second_artifacts[name])
        if first_digest != second_digest:
            raise ValueError(f"release artifact bytes differ between clean builds: {name}")


def main(argv: list[str]) -> int:
    """Verify two release build directories and return machine-stable exit status."""
    if len(argv) != 3:
        print(
            "usage: verify_reproducible_package_builds.py FIRST_BUILD SECOND_BUILD",
            file=sys.stderr,
        )
        return 2
    try:
        verify_reproducible_builds(Path(argv[1]), Path(argv[2]))
    except (OSError, ValueError) as exc:
        print(f"release package reproducibility verification failed: {exc}", file=sys.stderr)
        return 1
    print("release package builds are byte-reproducible")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
