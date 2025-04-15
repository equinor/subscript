import pytest
import rstcheck_core.checker
from ert.plugins.plugin_manager import ErtPluginManager

import subscript.hook_implementations.forward_model_steps

EXPECTED_STEPS = [
    "CHECK_SWATINIT",
    "CASEGEN_UPCARS",
    "CSV2OFMVOL",
    "CSV_STACK",
    "ECLCOMPRESS",
    "ECLDIFF2ROFF",
    "ECLGRID2ROFF",
    "ECLINIT2ROFF",
    "ECLRST2ROFF",
    "GRAV_SUBS_MAPS",
    "GRAV_SUBS_POINTS",
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

# Avoid category inflation. Add to this list when it makes sense:
ACCEPTED_STEP_CATEGORIES = ["modelling", "utility"]


def test_hooks_are_installed_in_erts_plugin_manager():
    """Test that we have the correct set of steps installed,
    nothing more, nothing less"""
    plugin_m = ErtPluginManager(
        plugins=[subscript.hook_implementations.forward_model_steps]
    )

    available_fm_steps = [step().name for step in plugin_m.forward_model_steps]
    assert set(EXPECTED_STEPS) == set(available_fm_steps)


@pytest.mark.integration
def test_executables_exists():
    """Test executables requested exist in $PATH"""
    plugin_m = ErtPluginManager(
        plugins=[subscript.hook_implementations.forward_model_steps]
    )

    steps = [step() for step in plugin_m.forward_model_steps]
    for step in steps:
        assert step.executable is not None


def test_hook_implementations_docs():
    """For each installed job, we require the associated
    description string to be nonempty, and valid RST markup"""

    plugin_m = ErtPluginManager(
        plugins=[subscript.hook_implementations.forward_model_steps]
    )

    steps = [step() for step in plugin_m.forward_model_steps]

    for step in steps:
        docs = step.documentation()
        assert docs is not None, f"{step.name} has no docs"
        assert docs.description, f"{step.name} has no description"
        assert not list(rstcheck_core.checker.check_source(docs.description)), (
            f"{step.name} has invalid RST syntax"
        )
        category = docs.category
        assert category != "other"
        assert category.split(".")[0] in ACCEPTED_STEP_CATEGORIES
