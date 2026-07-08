# asv_env_mamba

Drop-in ASV backend for `environment_type = "mamba"`.

Resolution order:

1. **libmambapy** when importable with a supported high-level create API
2. Else a **working** micromamba/mamba CLI (`--version` succeeds)

Broken stubs on PATH are skipped.

## Drop-in setup

```bash
# micromamba/mamba on PATH, or set MAMBA_EXE / MICROMAMBA_EXE / ASV_MAMBA_EXE
pip install asv
pip install "git+https://github.com/HaoZeke/asv_env_mamba.git"
# optional API path:
# pip install "asv_env_mamba[api]"
```

```json
{
  "environment_type": "mamba",
  "conda_channels": ["conda-forge"],
  "pythons": ["3.12"]
}
```

## Capabilities

| Flag | Value |
|------|-------|
| `matrix_install_mode` | `create` |
| `supports_joint_pypi_conda_solve` | `False` |
| `requires_host_tool` | `mamba` |

## Discovery

```toml
[project.entry-points."asv.environment_backends"]
mamba = "asv_env_mamba:Mamba"
```

## Tests

```bash
pip install -e ".[test]"
pytest -q
```
