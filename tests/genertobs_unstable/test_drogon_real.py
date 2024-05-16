import os
from shutil import copytree
from subprocess import Popen, PIPE
from pathlib import Path
from subscript.genertobs_unstable import main

DROGON = Path(__file__).parent / "data/drogon/"

DROGON_ERT_MODEL = DROGON / "ert/model/genertobs.ert"

UPLOAD_JOB = Path(__file__).parents[2] / "src/subscript/config_jobs/WF_UPLOAD_SUMO_OBS"


def write_ert_config_and_run(scratch_path, obs_path):
    encoding = "utf-8"
    os.chdir(scratch_path / "ert/model")

    ert_config = DROGON_ERT_MODEL.read_text()
    ert_config = ert_config.replace("/scratch/fmu", str(scratch_path))
    print(ert_config)
    tmp_drogon_ert = scratch_path / "ert/model" / DROGON_ERT_MODEL.name

    upload_job = scratch_path / f"ert/bin/workflows/{UPLOAD_JOB.name}"
    upload_job.write_text(UPLOAD_JOB.read_text())
    xhook_path = obs_path / "xhook_upload_observations.ert"

    xhook_contents = f"LOAD_WORKFLOW_JOB {str(upload_job)}\n {xhook_path.read_text()}"
    print(xhook_contents)
    xhook_path.write_text(xhook_contents)
    ert_config += f"\nINCLUDE {str(xhook_path)}"
    tmp_drogon_ert.write_text(ert_config)
    runpath = scratch_path / DROGON_ERT_MODEL.stem / "realization-0/iter-0"
    print(f"{str(runpath)}")
    process = Popen(
        ["ert", "test_run", str(tmp_drogon_ert)],
        stdout=PIPE,
        stderr=PIPE,
    )
    stdout, stderr = process.communicate()
    if stdout:
        print(stdout.decode(encoding))
    if stderr:
        print(stderr.decode(encoding))
    assert Path(
        runpath / "OK"
    ).is_file(), f"running {tmp_drogon_ert}, ended with errors"


def test_integration(tmp_path, masterdata_config):
    drogon_path = tmp_path / "drogon"
    copytree(DROGON, drogon_path)
    genert_config_name = "genertobs_config.yml"
    tmp_observations = drogon_path / "ert/input/observations/genertobs"
    test_config = drogon_path / f"ert/input/observations/{genert_config_name}"

    main.run(test_config, tmp_observations, masterdata_config)
    write_ert_config_and_run(drogon_path, tmp_observations)
