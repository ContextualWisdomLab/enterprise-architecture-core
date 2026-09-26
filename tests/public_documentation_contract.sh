#!/usr/bin/env bash
set -u

failures=0

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  failures=$((failures + 1))
}

require_file() {
  [ -f "$1" ] || fail "missing file: $1"
}

require_text() {
  local file="$1"
  local text="$2"
  if [ ! -f "$file" ] || ! grep -Fq -- "$text" "$file"; then
    fail "$file must contain: $text"
  fi
}

forbid_text() {
  local file="$1"
  local text="$2"
  if [ -f "$file" ] && grep -Fq -- "$text" "$file"; then
    fail "$file must not contain: $text"
  fi
}

require_file README.md
require_file docs/index.md
require_file docs/product-technical-gap-baseline.md

require_text README.md "## Current status"
require_text README.md "No executable package or release is currently published."
require_text README.md "## Integration"
require_text README.md "## Support"
require_text README.md "## License"
require_text README.md "No repository-level \`LICENSE\` is present."
require_text README.md "[Product and technical gap baseline](docs/product-technical-gap-baseline.md)"

require_text docs/index.md "[README](../README.md)"
require_text docs/index.md "[Product and technical gap baseline](product-technical-gap-baseline.md)"
require_text docs/index.md "No verified GitHub Pages publication exists."
forbid_text docs/index.md "/blob/develop/"
forbid_text docs/index.md "/tree/develop/"

for heading in PRD TRD ADR UML ERD "Context Map" Gap Action Status License Release Pages; do
  require_text docs/product-technical-gap-baseline.md "$heading"
done

if [ "$failures" -ne 0 ]; then
  printf 'public documentation contract: %d failure(s)\n' "$failures" >&2
  exit 1
fi

printf 'public documentation contract: OK\n'
