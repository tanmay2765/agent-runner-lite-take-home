"""Tests for TASK 5 — the start-run HTTP endpoint."""

from __future__ import annotations


def test_start_run_returns_404_when_task_is_missing(client):
    response = client.post("/api/v1/runs", json={"task_id": "t_missing"})

    assert response.status_code == 404
    assert response.json()["detail"] == "task not found"


def test_start_run_completes_send_followup_over_http(client):
    created = client.post(
        "/api/v1/tasks",
        json={
            "goal": "follow up with Acme",
            "scenario": "send_followup",
            "autonomy": "autonomous",
            "expected_effects": [{"tool": "send_message", "match": {"contact_id": "c_1"}}],
        },
    )
    assert created.status_code == 200
    task_id = created.json()["id"]

    started = client.post("/api/v1/runs", json={"task_id": task_id})

    assert started.status_code == 201
    body = started.json()
    assert body["status"] == "completed"
    assert body["task_id"] == task_id
    assert len(body["effects"]) == 1
    assert body["verdict"]["passed"] is True

    fetched = client.get(f"/api/v1/runs/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]
