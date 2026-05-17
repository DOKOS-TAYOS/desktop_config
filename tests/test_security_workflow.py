from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_security_workflow_runs_pytest_as_module() -> None:
    workflow = PROJECT_ROOT / ".github" / "workflows" / "security.yml"
    workflow_text = workflow.read_text(encoding="utf-8")

    assert ".venv/bin/python -m pytest" in workflow_text
    assert ".venv/bin/pytest" not in workflow_text


def test_dev_requirements_use_patched_pytest_version() -> None:
    requirements = PROJECT_ROOT / "requirements-dev.txt"
    requirements_text = requirements.read_text(encoding="utf-8")

    assert "pytest==9.0.3" in requirements_text
    assert "pytest==9.0.2" not in requirements_text
