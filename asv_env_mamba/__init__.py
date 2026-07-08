# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""ASV ``environment_type="mamba"`` backend.

Resolution order:

1. **libmambapy** when importable and a supported high-level create API exists.
2. Else a **working** micromamba/mamba CLI (``--version`` succeeds).

Broken stubs on PATH are skipped. Fail closed when neither path works.

Core ASV does not ship an in-tree mamba backend; this package is the provider.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from asv import environment, util
from asv.console import log

try:
    import libmambapy as _libmamba
except ImportError:  # pragma: no cover
    _libmamba = None

_HAS_LIBMAMBA = _libmamba is not None


def _cli_works(path: str) -> bool:
    try:
        r = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _find_mamba_cli() -> str | None:
    candidates = []
    for env_key in ("MAMBA_EXE", "MICROMAMBA_EXE", "ASV_MAMBA_EXE"):
        val = os.environ.get(env_key)
        if val:
            candidates.append(val)
    for name in ("micromamba", "mamba"):
        path = shutil.which(name)
        if path:
            candidates.append(path)
    seen = set()
    for cand in candidates:
        if cand in seen:
            continue
        seen.add(cand)
        if os.path.isfile(cand) and os.access(cand, os.X_OK) and _cli_works(cand):
            return cand
    return None


def _libmamba_create_supported() -> bool:
    if _libmamba is None:
        return False
    return any(callable(getattr(_libmamba, name, None)) for name in ("create", "install"))


class Mamba(environment.Environment):
    """Create environments via libmambapy and/or working mamba/micromamba CLI."""

    tool_name = "mamba"
    matrix_install_mode = "create"
    supports_joint_pypi_conda_solve = False
    supports_joint_pypi_solve = False
    project_install_prefers_no_deps = False
    requires_host_tool = "mamba"
    _matches_cache: dict = {}

    def __init__(self, conf, python, requirements, tagged_env_vars):
        self._python = python
        self._requirements = requirements
        self._channels = list(getattr(conf, "conda_channels", None) or [])
        if "conda-forge" not in self._channels:
            self._channels.append("conda-forge")
        self._cli = _find_mamba_cli()
        self._use_api = _libmamba_create_supported()
        if not self._use_api and not self._cli:
            raise environment.EnvironmentUnavailable(
                "asv_env_mamba requires a working micromamba/mamba CLI "
                "(set MAMBA_EXE / MICROMAMBA_EXE / ASV_MAMBA_EXE) or libmambapy "
                "with a create/install helper. Broken binaries on PATH are ignored."
            )
        super().__init__(conf, python, requirements, tagged_env_vars)

    @classmethod
    def matches(cls, python):
        if python not in cls._matches_cache:
            cls._matches_cache[python] = cls._matches(python)
        return cls._matches_cache[python]

    @classmethod
    def _matches(cls, python):
        if not (re.match(r"^[0-9].*$", python) or re.match(r"^pypy[0-9.]*$", python)):
            return False
        return bool(_libmamba_create_supported() or _find_mamba_cli())

    def _spec_list(self):
        specs = [f"python={self._python}", "pip", "wheel"]
        for key, val in {**self._requirements, **self._base_requirements}.items():
            if key.startswith("pip+"):
                continue
            if val:
                specs.append(f"{key}={val}")
            else:
                specs.append(key)
        return specs

    def _setup(self):
        log.info(f"Creating mamba environment for {self.name}")
        if self._use_api:
            try:
                self._setup_libmamba()
            except Exception as err:
                if self._cli:
                    log.warning(f"libmambapy create failed ({err}); falling back to CLI")
                    self._setup_cli()
                else:
                    raise environment.EnvironmentUnavailable(
                        f"libmambapy create failed and no working mamba/micromamba CLI: {err}"
                    ) from err
        else:
            self._setup_cli()
        self._install_pip_requirements()

    def _setup_libmamba(self):
        assert _libmamba is not None
        specs = self._spec_list()
        prefix = str(self._path)
        Path(prefix).mkdir(parents=True, exist_ok=True)
        create = getattr(_libmamba, "create", None)
        if not callable(create):
            raise environment.EnvironmentUnavailable(
                "libmambapy has no callable create(); use micromamba/mamba CLI"
            )
        try:
            create(prefix, specs, channels=self._channels)
        except TypeError:
            create(prefix, specs)

    def _setup_cli(self):
        cli = self._cli or _find_mamba_cli()
        if not cli:
            raise environment.EnvironmentUnavailable("working mamba/micromamba CLI not found")
        specs = self._spec_list()
        cmd = [cli, "create", "-y", "-p", self._path]
        for ch in self._channels:
            cmd.extend(["-c", ch])
        cmd.extend(specs)
        env = dict(os.environ)
        env.update(self.build_env_vars)
        try:
            util.check_call(cmd, env=env, timeout=self._install_timeout)
        except util.ProcessError as err:
            raise environment.EnvironmentUnavailable(
                f"mamba/micromamba create failed for python={self._python!r}: {err}. "
                "Try another Python version or reinstall micromamba/mamba."
            ) from err

    def _install_pip_requirements(self):
        for key, val in {**self._requirements, **self._base_requirements}.items():
            if not key.startswith("pip+"):
                continue
            declaration = f"{key[4:]} {val}" if val else key[4:]
            parsed = util.ParsedPipDeclaration(declaration)
            util.construct_pip_call(self._run_pip, parsed)()

    def _run_pip(self, args, **kwargs):
        return self.run_executable("python", ["-m", "pip"] + list(args), **kwargs)

    def run(self, args, **kwargs):
        log.debug(f"Running '{' '.join(args)}' in {self.name}")
        return self.run_executable("python", args, **kwargs)


__all__ = [
    "Mamba",
    "_HAS_LIBMAMBA",
    "_find_mamba_cli",
    "_libmamba_create_supported",
    "_cli_works",
]
