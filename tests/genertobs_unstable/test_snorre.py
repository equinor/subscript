import re
import os
from shutil import copytree

from pathlib import Path
from subprocess import Popen, PIPE

SNORRE_FOLDER = Path(__file__).parent / "data/snorre"


def run_command(arguments):
    encoding = "utf-8"
    process = Popen(
        arguments,
        stdout=PIPE,
        stderr=PIPE,
    )
    stdout, stderr = process.communicate()
    if stdout:
        print(stdout.decode(encoding))
    if stderr:
        print(stderr.decode(encoding))


def test_command_line(tmp_path):
    sn_tmp = tmp_path / "snorre"
    copytree(SNORRE_FOLDER, sn_tmp)
    obs_name = "observations"
    os.chdir(sn_tmp)
    genert_config = sn_tmp / "snorre_observations.yml"
    fmu_config = sn_tmp / "masterdata_config.yml"

    arguments = ["genertobs_unstable", genert_config, obs_name, fmu_config]
    run_command(arguments)
    obs_out = sn_tmp / obs_name
    assert obs_out.exists()
    ert_obs_file = obs_out / "ert_observations.obs"
    obs_str = ert_obs_file.read_text()
    val_error_smry = re.findall(r".*VALUE=([^;]+).*ERROR=([^;]+).*;", obs_str)
    value, error = val_error_smry[0]
    assert round(float(error), 2) == round(float(value) / 10, 2)

    rft_well_info = re.findall(
        r"GENERAL_OBSERVATION\s+([^{]+)\s+{DATA=([^;]+)\s+;.*", obs_str
    )
    print(rft_well_info)
    key_name, data_name = rft_well_info[0]

    for name in (key_name, data_name):

        assert not name.startswith("NO ")

        assert " " not in name

        name_parts = name.split("_")

        assert len(name_parts) > 1

        assert name_parts[-1] in ["OBS", "SIM"]

        assert len("_".join(name_parts[:-1])) <= 8
