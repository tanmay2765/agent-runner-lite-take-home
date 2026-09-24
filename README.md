# Agent Runner Lite — Intern Take-Home

Thanks for taking the time on this. You'll build a small **governed agent runner**: a service that
drives an AI agent through a tool-use loop, decides what the agent is allowed to do on its own, and
then checks that it actually did what was asked — and nothing more.

The full brief — the six tasks, what we look for, and the ground rules — is in **`BRIEF.md`**.
**Read that first.** This file is just how to run things, plus a map of the code, and it's where you
write up your work when you're done.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

pytest -q                                             # the example tests pass on a fresh checkout
uvicorn app.main:app --reload                         # http://127.0.0.1:8000/docs
```

Requires **Python 3.11+**. No API keys, no network, no external services — the language model is a
script (`app/seed.py`), so everything is deterministic and offline.

On a fresh checkout the app imports and `pytest` is green, but the six functions you're implementing
raise `NotImplementedError` (and `POST /runs` returns a 501). That's expected. Search the project for
`TODO(candidate)` to find them — there are six, numbered by task.

Nothing is persisted. Restart the server and your tasks and runs are gone. That's fine, don't work
around it.

## Where things are

```
app/
  models.py          the whole data contract — READ THIS FIRST, it's the map
  config.py          settings, all overridable by env var
  seed.py            toy contacts + 11 scripted model conversations
  store.py           two dicts standing in for a database
  model_client.py    TASK 4a — complete_with_retry     (mock model provided)
  tools.py           TASK 4b — send_message            (read tools + update_contact provided)
  autonomy.py        TASK 1  — evaluate_gate
  verifier.py        TASK 2  — verify
  agent.py           TASK 3  — run_agent               (five helpers provided)
  api.py             TASK 5  — start_run               (three other routes provided)
  main.py            the FastAPI app
tests/
  helpers.py         make_run() — builds an isolated run in one line
  conftest.py        store reset + a `client` fixture for HTTP tests
  test_example.py    four example tests showing the shapes you'll want
```

## A suggested first hour

If you're not sure where to start:

1. `pip install -r requirements.txt && pytest -q`. Green? Good.
2. Read **`app/models.py`** top to bottom. It's commented and it's the whole data model — most of
   the "what shape do I return?" questions are answered there.
3. Read **`app/seed.py`** to see what the mock model does. This is the trick that makes the whole
   thing testable, and it's worth understanding before anything else.
4. Open **`app/autonomy.py`** (Task 1). Write the tests for it first — `test_example.py` has a
   `parametrize` example to copy. Watch them fail, then make them pass.
5. Then `app/verifier.py` (Task 2), same way.

By then you'll have the shape of the codebase and two of the six tasks done.

## Useful to know

- **The scenarios in `app/seed.py` are your test fixtures.** There's one for each path you need to
  handle: `send_followup` (the happy path), `unknown_tool` (a hallucinated tool name),
  `tool_error` (a tool that fails), `three_writes` (the autonomy budget), `never_finishes` (the
  `max_steps` cap), `flaky_provider` (throttled then fine), `bad_credentials` (fatal, don't retry),
  `bad_json_then_good` and `always_bad_json` (malformed model output). Read the comments there.
- **`tests/helpers.py::make_run`** gives you a Run and its dependencies in one line, isolated. Use it
  for every loop test.
- **Everything is synchronous.** Plain `def`, `time.sleep`, no `await` anywhere. If you find
  yourself reaching for `asyncio`, you've gone off the path.
- **Settings are injected, not global.** Your functions take `settings`, so a test can say "budget
  of 1, retry twice" without touching the environment:
  `make_run(script, settings=replace(SETTINGS, max_auto_writes=1))`.
- Once Task 5 is done, `http://127.0.0.1:8000/docs` gives you a UI to create a task and start a run
  without writing any curl. Good for a sanity check that pytest can't give you.

---

# Your write-up

### What's working

All six tasks are done and `pytest` is green.

1. **Governance policy** — `evaluate_gate` in `app/autonomy.py`
2. **Verifier** — `verify` in `app/verifier.py`
3. **Agent loop** — `run_agent` in `app/agent.py`
4. **Resilience** — `complete_with_retry` and idempotent `send_message`
5. **Start-run endpoint** — `POST /api/v1/runs`
6. **Tests** — gate, verifier, retry, idempotency, loop, and HTTP

Nothing is knowingly broken. I did not add the optional extras (per-tool gate overrides, extra verdict summary lines, structured logging).

