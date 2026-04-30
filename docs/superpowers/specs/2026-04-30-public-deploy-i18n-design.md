## SunSetup Planner: Public GitHub + Streamlit Community Cloud + ES/EN I18n

### Goal

Leave the repository ready to be published publicly on GitHub and deployed on Streamlit Community Cloud, while adding a user-facing language switch between Spanish and English.

This iteration is about deployability and public readiness, not about adding new solar-analysis features.

### Scope

- Keep Open-Meteo enabled in the public app.
- Preserve the current fallback to the theoretical weather mode when the API is unavailable or the selected date is out of range.
- Add internationalization for the visible app UI and the most important user-facing result messages.
- Add a clear language switch in the Streamlit UI so the user can toggle between Spanish and English.
- Ensure the repository contains the files and runtime assumptions needed for Streamlit Community Cloud.

### Out of Scope

- More languages beyond Spanish and English.
- Automatic browser-language detection.
- A full translation framework such as `gettext`.
- New product features unrelated to deployment or language support.
- Converting all developer-facing docs and internal comments to both languages.

### Recommended Approach

Use lightweight in-repo internationalization based on translation keys and dictionaries.

Why this approach:

- It keeps the app simple and dependency-free for Streamlit Community Cloud.
- It is easy to test.
- It avoids scattering `if language == ...` throughout the app.
- It scales well enough for a two-language Streamlit application.

### Architecture

#### 1. Translation layer

Add a small module, for example under `app/ui/` or `app/utils/`, with:

- a `LanguageCode` type, limited to `es` and `en`
- a translation dictionary keyed by stable message ids
- a helper such as `translate(key: str, language: LanguageCode, **kwargs) -> str`

The helper should:

- return translated strings for both languages
- support simple interpolation for values such as scores, hours, and labels
- fail safely with a clear fallback if a key is missing

#### 2. Language state

Store the selected language in `st.session_state`.

Behavior:

- default language: Spanish
- visible switch in the main UI, near the top of the app
- user can toggle to English without losing the current scenario state

#### 3. UI integration

Translate:

- page header
- sidebar labels, help text, and buttons
- inspector labels
- analysis summaries
- recommendation messages shown in the UI
- captions and section titles
- model notes and user-facing warnings

The 2D editor custom component should also read the selected language from Python and render its own visible labels in the active language.

#### 4. Result-message translation

Some user-facing strings are currently assembled inside service modules such as:

- `app/services/analysis.py`
- `app/services/recommendations.py`
- `app/services/weather.py`

Those messages should no longer be hardcoded only in one language if they are shown to the user. The implementation should choose one of these two patterns consistently:

- return stable message keys plus structured values, then translate in the UI
- or keep the message-generation logic centralized behind a translation-aware helper

Recommended choice:

- move toward stable message keys for user-visible messages where practical
- keep the refactor scoped so this iteration does not become a large domain rewrite

### Streamlit Community Cloud readiness

#### 1. Runtime and dependencies

Verify that the app runs on Streamlit Community Cloud with the checked-in `requirements.txt`.

The repository should clearly support:

- Python 3.11+
- `streamlit_app.py` as the entrypoint
- the existing custom component assets shipped in the repo

If Streamlit Cloud needs an explicit runtime file or clearer dependency pinning, add it.

#### 2. No-secret deployment

The app should deploy without secrets.

Open-Meteo remains optional at runtime:

- if reachable, use forecast data
- if unreachable or outside the available horizon, degrade gracefully to theoretical mode

#### 3. Public-repo hygiene for deployment

Check for anything that could cause confusion or deployment trouble in a public repo:

- local-only paths or assumptions
- Windows-only instructions where cloud deployment needs cross-platform wording
- missing deploy steps in the README
- ignored files that should not be committed or public

This pass should stay focused on what affects public deployment.

### Testing Strategy

#### Unit tests

Add or update tests for:

- translation lookup in both languages
- language-switch state handling
- key UI helpers that now depend on active language
- fallback behavior if a translation key is missing

#### Integration tests

Keep `pytest` passing for the full suite.

Add at least lightweight coverage for:

- the default language being Spanish
- switching to English producing translated visible strings
- the static Plotly configuration and current editor pipeline remaining unaffected

#### Type checks

`pyright` must continue to pass after the i18n layer is introduced.

### README and deploy guidance

Update the README so a public visitor can:

1. understand what the app does
2. run it locally
3. deploy it to Streamlit Community Cloud
4. understand that the public app supports Spanish and English
5. understand that Open-Meteo is optional and has graceful fallback behavior

### Risks and Mitigations

#### Risk: mixed-language UI

Cause:

- some user-facing strings live in services, some in Streamlit, and some in the custom HTML editor

Mitigation:

- inventory user-facing strings and translate them systematically by layer

#### Risk: deploy-only failure in Streamlit Cloud

Cause:

- runtime assumptions can differ from local Windows development

Mitigation:

- verify imports, entrypoint, requirements, and custom component packaging from the repo root

#### Risk: oversized refactor

Cause:

- moving every user-visible string into a new translation system can spread widely

Mitigation:

- focus on visible user UI and core user-facing messages only
- do not redesign unrelated domain objects unless needed for clean translation boundaries

### Acceptance Criteria

- The repo is ready to publish publicly on GitHub for this app.
- The app is ready to deploy on Streamlit Community Cloud without secrets.
- The app keeps Open-Meteo enabled with graceful fallback.
- The app exposes an ES/EN language switch in the UI.
- The main visible experience works in both Spanish and English.
- `pytest` passes.
- `pyright` passes.
- `ruff check . --fix` and `ruff format .` pass.
