# Logging Design for SunSetup Planner

## Goal

Add a centralized, practical logging system for the Streamlit app so local development and Streamlit Community Cloud runs are easier to diagnose without adding unnecessary infrastructure or dependencies.

## Product intent

The logs should help answer questions like:

- Did the app start with the expected logging configuration?
- What scenario was analyzed and how long did it take?
- Why did the app fall back from live weather to theoretical clear sky?
- Which editor commits actually triggered a recomputation?
- Why did validation fail for a given configuration?
- What recommendation path produced the final improved scenario?

The system should be readable by humans in terminal output and still structured enough to grep or filter by event names and key fields.

## Non-goals

- No external observability vendors.
- No tracing backend.
- No persistent logging database.
- No verbose per-frame editor drag logs.
- No JSON-only pipeline in this iteration.

## Chosen approach

Use the Python standard `logging` module with centralized configuration, a single console handler, and a small helper layer for structured event-style logging.

Why this approach:

- It keeps dependencies stable and minimal.
- It works well in local development and Streamlit Community Cloud.
- It fits the current MVP scope without introducing operational overhead.

## Alternatives considered

### 1. Standard logging with plain structured console output

Chosen.

Pros:

- No new dependency.
- Good fit for Streamlit stdout logs.
- Easy to adopt incrementally.

Cons:

- Not as rich as a dedicated structured logging library.

### 2. Standard logging plus rotating local files

Rejected for now.

Pros:

- Useful for local debugging sessions.

Cons:

- Adds file-path concerns and little value on Streamlit Community Cloud.

### 3. `structlog` or equivalent

Rejected for now.

Pros:

- Stronger structured logging ergonomics.

Cons:

- Adds complexity and dependency weight not justified for the current app.

## Architecture

Add a central logging utility module, proposed path:

- `app/utils/logging_utils.py`

Responsibilities:

- Configure logging once for the whole app.
- Expose `setup_logging()`.
- Expose `get_logger(name)`.
- Expose a small helper for structured events such as `log_event(...)`.
- Expose lightweight context binding helpers for common fields.

The app entrypoint will initialize logging early, before the main UI flow starts.

## Output format

Default format:

`timestamp level logger event=... key=value ...`

Example:

`2026-03-18 13:10:02 INFO app.services.analysis event=analysis_completed comfort=71.2 glare=48.0 heat=33.1 duration_ms=184`

Formatting rules:

- One line per event.
- Stable key ordering where practical.
- Large objects must be summarized rather than dumped raw.
- Unknown values may be omitted instead of logged as noisy placeholders.

## Configuration

Environment variables:

- `SUNSETUP_LOG_LEVEL`
  - default: `INFO`
  - supported values: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- `SUNSETUP_LOG_TIMINGS`
  - default: off
  - when enabled, include timing-heavy diagnostic fields
- `SUNSETUP_DEBUG_CANDIDATES`
  - default: off
  - when enabled, allow recommendation candidate logs in `DEBUG`

If configuration is invalid, the app should fall back to a safe console logger instead of crashing.

## Shared context

When available, logs should include:

- `event`
- `session_id`
- `request_id`
- `analysis_date`
- `location_label`
- `editor_commit_version`

Context rules:

- `session_id` should be stable for the Streamlit session.
- `request_id` should identify a single analysis run or update flow.
- Context should be easy to attach without repeating string formatting everywhere.

## Instrumentation plan

### `streamlit_app.py`

Log:

- app start
- logging configured
- analysis triggered
- editor commit accepted
- editor fallback to numeric mode
- payload issues from the editor

Levels:

- `INFO` for normal milestones
- `WARNING` for degraded flows
- `ERROR` for unexpected UI-layer exceptions we intentionally catch

### `app/ui/forms.py`

Log:

- preset applied
- pending session patch applied
- location resolution mode used
- user-facing validation failures before rendering the message

Levels:

- `INFO` for normal actions
- `WARNING` for invalid or unresolved user input

### `app/services/analysis.py`

Log:

- analysis start
- analysis end
- aggregate scores
- weather mode used
- optional detailed timings

Levels:

- `INFO` for lifecycle events
- `DEBUG` for slot-level diagnostics only when explicitly enabled
- `WARNING` when analysis runs in degraded mode because live weather is unavailable

### `app/services/recommendations.py`

Log:

- recommendation search start
- winning candidate
- delta score achieved
- optional candidate exploration diagnostics

Levels:

- `INFO` for summary events
- `DEBUG` for candidate-level exploration when explicitly enabled

### `app/services/weather.py`

Log:

- geocoding request success
- weather forecast success
- fallback reasons
- malformed payloads or request failures

Levels:

- `INFO` for successful calls
- `WARNING` for graceful fallbacks
- `ERROR` for unexpected parsing or request handling problems

### `app/services/solar.py`

Log:

- normally silent in `INFO`
- optional `DEBUG` on targeted solar diagnostics if needed later

### `app/domain/validation.py`

Log:

- validation failures with short, actionable context

Levels:

- `WARNING`

## Noise policy

- Do not log every micro-movement from the editor while dragging.
- Log only on commit or meaningful failure.
- Keep `INFO` readable as a narrative of a real session.
- Use `DEBUG` for details that are only useful during active debugging.

## Error handling

Requirements:

- Logging must never become a reason for the app to fail.
- If the custom formatter or configuration fails, fall back to a minimal console configuration.
- Do not log secrets.
- Do not log full request payloads from external HTTP calls.
- Do not dump the entire editor scene unless specifically summarized in debug mode.

## Testing strategy

Add tests for:

- logging configuration respects `SUNSETUP_LOG_LEVEL`
- structured helper output includes `event=` and expected key fields
- weather fallback logs a `WARNING`
- analysis emits start and end events
- recommendation flow emits summary events

Testing principles:

- Assert key event markers, not brittle full-line equality.
- Avoid tests tied to wall-clock timestamps.
- Keep tests focused on behavior, not implementation details.

## File changes expected

- New: `app/utils/logging_utils.py`
- Update: `streamlit_app.py`
- Update: `app/ui/forms.py`
- Update: `app/services/analysis.py`
- Update: `app/services/recommendations.py`
- Update: `app/services/weather.py`
- Update: `app/domain/validation.py`
- New or updated tests under `tests/`
- Update: `README.md` with logging env vars and usage notes

## Risks and mitigations

### Risk: too much log noise

Mitigation:

- Keep `INFO` lean
- gate verbose diagnostics behind `DEBUG` and feature flags

### Risk: duplicated handlers on rerun

Mitigation:

- make logging setup idempotent
- mark configured handlers or guard setup with module state

### Risk: brittle tests

Mitigation:

- assert on event names and key fields rather than exact full strings

## Acceptance criteria

- App configures logging once per process safely.
- Console logs are readable locally and in Streamlit Cloud.
- Analysis, recommendation, weather fallback, validation, and editor commits emit useful events.
- No widget-driven rerun flow is broken by the new logging.
- Tests cover configuration and representative logging behavior.
