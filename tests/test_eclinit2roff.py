import logging
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from subscript import getLogger

logger = getLogger("subscript.ecldiff2roff.ecldiff2roff")
logger.setLevel(logging.INFO)

# pylint: disable=unused-argument  # false positive on fixtures


@pytest.fixture(name="reek_data")
def fixture_reek_data(tmp_path):
    """Prepare a data directory with Reek Eclipse binary output"""
    reekdir = Path(__file__).absolute().parent / "data" / "reek" / "eclipse" / "model"

    reekdest = tmp_path / "reekdata"
    shutil.copytree(reekdir, reekdest, copy_function=os.symlink)
    cwd = os.getcwd()
    os.chdir(reekdest)

    try:
        yield

    finally:
        os.chdir(cwd)


@pytest.mark.integration
def test_ert_integration(tmp_path, reek_data):
    pytest.importorskip("ert")
    os.chdir(tmp_path / "reekdata")
    ert_config = "config.ert"
    Path(ert_config).write_text(
        """
        NUM_REALIZATIONS 1
        RUNPATH .
        FORWARD_MODEL ECLINIT2ROFF(<ECLROOT>=2_R001_REEK-0, \
            <OUTPUT>=reek_init.roff, <PROP>=PORV)
    """,
        encoding="utf-8",
    )

    subprocess.run(["ert", "test_run", "--disable-monitor", ert_config], check=True)
    assert Path("reek_init--porv.roff").exists()
