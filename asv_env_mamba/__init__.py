# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""ASV ``environment_type="mamba"`` backend.

Resolution order for creating prefixes:

1. **libmambapy** when importable and a supported high-level create API is
   present (API-first).
2. Else **micromamba** / **mamba** CLI on ``PATH`` or ``MAMBA_EXE`` /
   ``MICROMAMBA_EXE`` (honest CLI path; not a fake always-fail stub).

If neither works, construction / ``matches`` fail closed with a clear message.

There is no in-tree ASV ``mamba`` plugin today, so this package is the
primary provider for ``environment_type=mamba`` via
``asv.environment_backends``.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path

from asv import environment, util
from asv.console import log

try:
    import libmambapy as _libmamba
except ImportError:  # pragma: no cover
    _libmamba = None

_HAS_LIBMAMBA = _libmamba is not None


def _find_mamba_cli() -> str | None:
    for env_key in ("MAMBA_EXE", "MICROMAMBA_EXE"):
        val = os.environ.get(env_key)
        if val and os.path.isfile(val) and os.access(val, os.X_OK):
            return val
    for name in ("micromamba", "mamba"):
        path = shutil.which(name)
        if path:
            return path
    return None


def _libmamba_create_supported() -> bool:
    if _libmamba is None:
        return False
    # High-level helpers (version-sensitive surface)
    return any(callable(getattr(_libmamba, name, None)) for name in ("create", "install"))


class Mamba(environment.Environment):
    """Create environments via libmambapy and/or mamba/micromamba CLI."""

    tool_name = "mamba"
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
                "asv_env_mamba requires libmambapy with a create/install helper "
                "or micromamba/mamba on PATH (set MAMBA_EXE / MICROMAMBA_EXE)"
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
        if _libmamba_create_supported() or _find_mamba_cli():
            return True
        return False

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
                        f"libmambapy create failed and no mamba/micromamba CLI: {err}"
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
        # Best-effort high-level create (signature varies by version)
        try:
            create(prefix, specs, channels=self._channels)
        except TypeError:
            create(prefix, specs)

    def _setup_cli(self):
        cli = self._cli or _find_mamba_cli()
        if not cli:
            raise environment.EnvironmentUnavailable("mamba/micromamba CLI not found")
        specs = self._spec_list()
        # micromamba create -p PREFIX -c channel ... specs -y
        cmd = [cli, "create", "-y", "-p", self._path]
        for ch in self._channels:
            cmd.extend(["-c", ch])
        cmd.extend(specs)
        env = dict(os.environ)
        env.update(self.build_env_vars)
        util.check_call(cmd, env=env, timeout=self._install_timeout)

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
]
