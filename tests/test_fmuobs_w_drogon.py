import os
from pathlib import Path
import pytest
from subscript.fmuobs.parsers import expand_includes


@pytest.fixture(name="drogon_obs_file")
def _fix_drogon():
    """Return path to observation file

    Returns:
        PosixPath: the path to observation file
    """
    obs_file_path = (
        Path(__file__).parent
        / "testdata_fmuobs/drogon/drogon_wbhp_rft_wct_gor_tracer_plt.obs"
    )
    if not obs_file_path.exists():
        raise FileNotFoundError(f"Cannot find observation file {obs_file_path}")
    return obs_file_path


def test_expand_includes(drogon_obs_file):
    """test expand_includes function with drogon_observation file

    Args:
        drogon_obs_file (PosixPath): ert observation file to parse
    """
    obs_text = expand_includes(drogon_obs_file.read_text())
    print(obs_text)
