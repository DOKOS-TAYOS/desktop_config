# Logging Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add centralized, structured, readable logging across the app with safe Streamlit integration and test coverage.

**Architecture:** Introduce a single logging utility module that configures root logging once and provides lightweight structured event helpers. Instrument the main UI flow plus analysis, recommendation, weather, and validation services with event-based logs while keeping `INFO` concise and `DEBUG` opt-in.

**Tech Stack:** Python `logging`, pytest `caplog`, Streamlit

---

## Chunk 1: Logging Core

### Task 1: Add logging utility module

**Files:**
- Create: `app/utils/logging_utils.py`
- Test: `tests/test_logging_utils.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_build_event_message_contains_event_and_fields():
    ...

def test_setup_logging_uses_env_level(monkeypatch):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_logging_utils.py -v`
Expected: FAIL because module/functions do not exist yet

- [ ] **Step 3: Write minimal implementation**

Add:
- idempotent `setup_logging(force=False)`
- `get_logger(name)`
- `build_event_message(event, **fields)`
- `log_event(logger, level, event, **fields)`
- `bind_context(logger, **fields)` helper

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_logging_utils.py -v`
Expected: PASS

## Chunk 2: Instrument Services

### Task 2: Add logging to weather, validation, analysis, and recommendations

**Files:**
- Modify: `app/services/weather.py`
- Modify: `app/domain/validation.py`
- Modify: `app/services/analysis.py`
- Modify: `app/services/recommendations.py`
- Test: `tests/test_logging_integration.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_weather_fallback_logs_warning(...):
    ...

def test_analysis_logs_start_and_end(...):
    ...

def test_recommendation_logs_summary(...):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_logging_integration.py -v`
Expected: FAIL because events are not logged yet

- [ ] **Step 3: Write minimal implementation**

Instrument:
- weather API success/fallbacks
- validation failures
- analysis start/end and degraded weather mode
- recommendation start/result and optional debug candidate logs

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_logging_integration.py -v`
Expected: PASS

## Chunk 3: Instrument Streamlit and docs

### Task 3: Wire logging into app entrypoint and forms

**Files:**
- Modify: `streamlit_app.py`
- Modify: `app/ui/forms.py`
- Modify: `README.md`
- Test: `tests/test_streamlit_app.py`

- [ ] **Step 1: Write the failing test or regression**

Extend coverage to ensure the app still loads with logging enabled.

- [ ] **Step 2: Run test to verify current gap or preserve baseline**

Run: `pytest tests/test_streamlit_app.py -v`

- [ ] **Step 3: Write minimal implementation**

Add:
- `setup_logging()` at startup
- session/request context helpers in the UI flow
- logging for presets, pending session patch application, analysis triggers, editor commits, and editor fallback
- README section for logging env vars

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_streamlit_app.py -v`
Expected: PASS

## Chunk 4: Final Verification

### Task 4: Full verification

**Files:**
- Verify repo state only

- [ ] **Step 1: Run full test suite**

Run: `pytest -q -p no:cacheprovider`
Expected: all tests pass

- [ ] **Step 2: Run compile check**

Run: `python -m compileall app streamlit_app.py`
Expected: exit 0

- [ ] **Step 3: Review README/logging docs**

Confirm logging env vars and behavior are documented
