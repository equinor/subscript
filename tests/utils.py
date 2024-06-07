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
    if "runeclipse" in simulator:
        simulator_option = ["-i"]
    if "flow" in simulator:
        simulator_option = ["--parsing-strictness=low"]

    result = subprocess.run(  # pylint: disable=subprocess-run-check
        [simulator] + simulator_option + [data_file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if (
        result.returncode != 0
        and "runeclipse" in simulator
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
