# Licensed under a 3-clause BSD style license - see LICENSE.rst
import asv_env_mamba
from asv_env_mamba import Mamba, _find_mamba_cli, _libmamba_create_supported


def test_tool_name():
    assert Mamba.tool_name == "mamba"


def test_matches_with_cli_or_api():
    # Host may have micromamba; matches must not crash
    result = Mamba.matches("3.12")
    assert result in (True, False)
    assert Mamba.matches("not-a-version") is False
    if _find_mamba_cli() or _libmamba_create_supported():
        assert result is True


def test_entry_point_metadata():
    from importlib.metadata import entry_points

    eps = entry_points()
    try:
        group = list(eps.select(group="asv.environment_backends"))
    except AttributeError:
        group = list(eps.get("asv.environment_backends", []))
    names = {ep.name: ep.value for ep in group if ep.name == "mamba"}
    assert "mamba" in names
    assert "asv_env_mamba" in names["mamba"]


def test_source_documents_fail_closed_paths():
    import inspect

    src = inspect.getsource(asv_env_mamba)
    assert "EnvironmentUnavailable" in src
    assert "_find_mamba_cli" in src
