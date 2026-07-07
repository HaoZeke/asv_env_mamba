# asv_env_mamba

ASV environment backend for `environment_type = "mamba"`.

## How it creates environments

1. **libmambapy** (optional extra `asv_env_mamba[api]`) when a high-level
   `create`/`install` helper is available.
2. Else **micromamba** or **mamba** CLI (`PATH`, or `MAMBA_EXE` /
   `MICROMAMBA_EXE`).

If neither is available, resolve/`Environment` construction **fail closed**
with a clear message (no installable-but-always-broken stub).

There is no in-tree ASV `mamba` plugin; this package is the primary provider
for this type under Stage-1 discovery.

## Stage-1 discovery

```toml
[project.entry-points."asv.environment_backends"]
mamba = "asv_env_mamba:Mamba"
```

```bash
pip install "git+https://github.com/HaoZeke/asv_env_mamba.git"
# optional: conda install libmambapy  # then pip install 'asv_env_mamba[api]'
```

```json
{ "environment_type": "mamba" }
```

## Tests

```bash
pip install -e ".[test]"
pytest -q
```
