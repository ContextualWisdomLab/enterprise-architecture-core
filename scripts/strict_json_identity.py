#!/usr/bin/env python3
"""Provide strict, lossless parsed-value identity for bounded JSON evidence."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

MAX_JSON_BYTES = 16 * 1024 * 1024


class DuplicateJsonMember(ValueError):
    """Signal that an input JSON object repeats a member name."""


def reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build a JSON object only when every member name is unique."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonMember(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def reject_nonstandard_constant(value: str) -> None:
    """Reject NaN and Infinity extensions because they are not valid JSON."""
    raise ValueError(f"non-standard JSON numeric constant: {value}")


def load_strict_json(data: bytes) -> Any:
    """Parse UTF-8 JSON without duplicate members or lossy binary floats."""
    return json.loads(
        data.decode("utf-8"),
        object_pairs_hook=reject_duplicate_members,
        parse_constant=reject_nonstandard_constant,
        parse_int=Decimal,
        parse_float=Decimal,
    )


def _canonical_decimal(value: Decimal) -> bytes:
    """Encode one finite JSON number by its exact mathematical decimal value."""
    if not value.is_finite():
        raise ValueError("JSON number identity requires a finite decimal")
    if value.is_zero():
        return b"d0;"

    decimal_tuple = value.as_tuple()
    digits = list(decimal_tuple.digits)
    exponent = decimal_tuple.exponent
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exponent += 1
    digit_text = "".join(str(digit) for digit in digits)
    return f"d{decimal_tuple.sign}:{digit_text}:{exponent};".encode("ascii")


def canonical_json_value_bytes(value: Any) -> bytes:
    """Encode a parsed JSON value injectively, preserving exact number meaning."""
    if value is None:
        return b"n;"
    if isinstance(value, bool):
        return b"b1;" if value else b"b0;"
    if isinstance(value, Decimal):
        return _canonical_decimal(value)
    if isinstance(value, str):
        encoded = value.encode("utf-8")
        return b"s" + str(len(encoded)).encode("ascii") + b":" + encoded
    if isinstance(value, list):
        prefix = b"l" + str(len(value)).encode("ascii") + b":"
        return prefix + b"".join(canonical_json_value_bytes(item) for item in value)
    if isinstance(value, dict):
        items = sorted(value.items())
        prefix = b"o" + str(len(items)).encode("ascii") + b":"
        encoded_items = []
        for key, item_value in items:
            if not isinstance(key, str):
                raise ValueError("JSON object member names must be strings")
            encoded_items.append(canonical_json_value_bytes(key))
            encoded_items.append(canonical_json_value_bytes(item_value))
        return prefix + b"".join(encoded_items)
    raise ValueError(f"unsupported parsed JSON value type: {type(value).__name__}")


def semantic_json_sha256(value: Any) -> str:
    """Return SHA-256 over the injective parsed-value encoding of JSON evidence."""
    return hashlib.sha256(canonical_json_value_bytes(value)).hexdigest()


def _content_identity(file_stat: os.stat_result) -> tuple[int, int, int]:
    """Return metadata that changes when an opened regular file is rewritten."""
    return (file_stat.st_size, file_stat.st_mtime_ns, file_stat.st_ctime_ns)


def read_stable_regular_file(path: Path, *, label: str) -> bytes:
    """Read one bounded regular file without following or accepting path mutation."""
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise OSError(f"platform lacks O_NOFOLLOW for {label}")
    descriptor = os.open(path, os.O_RDONLY | nofollow)
    try:
        opened_stat = os.fstat(descriptor)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise ValueError(f"{label} is not a regular file: {path}")
        chunks: list[bytes] = []
        remaining = MAX_JSON_BYTES + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > MAX_JSON_BYTES:
            raise ValueError(f"JSON evidence exceeds 16 MiB: {path}")

        final_opened_stat = os.fstat(descriptor)
        path_stat = os.stat(path, follow_symlinks=False)
        if not stat.S_ISREG(path_stat.st_mode):
            raise ValueError(f"{label} path stopped being a regular file: {path}")
        if (opened_stat.st_dev, opened_stat.st_ino) != (
            final_opened_stat.st_dev,
            final_opened_stat.st_ino,
        ) or (opened_stat.st_dev, opened_stat.st_ino) != (
            path_stat.st_dev,
            path_stat.st_ino,
        ):
            raise ValueError(f"{label} path changed while being read: {path}")
        if _content_identity(final_opened_stat) != _content_identity(opened_stat):
            raise ValueError(f"{label} changed while being read: {path}")
        return data
    finally:
        os.close(descriptor)


def snapshot_json_object_digest(path: Path, *, label: str) -> str:
    """Return strict semantic SHA-256 for one stable top-level JSON object."""
    value = load_strict_json(read_stable_regular_file(path, label=label))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return semantic_json_sha256(value)


def main(argv: list[str]) -> int:
    """Print one strict semantic JSON-object digest for a stable evidence file."""
    if len(argv) != 2:
        print("usage: strict_json_identity.py JSON_PATH", file=sys.stderr)
        return 2
    try:
        digest = snapshot_json_object_digest(
            Path(argv[1]),
            label="downloaded SPDX evidence",
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        message = f"unable to snapshot downloaded SPDX evidence strictly: {exc}"
        print(message, file=sys.stderr)
        return 1
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
