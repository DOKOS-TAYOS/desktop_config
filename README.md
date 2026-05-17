# SunSetup Planner

SunSetup Planner is a Streamlit app that helps people who work or study in front of a screen decide where to place a desk and monitor inside a room to reduce probable screen glare, direct solar heat, and poor daylight ergonomics.

The goal is practical guidance, not fake precision. The model is deliberately transparent: rectangular room in plan view, one main window, one desk, one monitor, real solar position, and human-readable heuristics for glare, heat, and comfort.

## In one sentence

You describe a room, place the window, desk, and monitor, and the app tells you when that setup is comfortable and how to improve it.

## Why it exists

Many home-office setups fail in very predictable ways:

- a west-facing room feels fine at noon and terrible at 18:00
- a desk looks well placed until the sun hits the monitor directly
- natural light helps in one season and becomes uncomfortable in another

This project turns those tradeoffs into a simple, explainable planning tool.

## What it does

- Resolves a location by city or manual latitude/longitude.
- Computes solar position across the day with `pvlib`.
- Estimates when the sun can enter through the main window.
- Flags likely glare on the screen, direct sun on the desk, and ergonomic issues.
- Builds a recommended variant by testing small desk and monitor adjustments.
- Shows a daily timeline, a 2D room plan, a comfort breakdown, a seasonal summary, and a current-vs-recommended comparison.
- Uses Open-Meteo when forecast data is available and falls back to a theoretical clear-sky model when it is not.
- Includes an in-app language switch so the public app can be used in Spanish or English.

## Who it is for

- People setting up a home office or study space.
- Users comparing room layouts before moving furniture.
- Anyone who wants a reasonable daylight and glare check without learning a CAD or lighting-simulation tool.

## What the app gives you

- A visual 2D editor of the room.
- A daily risk timeline across the selected date.
- A current-layout score for glare, heat, and ergonomics.
- A recommended alternative layout when the current one can be improved.
- A short diagnosis in plain language to explain the main problem.

## Main UX

- The main panel starts with an interactive 2D floor-plan editor.
- Users can drag the desk and monitor, rotate them with on-canvas handles, move the window along its wall, and resize the window width.
- The sidebar is reserved for location, date, weather, presets, and advanced numeric fallback controls.
- The analysis reruns when the gesture is committed, not on every drag frame.
- The result charts are intentionally static to avoid confusing less technical users with zoom, pan, or toolbar controls.

## How to use the app

1. Open the app and choose the interface language.
2. Enter your city, or type the latitude and longitude manually.
3. Set the room size and place the main window on the correct wall.
4. Move and rotate the desk and monitor in the editor until they roughly match the real room.
5. Pick the date you care about most, for example a summer afternoon or winter morning.
6. Press `Update analysis` to compute the results.
7. Read the diagnosis, timeline, and comparison panels.
8. If the app proposes a better layout, compare it with your current one and decide whether the suggested movement is realistic in your room.

## How to read the results

- `comfort_score`: overall convenience of the setup for the selected day.
- `glare_score`: risk of reflections or uncomfortable backlighting on the screen.
- `heat_score`: risk of direct solar exposure on the desk area.
- `ergonomic_score`: daylight orientation and monitor/desk placement quality.
- `Current vs recommended`: the most practical summary if you only want to know whether moving the setup is worth it.

This is a planning tool, not a scientific certification. A result is most useful as a comparative guide between two or three plausible layouts.

## MVP scope

- Rectangular room.
- One main window in the UI.
- One desk and one monitor.
- One detailed day analysis plus a simple seasonal summary.
- Heuristic geometry, not scientific optical simulation.

## Quick start

### Local run

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Recommended target runtime: Python 3.11+. The project was verified in this workspace with Python 3.12 and keeps the code compatible with Python 3.11 features.

For local development, install the development tools as well:

```bash
pip install -r requirements-dev.txt
```

If you are on Windows PowerShell, a typical first run looks like this:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run streamlit_app.py
```

### Run tests

```bash
python -m pytest
```

### Run formatting, type, and security checks

```bash
python -m ruff check .
python -m ruff format . --check
python -m pyright
python -m pip_audit --local
```

### Run type checks

`pyright` is configured to use the project-local `.venv` and the repository root as the import base for `app.*`.

```bash
pyright
```

### Logging

The app includes structured console logging designed to work well both locally and on Streamlit Community Cloud.

Environment variables:

- `SUNSETUP_LOG_LEVEL`
  - default: `INFO`
  - supported values: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- `SUNSETUP_LOG_TIMINGS`
  - optional flag for more timing-oriented diagnostics
- `SUNSETUP_DEBUG_CANDIDATES`
  - optional flag to show recommendation candidate improvements in `DEBUG`

Example:

```bash
SUNSETUP_LOG_LEVEL=DEBUG streamlit run streamlit_app.py
```

Example log line:

```text
2026-03-18 13:10:02 INFO app.services.analysis event=analysis_completed comfort_score=71.2 glare_score=48.0 heat_score=33.1 duration_ms=184.0
```

## Project structure

```text
streamlit_app.py
app/
  domain/
  services/
  ui/
  utils/
