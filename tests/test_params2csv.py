import os
import sys

import subprocess
import pytest

import pandas as pd

from subscript.params2csv import params2csv


def test_main(tmpdir):
    """Test invocation from command line"""
    tmpdir.chdir()
    with open("parameters1.txt", "w") as f_handle:
        f_handle.write("FOO     100\n")
        f_handle.write("BAR com\n")
        f_handle.write("BOGUS\n")
        f_handle.write("CONSTANT 1\n")

    with open("parameters2.txt", "w") as f_handle:
        f_handle.write("FOO 200\n")
        f_handle.write("BAR dot\n")
        f_handle.write("CONSTANT 1\n")
        f_handle.write("ONLYIN2 2\n")

    sys.argv = ["params2csv", "parameters1.txt", "parameters2.txt"]
    params2csv.main()

    result = pd.read_csv("params.csv")
    assert "FOO" in result
    assert "BAR" in result
    assert "CONSTANT" not in result
    assert "BOGUS" not in result
    assert "filename" in result
    assert set(result["filename"].values) == set(["parameters1.txt", "parameters2.txt"])

    # Test the cleaning mode:
    sys.argv = ["params2csv", "--clean", "parameters1.txt", "parameters2.txt"]
    params2csv.main()
    assert os.path.exists("parameters2.txt.backup")
    assert os.path.exists("parameters1.txt.backup")

    cleanedparams1 = open("parameters1.txt").readlines()
    cleanedparams2 = open("parameters2.txt").readlines()

    assert len(cleanedparams1) == len(cleanedparams2) == 5

    # Check that the ONLYIN2 parameter was passed on to parameters1.txt:
    assert any(["ONLYIN2" in x for x in cleanedparams1])

    # Check that BOGUS was transferred to parameters2.txt:
    assert any(["BOGUS" in x for x in cleanedparams2])

    # Check that we allow a file not to exist:
    sys.argv = ["params2csv", "parameters1.txt", "parametersFOO.txt", "parameters2.txt"]
    params2csv.main()
    result = pd.read_csv("params.csv")
    assert "FOO" in result
    assert "BAR" in result
    assert "CONSTANT" not in result
    assert "BOGUS" not in result
    assert "filename" in result
    assert set(result["filename"].values) == set(["parameters1.txt", "parameters2.txt"])


def test_spaces_in_values(tmpdir):
    """Test that we support spaces in values in parameters.txt
    if they are quoted properly"""
    tmpdir.chdir()
    with open("parameters.txt", "w") as f_handle:
        f_handle.write('somekey "value with spaces"')
    # Single-qoutes:
    with open("parameters2.txt", "w") as f_handle:
        f_handle.write("somekey 'value with spaces'")

    sys.argv = ["params2csv", "--keepconstantcolumns", "parameters.txt"]
    params2csv.main()
    result = pd.read_csv("params.csv")
    assert "somekey" in result
    assert result["somekey"].values[0] == "value with spaces"


def test_spaces_in_values_single_quotes(tmpdir):
    """Test that single quotes can also be used to support spaces in values"""
    tmpdir.chdir()
    with open("parameters.txt", "w") as f_handle:
        f_handle.write('somekey "value with spaces"')

    sys.argv = ["params2csv", "--keepconstantcolumns", "parameters.txt"]
    params2csv.main()
    result = pd.read_csv("params.csv")
    assert "somekey" in result
    assert result["somekey"].values[0] == "value with spaces"


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["params2csv", "-h"])
