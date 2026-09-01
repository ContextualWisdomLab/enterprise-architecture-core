"""Compatibility facade for the historical generic service module.

New decision-plane HTTP behavior belongs in :mod:`decision_plane_http`. This
module remains temporarily import-compatible while existing internal and
external consumers migrate to the responsibility-named path.
"""

from .decision_plane_http import *  # noqa: F403
from .decision_plane_http import (  # noqa: F401
    _parse_timestamp,
    _parse_uuid7,
    _postgres_environment,
)
