import subprocess
from pathlib import Path

import pytest

from subscript.gen_satfunc import gen_satfunc

EXAMPLE = """ --Example Configuration file for gen_satfunc.py

COMMENT Relperm curve for fantasy field
SWOF
RELPERM 4 2 1   3 2 1   0.15 0.10 0.5 20
RELPERM 4 1 1   4 2 1   0.14 0.12 0.3 20
RELPERM 4 3 1   3 3 1   0.13 0.11 0.6 20
RELPERM 4 1 0.5 3 2 0.5 0.16 0.09 0.4 20
"""


@pytest.mark.integration
def test_integration():
    """Test that endpoint is installed"""
    assert subprocess.check_output(["gen_satfunc", "-h"])


def test_gen_satfunc(tmpdir, mocker):
    """Test the main function and its args handling"""
    tmpdir.chdir()

    Path("relperm.conf").write_text(EXAMPLE)

    mocker.patch("sys.argv", ["gen_satfunc", "relperm.conf", "swof.inc"])
    gen_satfunc.main()

    assert Path("swof.inc").exists()
    assert len(Path("swof.inc").read_text().splitlines()) > 50

    Path("relpermpc.conf").write_text(
        """
SWOF
RELPERM 4 2 1   3 2 1   0.15 0.10 0.5 20 100 0.2 0.22 -0.5 30
"""
    )
    mocker.patch("sys.argv", ["gen_satfunc", "relpermpc.conf", "swofpc.inc"])
    gen_satfunc.main()
    assert Path("swofpc.inc").exists()
    swofpclines = Path("swofpc.inc").read_text().splitlines()
    assert len(swofpclines) > 20
    assert any(["sigma_costau=30" in x for x in swofpclines])
