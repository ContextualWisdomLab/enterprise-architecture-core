#!/usr/bin/env bash
# Preserve the baseline SPDX gate; full release verification is owned by PR #34.
set -euo pipefail
: "${1:?usage: validate-sbom.sh distribution-directory}"
python - "$1" <<'PY'
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
sbom = json.loads((root / "enterprise-architecture-core.spdx.json").read_text())
assert sbom.get("@context") == "https://spdx.org/rdf/3.0.1/spdx-context.jsonld"
graph = sbom.get("@graph")
assert isinstance(graph, list) and graph
assert any(
    item.get("type") == "CreationInfo" and item.get("specVersion") == "3.0.1"
    for item in graph if isinstance(item, dict)
)
assert any(
    item.get("type") == "software_Package"
    for item in graph if isinstance(item, dict)
)
assert len(list(root.glob("*.whl"))) == 1
assert len(list(root.glob("*.tar.gz"))) == 1
PY
(
  cd "$1"
  sha256sum -- *.whl *.tar.gz enterprise-architecture-core.spdx.json > SHA256SUMS
  sha256sum -c SHA256SUMS
)
