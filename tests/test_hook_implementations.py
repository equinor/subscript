import os
import sys

import pytest

import subscript.hook_implementations.jobs
from ert_shared.plugins.plugin_manager import ErtPluginManager


@pytest.mark.skipif(sys.version_info.major < 3, reason="requires python3")
def test_hook_implementations():
    pm = ErtPluginManager(plugins=[subscript.hook_implementations.jobs])

    expected_jobs = {
        "ECLCOMPRESS": "subscript/config_jobs/ECLCOMPRESS",
        "SUNSCH": "subscript/config_jobs/SUNSCH",
    }
    installable_jobs = pm.get_installable_jobs()
    for wf_name, wf_location in expected_jobs.items():
        assert wf_name in installable_jobs
        assert installable_jobs[wf_name].endswith(wf_location)
        assert os.path.isfile(installable_jobs[wf_name])

    # Check executable bit is set on the EXECUTABLE path in
    # each job file (assuming it is always on the first line)
    src_path = os.path.join(os.path.dirname(__file__), "../src")
    for _, job_config in expected_jobs.items():
        executable_path = (
            open(os.path.join(src_path, job_config)).readlines()[0].split()[1]
        )
        assert os.access(
            os.path.join(src_path, "subscript/config_jobs", executable_path), os.X_OK
        )

    assert set(installable_jobs.keys()) == set(expected_jobs.keys())

    expected_workflow_jobs = {}
    installable_workflow_jobs = pm.get_installable_workflow_jobs()
    for wf_name, wf_location in expected_workflow_jobs.items():
        assert wf_name in installable_workflow_jobs
        assert installable_workflow_jobs[wf_name].endswith(wf_location)

    assert set(installable_workflow_jobs.keys()) == set(expected_workflow_jobs.keys())
