"""Compatibility facade for Strategy & Transformation completion commands."""

from .strategy_transformation.complete import (
    TargetStateCompleteRequest,
    build_complete_authorization_config,
    build_target_state_complete_writer,
    parse_target_state_complete_request,
)

__all__ = [
    "TargetStateCompleteRequest",
    "build_complete_authorization_config",
    "build_target_state_complete_writer",
    "parse_target_state_complete_request",
]
