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
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROVENANCE_PREDICATE="https://slsa.dev/provenance/v1"

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

snapshot_artifact_digest() {
  python - "$1" <<'PY'
from __future__ import annotations

import hashlib
import os
import stat
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise OSError("platform lacks O_NOFOLLOW for release artifact")
    descriptor = os.open(path, os.O_RDONLY | nofollow)
    try:
        opened_stat = os.fstat(descriptor)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise ValueError(f"release artifact is not a regular file: {path}")
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        path_stat = os.stat(path, follow_symlinks=False)
        if not stat.S_ISREG(path_stat.st_mode):
            raise ValueError(f"release artifact path stopped being regular: {path}")
        if (opened_stat.st_dev, opened_stat.st_ino) != (
            path_stat.st_dev,
            path_stat.st_ino,
        ):
            raise ValueError(f"release artifact path changed while being read: {path}")
    finally:
        os.close(descriptor)
except (OSError, ValueError) as exc:
    print(f"unable to snapshot release artifact strictly: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc

print(digest.hexdigest())
PY
}

expected_sbom_digest="$(python "$SCRIPT_DIR/strict_json_identity.py" "$sbom_path")"

if [[ -e "$VERIFICATION_DIR" || -L "$VERIFICATION_DIR" ]]; then
  echo "refusing to reuse existing attestation verification directory" >&2
  exit 1
fi
umask 077
mkdir "$VERIFICATION_DIR"
if [[ "$(stat -c '%a' "$VERIFICATION_DIR")" != "700" ]]; then
  echo "attestation verification directory is not private" >&2
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

for artifact in "${artifacts[@]}"; do
  artifact_name="$(basename "$artifact")"
  expected_artifact_digest="$(snapshot_artifact_digest "$artifact")"

  gh attestation verify "$artifact" \
    "${common_policy[@]}" \
    --predicate-type "$PROVENANCE_PREDICATE" \
    --format json \
    | python "$SCRIPT_DIR/verify_attestation_output.py" \
        "$VERIFICATION_DIR/$artifact_name.provenance.json" \
        "$expected_artifact_digest" \
        "$PROVENANCE_PREDICATE"

  gh attestation verify "$artifact" \
    "${common_policy[@]}" \
    --predicate-type "$SPDX_PREDICATE" \
    --format json \
    | python "$SCRIPT_DIR/verify_attestation_output.py" \
        "$VERIFICATION_DIR/$artifact_name.sbom.json" \
        "$expected_artifact_digest" \
        "$SPDX_PREDICATE" \
        "$expected_sbom_digest"

  current_artifact_digest="$(snapshot_artifact_digest "$artifact")"
  if [[ "$current_artifact_digest" != "$expected_artifact_digest" ]]; then
    echo "release artifact changed during attestation verification: $artifact" >&2
    exit 1
  fi
done

current_sbom_digest="$(python "$SCRIPT_DIR/strict_json_identity.py" "$sbom_path")"
if [[ "$current_sbom_digest" != "$expected_sbom_digest" ]]; then
  echo "downloaded SPDX evidence changed during attestation verification" >&2
  exit 1
fi
