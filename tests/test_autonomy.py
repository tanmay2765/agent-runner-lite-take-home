"""Tests for TASK 1 — the governance policy (evaluate_gate)."""

from __future__ import annotations

import pytest

from app.autonomy import evaluate_gate
from app.models import AutonomyLevel


@pytest.mark.parametrize(
    "level",
    ["shadow", "supervised", "autonomous"],
)
def test_read_tools_always_allowed(level: AutonomyLevel):
    decision = evaluate_gate(level=level, tool_kind="read", writes_so_far=0)

    assert decision.allow is True
    assert decision.simulate is False
    assert decision.requires_approval is False
    assert decision.reason


def test_shadow_write_is_simulated():
    decision = evaluate_gate(level="shadow", tool_kind="write", writes_so_far=0)

    assert decision.allow is True
    assert decision.simulate is True
    assert decision.requires_approval is False


def test_supervised_write_requires_approval():
    decision = evaluate_gate(level="supervised", tool_kind="write", writes_so_far=0)

    assert decision.allow is False
    assert decision.simulate is False
    assert decision.requires_approval is True


@pytest.mark.parametrize(
    "writes_so_far,max_auto_writes,should_allow",
    [
        (0, 2, True),
        (1, 2, True),
        (2, 2, False),
        (3, 2, False),
    ],
)
def test_autonomous_write_budget(writes_so_far, max_auto_writes, should_allow):
    decision = evaluate_gate(
        level="autonomous",
        tool_kind="write",
        writes_so_far=writes_so_far,
        max_auto_writes=max_auto_writes,
    )

    if should_allow:
        assert decision.allow is True
        assert decision.simulate is False
        assert decision.requires_approval is False
    else:
        assert decision.allow is False
        assert decision.simulate is False
        assert decision.requires_approval is True
