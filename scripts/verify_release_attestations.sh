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

if [[ -e "$VERIFICATION_DIR" || -L "$VERIFICATION_DIR" ]]; then
  echo "refusing to reuse existing attestation verification directory" >&2
  exit 1
fi
if ! (umask 077 && mkdir "$VERIFICATION_DIR"); then
  echo "unable to create a private attestation verification directory" >&2
  exit 1
fi
common_policy=(
  --repo "$REPOSITORY"
  --source-digest "$SOURCE_SHA"
  --source-ref "$EXPECTED_SOURCE_REF"
  --signer-digest "$SOURCE_SHA"
  --signer-workflow "$SIGNER_WORKFLOW"
  --cert-oidc-issuer https://token.actions.githubusercontent.com
  --deny-self-hosted-runners
)

capture_and_validate_attestation_json() {
  local output_path="$1"
  local expected_digest="$2"
  shift 2
  python - "$output_path" "$expected_digest" "$@" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

MAX_JSON_BYTES = 16 * 1024 * 1024


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


def load_strict_json_bytes(data: bytes) -> Any:
    """Parse one bounded evidence document with strict JSON semantics."""
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


def read_process_stdout(command: list[str]) -> bytes:
    """Capture only bounded bytes emitted directly by the attestation producer."""
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    assert process.stdout is not None
    chunks: list[bytes] = []
    total = 0
    try:
        while True:
            chunk = process.stdout.read(min(1024 * 1024, MAX_JSON_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_JSON_BYTES:
                process.kill()
                process.wait()
                raise ValueError("attestation producer JSON exceeds 16 MiB")
        returncode = process.wait()
    except BaseException:
        if process.poll() is None:
            process.kill()
        process.wait()
        raise
    finally:
        process.stdout.close()
    if returncode != 0:
        raise RuntimeError(f"attestation producer exited with status {returncode}")
    return b"".join(chunks)


def retain_verified_bytes(path: Path, data: bytes) -> None:
    """Retain already-verified producer bytes in one exclusive private file."""
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise OSError("platform lacks O_NOFOLLOW for attestation evidence")
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow,
        0o600,
    )
    try:
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                raise OSError("attestation evidence write made no progress")
            offset += written
        os.fsync(descriptor)
        opened_stat = os.fstat(descriptor)
        path_stat = os.stat(path, follow_symlinks=False)
        if not stat.S_ISREG(opened_stat.st_mode) or not stat.S_ISREG(path_stat.st_mode):
            raise OSError(f"attestation evidence is not a regular file: {path}")
        if opened_stat.st_size != len(data) or stat.S_IMODE(opened_stat.st_mode) != 0o600:
            raise OSError(f"attestation evidence was not retained completely and privately: {path}")
        if (opened_stat.st_dev, opened_stat.st_ino) != (path_stat.st_dev, path_stat.st_ino):
            raise OSError(f"attestation evidence path changed while being retained: {path}")
    except BaseException:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
    finally:
        os.close(descriptor)


output_path = Path(sys.argv[1])
expected_digest = sys.argv[2]
command = sys.argv[3:]
try:
    raw = read_process_stdout(command)
    verification = load_strict_json_bytes(raw)
    if expected_digest != "-":
        if not isinstance(verification, list) or not verification:
            raise ValueError("gh attestation verification must return a non-empty JSON array")
        for candidate in verification:
            if not isinstance(candidate, dict):
                continue
            result = candidate.get("verificationResult")
            if not isinstance(result, dict):
                continue
            statement = result.get("statement")
            if not isinstance(statement, dict) or "predicate" not in statement:
                continue
            if hashlib.sha256(normalized_json(statement["predicate"])).hexdigest() == expected_digest:
                break
        else:
            raise ValueError("attested SPDX predicate does not match downloaded package SBOM")
    retain_verified_bytes(output_path, raw)
except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
    print(f"unable to capture or verify attestation evidence strictly: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc
except RuntimeError as exc:
    print(f"unable to capture attestation producer output: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc
PY
}

for artifact in "${artifacts[@]}"; do
  artifact_name="$(basename "$artifact")"
  provenance_verification="$VERIFICATION_DIR/$artifact_name.provenance.json"
  capture_and_validate_attestation_json "$provenance_verification" - gh attestation verify "$artifact" \
    "${common_policy[@]}" \
    --format json
  sbom_verification="$VERIFICATION_DIR/$artifact_name.sbom.json"
  capture_and_validate_attestation_json "$sbom_verification" "$expected_sbom_digest" gh attestation verify "$artifact" \
    "${common_policy[@]}" \
    --predicate-type "$SPDX_PREDICATE" \
    --format json
done
