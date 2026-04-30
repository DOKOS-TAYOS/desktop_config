# Changelog

## 2026-04-30

- Added a diagnosis layer to the analysis result so the app can explain the dominant risk, the best and worst time windows, and the confidence level of the analysis.
- Improved solar-day generation around daylight saving time changes and reduced heat-risk inflation when forecast radiation is near zero.
- Made recommendations more conservative so the app only presents a change as an improvement when it also reduces the dominant risk in a meaningful way.
- Reworked the Streamlit summary area to surface practical messages first and replaced the fragile AppTest smoke test with deterministic helper coverage that stays clean on Windows.
- Added `pyrightconfig.json` so type checking resolves the project-local `.venv` and local `app.*` imports consistently.
- Tightened the solar typing path so `pyright` passes without changing runtime behavior, and documented the expected `.venv` plus `pyright` workflow in the README.
- Switched the UI to a fixed dark theme, added drag-resize handles for the room and desk with automatic reclamping, expanded room presets, and normalized the visible Spanish copy.
