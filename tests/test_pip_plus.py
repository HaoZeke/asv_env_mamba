# Licensed under a 3-clause BSD style license - see LICENSE.rst
from pathlib import Path


def test_pip_plus_not_silently_dropped():
    root = Path(__file__).resolve().parents[1]
    src = (root / "asv_env_mamba/__init__.py").read_text()
    assert "pip+" in src
    # must have an install path after skip/continue of conda-only loops
    assert "_install_pip_requirements" in src
    # forbid only-continue pattern without later pip install helper
    assert "_run_pip" in src or "pip_install" in src or "construct_pip_call" in src
