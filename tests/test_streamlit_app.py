from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_app_smoke_loads_without_exceptions():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py"))

    app.run(timeout=120)

    assert len(app.title) == 1
    assert len(app.exception) == 0
