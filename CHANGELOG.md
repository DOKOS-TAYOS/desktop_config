# Changelog

## 2026-05-01

- Ran a final publication-readiness check for public GitHub and Streamlit deployment.
- Verified the current codebase with `pytest` and `pyright`.
- Added `THIRD_PARTY_LICENSES.md` with a reviewed inventory of installed Python dependencies and their reported licenses.
- Documented that the repository license is MIT, while the installed dependency set includes one weak-copyleft package (`certifi`, `MPL-2.0`), so not every installed dependency is permissive.
- Replaced the app's direct `requests` usage with standard-library `urllib` for Open-Meteo calls and removed `requests` from the direct dependency list, while documenting that `streamlit` still installs it transitively.

## 2026-04-30

- Added a diagnosis layer to the analysis result so the app can explain the dominant risk, the best and worst time windows, and the confidence level of the analysis.
- Improved solar-day generation around daylight saving time changes and reduced heat-risk inflation when forecast radiation is near zero.
- Made recommendations more conservative so the app only presents a change as an improvement when it also reduces the dominant risk in a meaningful way.
- Reworked the Streamlit summary area to surface practical messages first and replaced the fragile AppTest smoke test with deterministic helper coverage that stays clean on Windows.
- Added `pyrightconfig.json` so type checking resolves the project-local `.venv` and local `app.*` imports consistently.
- Tightened the solar typing path so `pyright` passes without changing runtime behavior, and documented the expected `.venv` plus `pyright` workflow in the README.
- Switched the UI to a fixed dark theme, added drag-resize handles for the room and desk with automatic reclamping, expanded room presets, and normalized the visible Spanish copy.
- Locked all Plotly result charts into a static mode with no toolbar, zoom, or pan controls so the analysis panels are easier to read for end users.
- Added a public-facing ES/EN language switch, translated the main Streamlit UI and the floor-plan editor, and clarified the repository's Streamlit Community Cloud deployment guidance while keeping Open-Meteo fallback behavior.
- Reworked recommendation search so desk and monitor rotation are chosen from a global sweep plus local refinement, which avoids chained “rotate 30° twice” guidance and produces a single better estimate.
- Adjusted the daily comfort rollup so it reflects not only the average but also the worst slice of the day, which better matches layouts that feel fine overall but have clearly bad periods.
- Switched the UI to manual analysis updates, so editing the floor plan or numeric controls no longer triggers a heavy recomputation until the user explicitly asks for it.
- Added session-level caching and deferred loading for the most expensive analysis, recommendation, and chart modules, which reduces both the first-load delay and repeated recalculations for the same scenario.
- Moved the 2D plan legend higher above the plotting area so it no longer overlaps the room drawing when several series are visible.
- Fixed the advanced sidebar window-center slider so its valid range adapts to the actual wall span and window width, avoiding crashes after dragging the window close to a wall edge.
- Hardened the same window-center slider against tiny floating-point overflows by clamping the stored value to the computed range before Streamlit renders the control.
- Added a second `Update analysis` button inside the inspector, directly below the monitor centering action when that block is visible, so manual recalculation is easier while editing.
- Added a permanent scale bar and a recommended-layout ghost overlay inside the 2D editor, so movement suggestions such as `25 cm south` can be understood visually on the plan itself.
- Prevented the editor from snapping back to the last analyzed layout when a transient validation issue appears near a boundary by keeping the latest edited draft request in session state.
- Hardened the editor-to-request conversion so a desk returned from the browser near a wall is reclamped before analysis, which avoids `desk must remain inside the room bounds` crashes after edge drags.
- Relaxed room-bound validation with the shared geometry epsilon so a rotated desk can touch a wall corner without triggering a false out-of-bounds error from floating-point rounding.
