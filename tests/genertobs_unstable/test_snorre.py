import re
import os
from shutil import copytree

from pathlib import Path
from subprocess import Popen, PIPE
from subscript.genertobs_unstable.parse_config import (
    generate_data_from_config,
    read_yaml_config,
)

SNORRE_FOLDER = Path(__file__).parent / "data/snorre"


def run_command(arguments):
    encoding = "utf-8"
    with Popen(
        arguments,
        stdout=PIPE,
        stderr=PIPE,
    ) as process:
        stdout, stderr = process.communicate()
    if stdout:
        print("stdout:", stdout.decode(encoding), sep="\n")
    if stderr:
        print("stderr:", stderr.decode(encoding), sep="\n")


def test_generate_data(tmp_path, monkeypatch):
    sn_tmp = tmp_path / "snorre"
    copytree(SNORRE_FOLDER, sn_tmp)
    obs_name = "snorre_observations"
    monkeypatch.chdir(sn_tmp)

    genert_config = sn_tmp / "snorre_observations.yml"

    config = read_yaml_config(genert_config)
    print("\n", config)
    data = generate_data_from_config(config, sn_tmp)
    print(data)


def test_command_line(tmp_path, monkeypatch):
    sn_tmp = tmp_path / "snorre"
    copytree(SNORRE_FOLDER, sn_tmp)
    obs_name = "snorre_observations"
    monkeypatch.chdir(sn_tmp)
    genert_config = sn_tmp / "snorre_observations.yml"

    arguments = ["genertobs_unstable", genert_config]
    run_command(arguments)
    obs_out = sn_tmp / obs_name
    assert obs_out.exists(), f"{obs_out} does not exist"
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

        assert not name.startswith("NO "), f"NO should've been removed in {name}"

        assert " " not in name, f"Still spaces remaining in name |{name}|"

        name_parts = name.split("_")

        assert len(name_parts) > 1, f"No _ in name {name}"

        assert name_parts[-1] in ["OBS", "SIM"], f"No OBS or SIM part in {name}"

        joined_parts = "_".join(name_parts[:-1])
        assert (
            len(joined_parts) <= 8
        ), f"{joined_parts} should be less than 8 characters, but is {len(joined_parts)}"
