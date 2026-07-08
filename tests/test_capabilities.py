# Licensed under a 3-clause BSD style license - see LICENSE.rst
from asv_env_mamba import Mamba


def test_capability_attrs():
    assert Mamba.matrix_install_mode == 'create'
    assert Mamba.requires_host_tool == 'mamba'

