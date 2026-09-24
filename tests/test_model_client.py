"""Tests for TASK 4a — model call retry logic."""

from __future__ import annotations

import pytest

from app.config import SETTINGS, Settings
from app.model_client import (
    FatalError,
    MockModelClient,
    ThrottleError,
    complete_with_retry,
)


def test_complete_with_retry_succeeds_after_transient_throttling():
    model = MockModelClient(
        [
            ThrottleError("429"),
            ThrottleError("429"),
            '{"intent": "final", "answer": "hi"}',
        ]
    )
    settings = Settings(model_max_retries=3, model_backoff_base_seconds=0)

    result = complete_with_retry(model, messages=[{"role": "user", "content": "go"}], settings=settings)

    assert result == '{"intent": "final", "answer": "hi"}'
    assert model.calls == 3


def test_complete_with_retry_does_not_retry_fatal_errors():
    model = MockModelClient(
        [
            FatalError("bad key"),
            '{"intent": "final", "answer": "hi"}',
        ]
    )
    settings = Settings(model_max_retries=3, model_backoff_base_seconds=0)

    with pytest.raises(FatalError, match="bad key"):
        complete_with_retry(model, messages=[{"role": "user", "content": "go"}], settings=settings)

    assert model.calls == 1