Drive it from the docs UI at `http://127.0.0.1:8000/docs`: create a task with scenario `send_followup`, then start a run with that `task_id`.

### Design decisions

**What ends a run vs what becomes an observation.** The loop treats unknown tools, `ToolError`, and a rejected reviewer as normal: emit a failed `tool_result`, append an observation, and continue so the model can recover. A run only stops when the model returns `final`, `_decide` never produces valid JSON, `max_steps` is exhausted, or a provider/`Exception` is unrecoverable. Failed runs get `status="failed"` and `run.error` so a caller cannot poll a stuck `"running"` forever. Verification only runs on `completed` runs — a failed run has no verdict.

**The loop is a thin orchestrator.** `_decide`, `_emit`, `_ask_reviewer`, `_execute`, and `_observation` already existed; `run_agent` sequences them and records `Effect`s / `writes_done` on successful writes (including simulated ones, so shadow still consumes budget the same way autonomous would).

**Idempotency.** `_execute` stamps `send_message` with `{run.id}:{len(run.steps)}`. The tool stores the original result in `Workspace._idem`. A repeat key returns that result with `deduped=True` and does not append to `ws.messages`. Missing `contact_id` or `idempotency_key` is a `ToolError`, not a silent send.

**Retries.** Only `ThrottleError` is retried, with `base * 2**attempt` backoff, up to `model_max_retries`. `FatalError` (and anything else) raises immediately. After retries are spent, the last `ThrottleError` propagates and the loop marks the run failed.

**Assumptions I made where the brief was open:**
- Gate `reason` strings are human-readable audit text; tests assert decision flags, not exact wording (except that a reason is present for reads).
- Match in the verifier is a subset check on `args`; extra keys like `idempotency_key` do not prevent a match.
- Each actual effect is spent at most once, in first-match order.
- Simulated effects are not filtered out of verification.
- If `run.task_id` is missing from the store, `run_agent` fails the run rather than throwing.

### Testing approach

I wrote the Task 1 and Task 2 tests **before** the implementations (see commits `b4aa539` then `a226581`, and `0d75f27` then `7cfab87`). Those two are pure functions, so TDD was cheap and caught the budget boundary and one-effect-one-expectation rules.

I did **not** TDD the agent loop itself. The helpers and scenarios already specified the shape; I implemented `run_agent` against the docstring, smoke-checked seed scenarios, then added tests. Tasks 4a/4b tests were written in the same commit as the code, with the assertions the brief asked for (`model.calls == 3` / `== 1`, `len(ws.messages) == 1`).

What I chose to test:
- Gate decision table, including `writes_so_far == max_auto_writes` (budget is 2, not 3)
- Verifier pass / missing / unexpected / simulated / double-expectation
- Retry vs no-retry by **call count**, not only "it raised"
- Idempotency by **workspace messages**, not only the return dict
- Loop: no tools, one verified write, unknown tool recovery, shadow leaves `messages == []`, `never_finishes` fails, fatal credentials fail without escaping
- HTTP: 404 for a missing task, `send_followup` over `POST /runs` returns 201 with a passing verdict

What I deliberately skipped:
- Exhaustive tests of every seed scenario (`tool_error`, `flaky_provider`, `always_bad_json`, `three_writes` budget gating in the loop)
- Exact gate `reason` strings
- Reviewer-rejects path as its own test (the loop handles it; `_ask_reviewer` is provided)

Those would be next if I were tightening coverage, not because the code is untested.

### What was hardest

Keeping the agent loop **boring**. The instinct is to fail the run on an unknown tool or a `ToolError`; the brief is the opposite — those are observations. Reading the five helpers first, then implementing the docstring as a checklist, stopped me from inventing extra control flow.

The verifier's "one effect, one expectation" rule is easy to get wrong if you rescan the full effect list for every expectation. I tracked spent indices instead. The gate's `writes_so_far < max_auto_writes` boundary is the same class of bug: `<=` would silently allow a third write.

Parametrize for the gate felt natural after copying the example in `test_example.py`; the budget rows are one table so an off-by-one fails a named case instead of hiding in a long test.

### What I'd do next

- Add the loop tests I skipped: `three_writes` with `max_auto_writes=1`, reviewer reject, `tool_error`, `flaky_provider`.
- Optional: a per-tool override so `send_message` can still require approval under `autonomous`.
- Optional: put the missing expectation in `Verdict.detail` so a failed run is readable without dumping lists.
- Structured logs with `run.id` as a correlation id (still no extra dependencies).

### Time spent

About 5 focused hours, plus some time reading the scaffold before writing code.
