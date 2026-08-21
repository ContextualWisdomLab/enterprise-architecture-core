#!/usr/bin/env bash
set -euo pipefail

: "${SOURCE_SHA:?SOURCE_SHA is required}"
: "${SOURCE_REF:?SOURCE_REF is required}"
: "${EXPECTED_SOURCE_REF:?EXPECTED_SOURCE_REF is required}"
: "${REPOSITORY:?REPOSITORY is required}"
: "${SIGNER_WORKFLOW:?SIGNER_WORKFLOW is required}"
: "${SPDX_PREDICATE:?SPDX_PREDICATE is required}"

EVIDENCE_DIR="${EVIDENCE_DIR:-evidence}"
VERIFICATION_DIR="${VERIFICATION_DIR:-attestation-verification}"

if [[ "$SOURCE_REF" != "$EXPECTED_SOURCE_REF" ]]; then
  echo "refusing attestation verification outside protected main" >&2
  exit 1
fi

if [[ ! "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo "source SHA must be an exact lowercase 40-hex commit" >&2
  exit 1
fi

shopt -s nullglob
wheels=("$EVIDENCE_DIR"/*.whl)
sdists=("$EVIDENCE_DIR"/*.tar.gz)
if (( ${#wheels[@]} != 1 || ${#sdists[@]} != 1 )); then
  echo "expected exactly one wheel and one source distribution" >&2
  exit 1
fi
artifacts=("${wheels[@]}" "${sdists[@]}")

sbom_path="$EVIDENCE_DIR/enterprise-architecture-core.spdx.json"
if [[ ! -f "$sbom_path" || -L "$sbom_path" ]]; then
  echo "expected one regular downloaded SPDX evidence document" >&2
  exit 1
fi

snapshot_downloaded_sbom_digest() {
  python - "$sbom_path" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any


class DuplicateJsonMember(ValueError):
    """Reject ambiguous JSON objects with duplicate member names."""


def reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build a JSON object only when every member name is unique."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonMember(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def reject_nonstandard_constant(value: str) -> None:
    """Reject NaN and Infinity extensions that are not valid JSON."""
    raise ValueError(f"non-standard JSON numeric constant: {value}")


def read_stable_regular_file(path: Path) -> bytes:
    """Read one bounded regular file without following a replacement symlink."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened_stat = os.fstat(descriptor)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise ValueError(f"SPDX evidence is not a regular file: {path}")
        chunks: list[bytes] = []
        remaining = 16 * 1024 * 1024 + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > 16 * 1024 * 1024:
            raise ValueError(f"JSON evidence exceeds 16 MiB: {path}")
    finally:
        os.close(descriptor)

    path_stat = os.stat(path, follow_symlinks=False)
    if not stat.S_ISREG(path_stat.st_mode):
        raise ValueError(f"SPDX evidence path stopped being a regular file: {path}")
    if (opened_stat.st_dev, opened_stat.st_ino) != (path_stat.st_dev, path_stat.st_ino):
        raise ValueError(f"SPDX evidence path changed while being read: {path}")
    return data


def load_strict_json_bytes(data: bytes) -> Any:
    """Parse bounded JSON bytes with strict member and number semantics."""
    return json.loads(
        data.decode("utf-8"),
        object_pairs_hook=reject_duplicate_members,
        parse_constant=reject_nonstandard_constant,
    )


def normalized_json(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON for parsed-value identity."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


path = Path(sys.argv[1])
try:
    expected = load_strict_json_bytes(read_stable_regular_file(path))
except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
    print(f"unable to snapshot downloaded SPDX evidence strictly: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc

if not isinstance(expected, dict):
    print("downloaded SPDX evidence must be a JSON object", file=sys.stderr)
    raise SystemExit(1)

print(hashlib.sha256(normalized_json(expected)).hexdigest())
PY
}

expected_sbom_digest="$(snapshot_downloaded_sbom_digest)"

mkdir -p "$VERIFICATION_DIR"
common_policy=(
  --repo "$REPOSITORY"
  --source-digest "$SOURCE_SHA"
  --source-ref "$EXPECTED_SOURCE_REF"
  --signer-digest "$SOURCE_SHA"
  --signer-workflow "$SIGNER_WORKFLOW"
  --cert-oidc-issuer https://token.actions.githubusercontent.com
  --deny-self-hosted-runners
)

verify_attested_sbom_matches_downloaded_evidence() {
  local verification_path="$1"
  python - "$expected_sbom_digest" "$verification_path" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


class DuplicateJsonMember(ValueError):
    """Reject ambiguous JSON objects with duplicate member names."""


def reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build a JSON object only when every member name is unique."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonMember(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def reject_nonstandard_constant(value: str) -> None:
    """Reject NaN and Infinity extensions that are not valid JSON."""
    raise ValueError(f"non-standard JSON numeric constant: {value}")


def load_strict_json(path: Path) -> Any:
    """Parse one bounded evidence document with strict JSON member semantics."""
    with path.open("rb") as stream:
        data = stream.read(16 * 1024 * 1024 + 1)
    if len(data) > 16 * 1024 * 1024:
        raise ValueError(f"JSON evidence exceeds 16 MiB: {path}")
    return json.loads(
        data.decode("utf-8"),
        object_pairs_hook=reject_duplicate_members,
        parse_constant=reject_nonstandard_constant,
    )


def normalized_json(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON for parsed-value identity."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


expected_digest = sys.argv[1]
verification_path = Path(sys.argv[2])
try:
    verification = load_strict_json(verification_path)
except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
    print(f"unable to parse attestation/SBOM evidence strictly: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc

if not isinstance(verification, list) or not verification:
    print("gh attestation verification must return a non-empty JSON array", file=sys.stderr)
    raise SystemExit(1)

for candidate in verification:
    if not isinstance(candidate, dict):
        continue
    result = candidate.get("verificationResult")
    if not isinstance(result, dict):
        continue
    statement = result.get("statement")
    if not isinstance(statement, dict) or "predicate" not in statement:
        continue
    candidate_digest = hashlib.sha256(normalized_json(statement["predicate"])).hexdigest()
    if candidate_digest == expected_digest:
        raise SystemExit(0)

print(
    "attested SPDX predicate does not match downloaded package SBOM",
    file=sys.stderr,
)
raise SystemExit(1)
PY
}

for artifact in "${artifacts[@]}"; do
  artifact_name="$(basename "$artifact")"
  gh attestation verify "$artifact" \
    "${common_policy[@]}" \
    --format json \
    > "$VERIFICATION_DIR/$artifact_name.provenance.json"
  sbom_verification="$VERIFICATION_DIR/$artifact_name.sbom.json"
  gh attestation verify "$artifact" \
    "${common_policy[@]}" \
    --predicate-type "$SPDX_PREDICATE" \
    --format json \
    > "$sbom_verification"
  verify_attested_sbom_matches_downloaded_evidence "$sbom_verification"
done
