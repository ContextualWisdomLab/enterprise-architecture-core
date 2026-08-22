"""HTTP framing regressions for governed target-state write commands."""

from __future__ import annotations

from email.message import Message
from io import BytesIO

import pytest

from ea_core_foundation.service import FoundationServiceHandler, PlannerRequestError


def _command_handler(
    body: bytes,
    *,
    transfer_encoding: str | None = None,
    duplicate_content_length: bool = False,
) -> FoundationServiceHandler:
    """Build only the request-body state shared by approval and scheduling."""

    handler = FoundationServiceHandler.__new__(FoundationServiceHandler)
    headers = Message()
    headers["Content-Type"] = "application/json"
    headers["Content-Length"] = str(len(body))
    if duplicate_content_length:
        headers["Content-Length"] = str(len(body))
    if transfer_encoding is not None:
        headers["Transfer-Encoding"] = transfer_encoding
    handler.headers = headers
    handler.rfile = BytesIO(body)
    return handler


def test_commands_reject_transfer_encoding_before_reading_json() -> None:
    """A write command cannot mix unsupported transfer framing with length framing."""

    handler = _command_handler(b"{}", transfer_encoding="chunked")

    with pytest.raises(PlannerRequestError, match="Transfer-Encoding"):
        handler._read_approval_json()


def test_commands_reject_duplicate_content_length_before_reading_json() -> None:
    """Multiple Content-Length fields are ambiguous even when values are identical."""

    handler = _command_handler(b"{}", duplicate_content_length=True)

    with pytest.raises(PlannerRequestError, match="Content-Length"):
        handler._read_approval_json()
