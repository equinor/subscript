import shutil
from os import path
from pathlib import Path

import pytest
import rstcheck_core.checker
import subscript.hook_implementations.jobs
from ert.shared.plugins.plugin_manager import ErtPluginManager

# pylint: disable=redefined-outer-name


@pytest.fixture
def expected_jobs(path_to_subscript):
    """dictionary of installed jobs with location to config"""
    expected_job_names = [
        "CHECK_SWATINIT",
        "CASEGEN_UPCARS",
        "CSV2OFMVOL",
        "CSV_STACK",
        "ECLCOMPRESS",
        "ECLDIFF2ROFF",
        "ECLGRID2ROFF",
        "ECLINIT2ROFF",
        "ECLRST2ROFF",
        "INTERP_RELPERM",
        "MERGE_RFT_ERTOBS",
        "MERGE_UNRST_FILES",
        "OFMVOL2CSV",
        "PARAMS2CSV",
        "RI_WELLMOD",
        "PRTVOL2CSV",
        "SUNSCH",
        "WELLTEST_DPDS",
    ]
    return {
        name: path.join(path_to_subscript, "config_jobs", name)
        for name in expected_job_names
    }


# Avoid category inflation. Add to this list when it makes sense:
ACCEPTED_JOB_CATEGORIES = ["modelling", "utility"]


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
        for line in Path(job_config).read_text(encoding="utf8").splitlines():
            if not line.strip().startswith("--") and "--" in line:
                assert '"--' in line and " --" not in line


@pytest.mark.integration
def test_executables(expected_jobs):
    """Test executables listed in job configurations exist in $PATH"""
    for _, job_config in expected_jobs.items():
        executable = (
            Path(job_config).read_text(encoding="utf8").splitlines()[0].split()[1]
        )
        assert shutil.which(executable)


def test_hook_implementations_job_docs():
    """For each installed job, we require the associated
    description string to be nonempty, and valid RST markup"""

    plugin_m = ErtPluginManager(plugins=[subscript.hook_implementations.jobs])

    installable_jobs = plugin_m.get_installable_jobs()

    docs = plugin_m.get_documentation_for_jobs()

    assert set(docs.keys()) == set(installable_jobs.keys())

    for job_name in installable_jobs:
        desc = docs[job_name]["description"]
        assert desc != ""
        assert not list(rstcheck_core.checker.check_source(desc))
        category = docs[job_name]["category"]
        assert category != "other"
        assert category.split(".")[0] in ACCEPTED_JOB_CATEGORIES
