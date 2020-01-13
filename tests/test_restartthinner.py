"""Test module for restartthinner"""
from __future__ import absolute_import

import sys
import os
import shutil

from subscript.restartthinner import restartthinner


def test_main(tmpdir):
    """Basic testing of the command line application"""
    ecldir = os.path.join(os.path.dirname(__file__), "data/reek/eclipse/model")

    unrst_fname = "2_R001_REEK-0.UNRST"

    shutil.copyfile(ecldir + "/" + unrst_fname, str(tmpdir.join(unrst_fname)))

    tmpdir.chdir()

    orig_rstindices = restartthinner.get_restart_indices(unrst_fname)
    assert len(orig_rstindices) == 4

    sys.argv = ["restartthinner", "-d", "-n", "2", unrst_fname]
    restartthinner.main()

    # Check that dry run did not do anything
    assert os.path.exists(unrst_fname)
    assert len(orig_rstindices) == len(restartthinner.get_restart_indices(unrst_fname))

    # Now go down to two points, this should give us the first and last.
    sys.argv = ["restartthinner", "-n", "2", unrst_fname, "--keep"]
    restartthinner.main()

    assert os.path.exists(unrst_fname)
    assert os.path.exists(unrst_fname + ".orig")  # The backed up file

    new_rstindices = restartthinner.get_restart_indices(unrst_fname)
    assert len(new_rstindices) == 2
    assert new_rstindices[0] == orig_rstindices[0]
    assert new_rstindices[-1] == orig_rstindices[-1]
    assert len(restartthinner.get_restart_indices(unrst_fname + ".orig")) == 4
