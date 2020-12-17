import shutil
from os import path

import pytest
import rstcheck
from ert_shared.plugins.plugin_manager import ErtPluginManager

import subscript.hook_implementations.jobs

# pylint: disable=redefined-outer-name


@pytest.fixture
def expected_jobs(path_to_subscript):
    """ dictionary of installed jobs with location to config"""
    expected_job_names = [
        "CSV2OFMVOL",
        "CSV_STACK",
        "ECLCOMPRESS",
        "ECLDIFF2ROFF",
        "ECLGRID2ROFF",
        "ECLINIT2ROFF",
        "ECLRST2ROFF",
        "INTERP_RELPERM",
        "MERGE_RFT_ERTOBS",
        "OFMVOL2CSV",
        "PRTVOL2CSV",
        "SUNSCH",
    ]
    return {
        name: path.join(path_to_subscript, "config_jobs", name)
        for name in expected_job_names
    }


# Avoid category inflation. Add to this list when it makes sense:
ACCEPTED_JOB_CATEGORIES = ["modeling", "utility"]


def test_hook_implementations(expected_jobs):
    """Test that we have the correct set of jobs installed,
    nothing more, nothing less"""
    plugin_m = ErtPluginManager(plugins=[subscript.hook_implementations.jobs])

    installable_jobs = plugin_m.get_installable_jobs()
    for wf_name, wf_location in expected_jobs.items():
        assert wf_name in installable_jobs
        assert installable_jobs[wf_name].endswith(wf_location)
        assert path.isfile(installable_jobs[wf_name])

    assert set(installable_jobs.keys()) == set(expected_jobs.keys())

    expected_workflow_jobs = {}
    installable_workflow_jobs = plugin_m.get_installable_workflow_jobs()
    for wf_name, wf_location in expected_workflow_jobs.items():
        assert wf_name in installable_workflow_jobs
        assert installable_workflow_jobs[wf_name].endswith(wf_location)

    assert set(installable_workflow_jobs.keys()) == set(expected_workflow_jobs.keys())


def test_job_config_syntax(expected_jobs):
    """Check for syntax errors made in job configuration files"""
    for _, job_config in expected_jobs.items():
        # Check (loosely) that double-dashes are enclosed in quotes:
        with open(job_config) as f_handle:
            for line in f_handle.readlines():
                if not line.strip().startswith("--") and "--" in line:
                    assert '"--' in line and " --" not in line


@pytest.mark.integration
def test_executables(expected_jobs):
    """Test executables listed in job configurations exist in $PATH"""
    for _, job_config in expected_jobs.items():
        with open(job_config) as f_handle:
            executable = f_handle.readlines()[0].split()[1]
            assert shutil.which(executable)


def test_hook_implementations_job_docs():
    """For each installed job, we require the associated
    description string to be nonempty, and valid RST markup"""

    plugin_m = ErtPluginManager(plugins=[subscript.hook_implementations.jobs])

    installable_jobs = plugin_m.get_installable_jobs()

    docs = plugin_m.get_documentation_for_jobs()

    assert set(docs.keys()) == set(installable_jobs.keys())

    for job_name in installable_jobs.keys():
        desc = docs[job_name]["description"]
        assert desc != ""
        assert not list(rstcheck.check(desc))
        category = docs[job_name]["category"]
        assert category != "other"
        assert category.split(".")[0] in ACCEPTED_JOB_CATEGORIES
