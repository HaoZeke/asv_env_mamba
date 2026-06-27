# asv_env_mamba

ASV environment backend plugin for `environment_type = "mamba"`.

## Install (HaoZeke / editable)

```bash
pip install "git+https://github.com/HaoZeke/asv_env_mamba.git"
# or clone and: pip install -e .
```

## Configure

```json
{
  "environment_type": "mamba",
  "plugins": ["asv_env_mamba"]
}
```

Core ASV ships **virtualenv** only. Plugins use the shared `asv_env_*` naming so they are easy to find and load via the `plugins` list (and optional `asv.plugins` entry points when ASV grows auto-discovery).
