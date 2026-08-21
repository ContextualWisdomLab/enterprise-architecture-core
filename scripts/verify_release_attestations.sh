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

for artifact in "${artifacts[@]}"; do
  artifact_name="$(basename "$artifact")"
  gh attestation verify "$artifact" \
    "${common_policy[@]}" \
    --format json \
    > "$VERIFICATION_DIR/$artifact_name.provenance.json"
  gh attestation verify "$artifact" \
    "${common_policy[@]}" \
    --predicate-type "$SPDX_PREDICATE" \
    --format json \
    > "$VERIFICATION_DIR/$artifact_name.sbom.json"
done
