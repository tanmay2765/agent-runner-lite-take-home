"""Tests for TASK 3 — the agent loop (run_agent)."""

from __future__ import annotations

from dataclasses import replace

from app.agent import run_agent
from app.config import SETTINGS
from app.models import ExpectedEffect
from app.seed import SCENARIOS
from tests.helpers import make_run


def test_default_completes_with_no_tools():
    run, deps = make_run(SCENARIOS["default"])

    run_agent(run, deps)

    assert run.status == "completed"
    assert run.effects == []
    assert deps.workspace.messages == []
    assert any(step.type == "final" for step in run.steps)


def test_send_followup_records_one_write_and_passes_verification():
    run, deps = make_run(
        SCENARIOS["send_followup"],
        expected=[ExpectedEffect(tool="send_message", match={"contact_id": "c_1"})],
    )

    run_agent(run, deps)

    assert run.status == "completed"
    assert len(run.effects) == 1
    assert run.effects[0].tool == "send_message"
    assert run.effects[0].simulated is False
    assert run.verdict is not None
    assert run.verdict.passed is True
    assert len(deps.workspace.messages) == 1


def test_unknown_tool_recovers_and_completes():
    run, deps = make_run(SCENARIOS["unknown_tool"])

    run_agent(run, deps)

    assert run.status == "completed"
    failed_results = [step for step in run.steps if step.type == "tool_result" and not step.ok]
    assert failed_results
    assert "archive_contact" in str(failed_results[0].result)


def test_shadow_records_simulated_effect_and_does_not_send():
    run, deps = make_run(
        SCENARIOS["send_followup"],
        autonomy="shadow",
        expected=[ExpectedEffect(tool="send_message", match={"contact_id": "c_1"})],
    )

    run_agent(run, deps)

    assert run.status == "completed"
    assert run.effects[0].simulated is True
    assert run.verdict is not None
    assert run.verdict.passed is True
    assert deps.workspace.messages == []


def test_never_finishes_fails_instead_of_hanging():
    run, deps = make_run(
        SCENARIOS["never_finishes"],
        settings=replace(SETTINGS, max_steps=5),
    )

    run_agent(run, deps)

    assert run.status == "failed"
    assert run.error is not None
    assert any(step.type == "error" for step in run.steps)


def test_bad_credentials_fails_without_raising():
    run, deps = make_run(SCENARIOS["bad_credentials"])

    result = run_agent(run, deps)

    assert result.status == "failed"
    assert result.error is not None
    assert "invalid api key" in result.error
    assert deps.model.calls == 1