tests/
assets/
.streamlit/config.toml
requirements.txt
requirements-dev.txt
.github/
README.md
LICENSE
```

## Technical stack

- Python
- Streamlit
- Plotly
- pandas
- numpy
- pvlib

Development tooling:

- pytest
- Ruff
- Pyright
- pip-audit

Weather HTTP access uses Python's standard-library `urllib`, while Streamlit still brings its own transitive networking dependencies.

## Security posture

- Production dependencies are pinned in `requirements.txt`; development-only tools live in `requirements-dev.txt`, so Streamlit Community Cloud installs a smaller runtime dependency set.
- No secrets are required for the default public app. If secrets are added later, keep `.streamlit/secrets.toml` and `.env*` files out of git and use Streamlit Community Cloud's app settings.
- Dependabot is configured for Python dependencies and GitHub Actions in `.github/dependabot.yml`.
- The GitHub Actions security workflow runs Ruff, Pyright, pytest, Dependency Review on pull requests, and `pip-audit` on the installed dependency environment.
- Keep these GitHub repository settings enabled: Dependency Graph, Dependabot alerts, Dependabot security updates, code scanning default setup, and secret scanning/push protection when available for the repo.

## How the model works

1. The room is represented in 2D with a rectangular footprint and one main window attached to a wall.
2. The sun position is computed for each 15-minute slot of the selected day.
3. A simplified 3D ray is projected from the window into the room.
4. The app checks whether that ray reaches the desk plane, the monitor plane, or a backlighting condition near the user's line of sight.
5. It scores:
   - `glare_score`: likely screen reflection or bad backlighting.
   - `heat_score`: direct solar exposure on desk/work zone, modulated by weather when available.
   - `ergonomic_score`: poor daylight orientation, monitor/desk misalignment, and eye-height mismatch.
6. A composite `comfort_score` is derived from those risks.

Weights used in the MVP:

- Glare: `0.45`
- Heat: `0.35`
- Ergonomics: `0.20`

## Public repo notes

- No secrets are required.
- No private APIs or paid services are required.
- Open-Meteo is optional and used opportunistically.
- The app remains usable if weather lookups fail.
- The interactive editor is a local Streamlit custom component shipped inside the repo.
- The public UI supports both Spanish and English with an in-app language switch.

## Streamlit Community Cloud deployment

1. Push this repo to GitHub.
2. Create a new app in Streamlit Community Cloud.
3. Select the repository, branch, and `streamlit_app.py` as the entrypoint.
4. In Advanced settings, choose the same Python version used locally. This project is verified with Python `3.12`.
5. Deploy without secrets.
6. If Open-Meteo is temporarily unavailable, the app will fall back to the theoretical clear-sky mode automatically.

Deployment notes:

- `requirements.txt` is already in the repository root, which is the expected location for this project layout.
- `.streamlit/config.toml` is already in the repository root, which is the correct location for Streamlit app configuration.
- No `packages.txt` is required for the current dependency set.
- No secrets are required for the default public deployment.
- Only `requirements.txt` is used for the deployed app. `requirements-dev.txt` is for local checks and GitHub Actions.

## Limitations

- The model uses heuristics and simplified geometry.
- It does not simulate blinds, curtains, neighboring buildings, deep shading, or multiple reflections.
- The seasonal summary is based on representative dates and theoretical sky assumptions.
- One main window is exposed in the current UI.
- The weather integration only uses forecast data when the selected date is inside the available horizon.
- The editor is 2D only in this MVP. There is no 3D scene or live optical path tracing.

## Roadmap

- Multiple windows and wall openings.
- Window height and sill as editable user inputs.
- Blinds and shading presets.
- Better seasonal comparison across custom date ranges.
- Exportable scenario reports.
- Saved scenarios and shareable links.

## Suggested screenshots

See [assets/README.md](assets/README.md) for placeholder names to replace with real captures.

---

## Resumen en español

SunSetup Planner ayuda a decidir dónde colocar mesa y monitor dentro de una habitación para reducir reflejos en pantalla, calor solar directo y configuraciones incómodas respecto a la luz natural.

### Qué incluye este MVP

- Entrada por ciudad o latitud/longitud.
- Editor 2D para mover ventana, mesa y monitor.
- Análisis detallado de un día en intervalos de 15 minutos.
- Resumen estacional simple.
- Comparador entre configuración actual y recomendada.
- Plano 2D, timeline y recomendaciones accionables.
- Selector visible de idioma entre español e inglés.

### Cómo se usa

1. Indica ciudad o coordenadas.
2. Dibuja la habitación en el editor y coloca ventana, mesa y monitor.
3. Elige fecha.
4. Pulsa `Update analysis`.
5. Revisa diagnóstico, timeline y propuesta recomendada.

### Lo importante sobre la precisión

No es una simulación física exhaustiva. Es un modelo geométrico razonable, explicable y honesto para tomar mejores decisiones domésticas o de teletrabajo.

### Ejecución rápida

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
pytest
```
