"""Compatibility facade for the historical authorization module.

Keyverse/OIDC verification belongs to the Generic identity/authorization
adapter. The historical import resolves to the same module object so existing
callers and monkeypatches keep one authorization implementation during the
compatibility window.
"""

import sys as _sys

from .identity_authorization import authorization as _authorization
from .identity_authorization.authorization import *  # noqa: F403

_sys.modules[__name__] = _authorization
