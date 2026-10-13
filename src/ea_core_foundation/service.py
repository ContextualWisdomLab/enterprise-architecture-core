"""Compatibility facade for the historical generic service module.

New decision-plane HTTP behavior belongs in :mod:`decision_plane_http`. The
legacy import resolves to that same module object so monkeypatches and private
compatibility imports keep their historical semantics during migration.
"""

import sys as _sys

from . import decision_plane_http as _decision_plane_http
from .decision_plane_http import *  # noqa: F403

_sys.modules[__name__] = _decision_plane_http
