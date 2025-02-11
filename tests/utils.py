import contextlib
import subprocess
import time
from os import getcwd


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

    result = subprocess.run(  # pylint: disable=subprocess-run-check
        [simulator] + simulator_option + [data_file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
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
        result = subprocess.run(  # pylint: disable=subprocess-run-check
            [simulator] + simulator_option + [data_file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
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
