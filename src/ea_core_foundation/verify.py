"""Compatibility facade for Strategy & Transformation verification commands."""

from .strategy_transformation.verify import (
    TargetStateVerificationRequest,
    build_target_state_verification_writer,
    build_verification_authorization_config,
    parse_target_state_verification_request,
)

__all__ = [
    "TargetStateVerificationRequest",
    "build_target_state_verification_writer",
    "build_verification_authorization_config",
    "parse_target_state_verification_request",
]
