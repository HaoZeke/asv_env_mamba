# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os
import tempfile
from pathlib import Path

import pytest

from asv.config import Config
from asv import environment as envmod
from asv_env_mamba import Mamba, _find_mamba_cli, _libmamba_create_supported


@pytest.fixture
def conf(tmp_path):
    c = Config()
    c.env_dir = str(tmp_path / "env")
    c.project = "smoke"
    c.repo = str(tmp_path / "repo")
    c.repo_subdir = ""
    c.install_timeout = 900.0
    c.default_benchmark_timeout = 60.0
    c.conda_channels = ["conda-forge"]
    c.conda_environment_file = "IGNORE"
    c.matrix = {}
    return c


def test_create_mamba_has_python(conf):
    if not (_find_mamba_cli() or _libmamba_create_supported()):
        pytest.skip("no working mamba/micromamba or libmambapy")
    os.chdir(tempfile.mkdtemp())
    try:
        env = Mamba(conf, "3.12", {}, {})
    except envmod.EnvironmentUnavailable as e:
        pytest.skip(str(e))
    Path(env._path).mkdir(parents=True, exist_ok=True)
    try:
        env._setup()
    except envmod.EnvironmentUnavailable as e:
        pytest.skip(str(e))
    py_path = Path(env.find_executable("python"))
    assert py_path.exists()
    out = env.run_executable("python", ["-c", "print(7+7)"])
    assert "14" in out
