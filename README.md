# SunSetup Planner

SunSetup Planner is a Streamlit app that helps people who work or study in front of a screen decide where to place a desk and monitor inside a room to reduce probable screen glare, direct solar heat, and poor daylight ergonomics.

The goal is practical guidance, not fake precision. The model is deliberately transparent: rectangular room in plan view, one main window, one desk, one monitor, real solar position, and human-readable heuristics for glare, heat, and comfort.

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

## Main UX

- The main panel starts with an interactive 2D floor-plan editor.
- Users can drag the desk and monitor, rotate them with on-canvas handles, move the window along its wall, and resize the window width.
- The sidebar is reserved for location, date, weather, presets, and advanced numeric fallback controls.
- The analysis reruns when the gesture is committed, not on every drag frame.

## MVP scope

- Rectangular room.
- One main window in the UI.
- One desk and one monitor.
- One detailed day analysis plus a simple seasonal summary.
- Heuristic geometry, not scientific optical simulation.

## Quick start

### Local run

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Recommended target runtime: Python 3.11+. The project was verified in this workspace with Python 3.12 and keeps the code compatible with Python 3.11 features.

### Run tests

```bash
pytest
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
- requests
- pytest

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

## Streamlit Community Cloud deployment

1. Push this repo to GitHub.
2. Create a new app in Streamlit Community Cloud.
3. Select the repository and branch.
4. Set `streamlit_app.py` as the entrypoint.
5. Deploy without secrets.

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

## Resumen en espanol

SunSetup Planner ayuda a decidir donde colocar mesa y monitor dentro de una habitacion para reducir reflejos en pantalla, calor solar directo y configuraciones incomodas respecto a la luz natural.

### Que incluye este MVP

- Entrada por ciudad o latitud/longitud.
- Editor 2D para mover ventana, mesa y monitor.
- Analisis detallado de un dia en intervalos de 15 minutos.
- Resumen estacional simple.
- Comparador entre configuracion actual y recomendada.
- Plano 2D, timeline y recomendaciones accionables.

### Lo importante sobre precision

No es una simulacion fisica exhaustiva. Es un modelo geometrico razonable, explicable y honesto para tomar mejores decisiones domesticas o de teletrabajo.

### Ejecucion rapida

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
pytest
```
