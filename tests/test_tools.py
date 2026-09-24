"""Tests for TASK 4b — idempotent send_message."""

from __future__ import annotations

import pytest

from app.seed import CONTACTS
from app.tools import ToolError, Workspace


def test_send_message_is_idempotent_for_duplicate_keys():
    ws = Workspace(CONTACTS)

    first = ws.send_message(
        contact_id="c_1",
        body="hello",
        idempotency_key="r_1:1",
    )
    second = ws.send_message(
        contact_id="c_1",
        body="hello",
        idempotency_key="r_1:1",
    )

    assert len(ws.messages) == 1
    assert first["deduped"] is False
    assert second["deduped"] is True
    assert second["message_id"] == first["message_id"]
    assert second["contact_id"] == "c_1"


def test_send_message_requires_idempotency_key():
    ws = Workspace(CONTACTS)

    with pytest.raises(ToolError, match="idempotency_key"):
        ws.send_message(contact_id="c_1", body="hello")
