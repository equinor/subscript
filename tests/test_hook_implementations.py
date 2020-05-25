import os
import sys

import pytest

import subscript.hook_implementations.jobs
from ert_shared.plugins.plugin_manager import ErtPluginManager


@pytest.mark.skipif(sys.version_info.major < 3, reason="requires python3")
def test_hook_implementations():
    pm = ErtPluginManager(plugins=[subscript.hook_implementations.jobs])

    expected_jobs = {
        "SUNSCH": "subscript/config_jobs/SUNSCH",
    }
    installable_jobs = pm.get_installable_jobs()
    for wf_name, wf_location in expected_jobs.items():
        assert wf_name in installable_jobs
        assert installable_jobs[wf_name].endswith(wf_location)
        assert os.path.isfile(installable_jobs[wf_name])

    assert set(installable_jobs.keys()) == set(expected_jobs.keys())

    expected_workflow_jobs = {}
    installable_workflow_jobs = pm.get_installable_workflow_jobs()
    for wf_name, wf_location in expected_workflow_jobs.items():
        assert wf_name in installable_workflow_jobs
        assert installable_workflow_jobs[wf_name].endswith(wf_location)

    assert set(installable_workflow_jobs.keys()) == set(expected_workflow_jobs.keys())
