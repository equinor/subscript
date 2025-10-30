import contextlib
import io
import subprocess
import time
from os import getcwd

import numpy as np
import pandas as pd


def run_simulator(simulator, data_file_path):
    """Run the given simulator (Eclipse100 or OPM-flow)
    on a DATA file

    Will write to cwd. Caller is responsible for starting
    in a suitable directory.

    If the simulator fails, the stdout and stderr will be printed.

    Args:
        simulator (string): Path to a working reservoir simulator
            executable
        data_file_path (str): Location of DATA file
    Returns:
        None
    """
    simulator_option = []
    if "eclrun" in simulator:
        simulator_option = ["eclipse"]
    if "flow" in simulator:
        simulator_option = ["--parsing-strictness=low"]

    result = subprocess.run(
        [simulator, *simulator_option, data_file_path],
        capture_output=True,
        check=False,
    )
    if (
        "eclrun" in simulator
        and _error_count_from_ecl_stdout(
            result.stdout.decode() + result.stderr.decode()
        )
        > 0
    ):
        # eclrun returns returncode 0 matter what.
        result.returncode = 1

    if (
        result.returncode != 0
        and "ecl" in simulator
        and "LICENSE FAILURE" in result.stdout.decode() + result.stderr.decode()
    ):
        print("Eclipse failed due to license server issues. Retrying in 30 seconds.")
        time.sleep(30)
        result = subprocess.run(
            [simulator, *simulator_option, data_file_path],
            capture_output=True,
            check=False,
        )

    if result.returncode != 0:
        print(result.stdout.decode())
        print(result.stderr.decode())
        raise AssertionError(f"reservoir simulator failed in {getcwd()}")


def _error_count_from_ecl_stdout(stdouterr: str):
    error_count = 0
    for line in stdouterr.splitlines():
        if line.startswith(" Errors"):
            with contextlib.suppress(ValueError):
                error_count = int(line.split("Errors")[1].strip())
    return error_count


# following is copied from pyscal tests/utils.py
def sat_table_str_ok(sat_table_str: str) -> None:
    """Test that a supplied string from SWOF()/SGOF() etc is
    probably ok for Eclipse.

    Number of floats pr. line must be constant
    All numerical lines must be parseable to a rectangular dataframe
    with only floats. The first column must contain only unique values
    for every SATNUM.
    """
    assert sat_table_str

    for line in sat_table_str.splitlines():
        try:
            if not (not line or line.startswith(("S", "--", "/")) or int(line[0]) >= 0):
                raise AssertionError

        except ValueError as e_msg:
            # the int(line[0]) will get here on strings.
            raise AssertionError from e_msg

    assert "-- pyscal: " in sat_table_str

    # On non-comment lines, number of ascii floats should be the same:
    number_lines = [
        line
        for line in sat_table_str.splitlines()
        if line.strip() and line.strip()[0] in ["0", "1", "."]
    ]

    floats_pr_line = {len(line.split()) for line in number_lines}
    # This must be a constant:
    assert len(floats_pr_line) == 1
    # And not more than 4:
    if not next(iter(floats_pr_line)) <= 4:
        print(sat_table_str)
    assert next(iter(floats_pr_line)) <= 4

    float_characters = {len(flt) for flt in " ".join(number_lines).split()}
    digits = 7
    for float_str_length in float_characters:
        assert not 1 < float_str_length < digits + 2
        # float_str_length must be 1 (a pure zero value),
        # or above digits + 1, otherwise it is a sign of some error.

    # And pyscal only emits three or four floats pr. line for all keywords:
    assert next(iter(set(floats_pr_line))) in [3, 4]

    # So we should be able to parse this to a dataframe:
    dframe = pd.read_csv(io.StringIO("\n".join(number_lines)), sep=" ", header=None)
    assert len(dframe) == len(number_lines)

    # The first column holds saturations, for pyscal test-data that
    # is always between zero and 1
    assert 0 <= dframe[0].min() <= dframe[0].max() <= 1

    # Saturations should be unique, but only within each SATNUM.
    # Assert this by checking that the two consecutive numbers in the
    # first column are never the same:
    assert (~np.isclose(dframe[0].diff().dropna(), 0)).all()

    # Second column is never capillary pressure, so there we can enforce the same
    assert 0 <= dframe[1].min() <= dframe[1].max() <= 1
    # And then sometimes for the third column:
    if len(dframe.columns) > 3 or "SOF3" in sat_table_str:
        assert 0 <= dframe[2].min() <= dframe[2].max() <= 1
