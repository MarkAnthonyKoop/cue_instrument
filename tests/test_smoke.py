"""Smoke test for cue_instrument — design-only project, no importable package."""

def test_readme_exists():
    from pathlib import Path
    assert Path(__file__).parent.parent.joinpath("README.md").exists()
