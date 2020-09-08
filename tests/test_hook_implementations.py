import os
import shutil

import pytest

import subscript.hook_implementations.jobs
from ert_shared.plugins.plugin_manager import ErtPluginManager

EXPECTED_JOBS = {
    "ECLCOMPRESS": "subscript/config_jobs/ECLCOMPRESS",
    "SUNSCH": "subscript/config_jobs/SUNSCH",
    "INTERP_RELPERM": "subscript/config_jobs/INTERP_RELPERM",
}


def test_hook_implementations():
    pm = ErtPluginManager(plugins=[subscript.hook_implementations.jobs])

    installable_jobs = pm.get_installable_jobs()
    for wf_name, wf_location in EXPECTED_JOBS.items():
        assert wf_name in installable_jobs
        assert installable_jobs[wf_name].endswith(wf_location)
        assert os.path.isfile(installable_jobs[wf_name])

    assert set(installable_jobs.keys()) == set(EXPECTED_JOBS.keys())

    expected_workflow_jobs = {}
    installable_workflow_jobs = pm.get_installable_workflow_jobs()
    for wf_name, wf_location in expected_workflow_jobs.items():
        assert wf_name in installable_workflow_jobs
        assert installable_workflow_jobs[wf_name].endswith(wf_location)

    assert set(installable_workflow_jobs.keys()) == set(expected_workflow_jobs.keys())


def test_job_config_syntax():
    """Check for syntax errors made in job configuration files"""
    src_path = os.path.join(os.path.dirname(__file__), "../src")
    for _, job_config in EXPECTED_JOBS.items():
        # Check (loosely) that double-dashes are enclosed in quotes:
        with open(os.path.join(src_path, job_config)) as f_handle:
            for line in f_handle.readlines():
                if not line.strip().startswith("--") and "--" in line:
                    assert '"--' in line and " --" not in line


@pytest.mark.integration
def test_executables():
    """Test executables listed in job configurations exist in $PATH"""
    src_path = os.path.join(os.path.dirname(__file__), "../src")
    for _, job_config in EXPECTED_JOBS.items():
        with open(os.path.join(src_path, job_config)) as f_handle:
            executable = f_handle.readlines()[0].split()[1]
            assert shutil.which(executable)


def test_hook_implementations_job_docs():
    pm = ErtPluginManager(plugins=[subscript.hook_implementations.jobs])

    installable_jobs = pm.get_installable_jobs()

    docs = pm.get_documentation_for_jobs()

    assert set(docs.keys()) == set(installable_jobs.keys())

    for job_name in installable_jobs.keys():
        assert docs[job_name]["description"] != ""
        assert docs[job_name]["category"] != "other"
