import os
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from subscript.params2csv import params2csv

try:
    # pylint: disable=unused-import
    import ert.shared  # noqa

    HAVE_ERT = True
except ImportError:
    HAVE_ERT = False


def test_main(tmp_path, mocker):
    """Test invocation from command line"""
    os.chdir(tmp_path)
    Path("parameters1.txt").write_text(
        "\n".join(["FOO     100", "BAR com", "BOGUS", "CONSTANT 1"]), encoding="utf8"
    )

    Path("parameters2.txt").write_text(
        "\n".join(["FOO 200", "BAR dot", "CONSTANT 1", "ONLYIN2 2"]), encoding="utf8"
    )

    mocker.patch("sys.argv", ["params2csv", "parameters1.txt", "parameters2.txt"])
    params2csv.main()

    result = pd.read_csv("params.csv")
    assert "FOO" in result
    assert "BAR" in result
    assert "CONSTANT" not in result
    assert "BOGUS" not in result
    assert "filename" in result
    assert set(result["filename"].values) == set(["parameters1.txt", "parameters2.txt"])

    # Test the cleaning mode:
    mocker.patch(
        "sys.argv", ["params2csv", "--clean", "parameters1.txt", "parameters2.txt"]
    )
    params2csv.main()
    assert Path("parameters2.txt.backup").exists()
    assert Path("parameters1.txt.backup").exists()

    cleanedparams1 = Path("parameters1.txt").read_text(encoding="utf8").splitlines()
    cleanedparams2 = Path("parameters2.txt").read_text(encoding="utf8").splitlines()

    assert len(cleanedparams1) == len(cleanedparams2) == 5

    # Check that the ONLYIN2 parameter was passed on to parameters1.txt:
    assert any("ONLYIN2" in x for x in cleanedparams1)

    # Check that BOGUS was transferred to parameters2.txt:
    assert any("BOGUS" in x for x in cleanedparams2)

    # Check that we allow a file not to exist:
    mocker.patch(
        "sys.argv",
        ["params2csv", "parameters1.txt", "parametersFOO.txt", "parameters2.txt"],
    )
    params2csv.main()
    result = pd.read_csv("params.csv")
    assert "FOO" in result
    assert "BAR" in result
    assert "CONSTANT" not in result
    assert "BOGUS" not in result
    assert "filename" in result
    assert set(result["filename"].values) == set(["parameters1.txt", "parameters2.txt"])


def test_spaces_in_values(tmp_path, mocker):
    """Test that we support spaces in values in parameters.txt
    if they are quoted properly"""
    os.chdir(tmp_path)
    Path("parameters.txt").write_text('somekey "value with spaces"', encoding="utf8")
    # Single-qoutes:
    Path("parameters2.txt").write_text("somekey 'value with spaces'", encoding="utf8")

    mocker.patch("sys.argv", ["params2csv", "--keepconstantcolumns", "parameters.txt"])
    params2csv.main()
    result = pd.read_csv("params.csv")
    assert "somekey" in result
    assert result["somekey"].values[0] == "value with spaces"


def test_spaces_in_values_single_quotes(tmp_path, mocker):
    """Test that single quotes can also be used to support spaces in values"""
    os.chdir(tmp_path)
    Path("parameters.txt").write_text('somekey "value with spaces"', encoding="utf8")

    mocker.patch("sys.argv", ["params2csv", "--keepconstantcolumns", "parameters.txt"])
    params2csv.main()
    result = pd.read_csv("params.csv")
    assert "somekey" in result
    assert result["somekey"].values[0] == "value with spaces"


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["params2csv", "-h"])


@pytest.mark.integration
@pytest.mark.skipif(not HAVE_ERT, reason="Requires ERT to be installed")
def test_ert_forward_model(tmp_path):
    """Test that the ERT hook can run on a mocked case"""
    # pylint: disable=redefined-outer-name
    # pylint: disable=unused-argument
    os.chdir(tmp_path)

    ert_config_fname = "test_params2csv.ert"
    ert_config = [
        "QUEUE_SYSTEM LOCAL",
        "NUM_REALIZATIONS 1",
        "RUNPATH <CONFIG_PATH>",
        f"FORWARD_MODEL PARAMS2CSV(<PARAMETERFILES>={ert_config_fname})",
    ]
    Path(ert_config_fname).write_text("\n".join(ert_config), encoding="utf8")
    subprocess.run(["ert", "test_run", ert_config_fname], check=True)
    dframe = pd.read_csv("parameters.csv")
    assert not dframe.empty
    assert "QUEUE_SYSTEM" in dframe
    assert "filename" in dframe


@pytest.mark.integration
@pytest.mark.skipif(not HAVE_ERT, reason="Requires ERT to be installed")
def test_ert_forward_model_filename_column(tmp_path):
    """Test that the ERT hook can run on a mocked case"""
    # pylint: disable=redefined-outer-name
    # pylint: disable=unused-argument
    os.chdir(tmp_path)

    ert_config_fname = "test_params2csv.ert"
    ert_config = [
        "QUEUE_SYSTEM LOCAL",
        "NUM_REALIZATIONS 1",
        "RUNPATH <CONFIG_PATH>",
        f"FORWARD_MODEL PARAMS2CSV(<PARAMETERFILES>={ert_config_fname},"
        "<FILENAMECOLUMN>=SOURCE_FILE)",
    ]
    Path(ert_config_fname).write_text("\n".join(ert_config), encoding="utf8")
    subprocess.run(["ert", "test_run", ert_config_fname], check=True)
    dframe = pd.read_csv("parameters.csv")
    assert not dframe.empty
    assert "QUEUE_SYSTEM" in dframe
    assert "filename" not in dframe
    assert "SOURCE_FILE" in dframe


@pytest.mark.integration
@pytest.mark.skipif(not HAVE_ERT, reason="Requires ERT to be installed")
def test_ert_workflow(tmp_path):
    """Test that PARAMS2CSV can be run as an ERT workflow/plugin"""
    os.chdir(tmp_path)

    realizations = 3
    for i in range(realizations):
        Path(f"realization-{i}/iter-0").mkdir(parents=True)
        Path(f"realization-{i}/iter-0/parameters.txt").write_text(
            f"real\t{i}", encoding="utf8"
        )

    Path("PARAMS2CSV_ITER0").write_text(
        (
            'PARAMS2CSV "-o" <CONFIG_PATH>/parameters.csv '
            "<CONFIG_PATH>/realization-*/iter-0/parameters.txt"
        )
    )

    ert_config_fname = "test_params2csv.ert"
    ert_config = [
        "QUEUE_SYSTEM LOCAL",
        "NUM_REALIZATIONS 1",
        "RUNPATH <CONFIG_PATH>",
        "",
        "LOAD_WORKFLOW PARAMS2CSV_ITER0",
    ]
    Path(ert_config_fname).write_text("\n".join(ert_config), encoding="utf8")
    subprocess.run(
        ["ert", "workflow", "PARAMS2CSV_ITER0", ert_config_fname], check=True
    )

    dframe = pd.read_csv("parameters.csv")
    assert not dframe.empty
    assert "Realization" in dframe
    assert "real" in dframe
    assert len(dframe.index) == realizations
