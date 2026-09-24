"""Tests for TASK 2 — behaviour-equivalence check (verify)."""

from __future__ import annotations

from app.models import Effect, ExpectedEffect, Run, Task
from app.verifier import verify


def _task(*expected_effects: ExpectedEffect) -> Task:
    return Task(
        id="t_1",
        goal="test task",
        expected_effects=list(expected_effects),
    )


def _run(*effects: Effect, autonomy: str = "autonomous") -> Run:
    return Run(
        id="r_1",
        task_id="t_1",
        autonomy=autonomy,
        effects=list(effects),
    )


def test_verify_passes_when_all_expected_effects_matched():
    task = _task(ExpectedEffect(tool="send_message", match={"contact_id": "c_1"}))
    run = _run(
        Effect(
            tool="send_message",
            args={"contact_id": "c_1", "body": "hello", "idempotency_key": "r_1:1"},
        )
    )

    verdict = verify(task, run)

    assert verdict.passed is True
    assert verdict.missing == []
    assert verdict.unexpected == []
    assert len(verdict.matched) == 1


def test_verify_fails_when_expected_effect_is_missing():
    task = _task(ExpectedEffect(tool="send_message", match={"contact_id": "c_1"}))
    run = _run()

    verdict = verify(task, run)

    assert verdict.passed is False
    assert len(verdict.missing) == 1
    assert verdict.missing[0].tool == "send_message"
    assert verdict.missing[0].match == {"contact_id": "c_1"}
    assert verdict.unexpected == []


def test_verify_fails_when_unexpected_effect_present():
    task = _task()
    run = _run(
        Effect(
            tool="send_message",
            args={"contact_id": "c_1", "body": "surprise"},
        )
    )

    verdict = verify(task, run)

    assert verdict.passed is False
    assert verdict.missing == []
    assert len(verdict.unexpected) == 1
    assert verdict.unexpected[0].tool == "send_message"


def test_verify_treats_simulated_effects_like_real_ones():
    task = _task(ExpectedEffect(tool="send_message", match={"contact_id": "c_1"}))
    run = _run(
        Effect(
            tool="send_message",
            args={"contact_id": "c_1", "body": "shadow"},
            simulated=True,
        ),
        autonomy="shadow",
    )

    verdict = verify(task, run)

    assert verdict.passed is True
    assert verdict.missing == []
    assert verdict.unexpected == []
    assert verdict.mode == "shadow"


def test_verify_each_effect_can_only_match_one_expectation():
    task = _task(
        ExpectedEffect(tool="send_message", match={"contact_id": "c_1"}),
        ExpectedEffect(tool="send_message", match={"contact_id": "c_1"}),
    )
    run = _run(
        Effect(
            tool="send_message",
            args={"contact_id": "c_1", "body": "only one"},
        )
    )

    verdict = verify(task, run)

    assert verdict.passed is False
    assert len(verdict.matched) == 1
    assert len(verdict.missing) == 1
    assert verdict.unexpected == []
