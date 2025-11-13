import pytest
import rstcheck_core.checker
from ert.config import ConfigValidationError, ErtConfig
from ert.plugins import ErtPluginManager, ErtRuntimePlugins

import subscript.hook_implementations.forward_model_steps as fm_steps

DEFAULT_CONFIG = """
NUM_REALIZATIONS 1

FORWARD_MODEL {}({})
"""

EXPECTED_STEPS = [
    "CASEGEN_UPCARS",
    "CHECK_SWATINIT",
    "CREATE_DATE_FILES",
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
    "PRTVOL2CSV",
    "SUNSCH",
    "WELLTEST_DPDS",
]

# Avoid category inflation. Add to this list when it makes sense:
ACCEPTED_STEP_CATEGORIES = ["modelling", "utility"]


def test_hooks_are_installed_in_erts_plugin_manager():
    """Test that we have the correct set of steps installed,
    nothing more, nothing less"""
    plugin_m = ErtPluginManager(plugins=[fm_steps])

    available_fm_steps = [step().name for step in plugin_m.forward_model_steps]
    assert set(EXPECTED_STEPS) == set(available_fm_steps)


@pytest.mark.integration
def test_executables_exists():
    """Test executables requested exist in $PATH"""
    plugin_m = ErtPluginManager(plugins=[fm_steps])

    steps = [step() for step in plugin_m.forward_model_steps]
    for step in steps:
        assert step.executable is not None


def test_hook_implementations_docs():
    """For each installed job, we require the associated
    description string to be nonempty, and valid RST markup"""

    plugin_m = ErtPluginManager(plugins=[fm_steps])

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


@pytest.mark.parametrize(
    "call_content, expected_failure",
    [
        pytest.param(
            "<GLOBVARFILE>=myfile.yml, <SINGLEDATES>=MY_DATE, <DIFFDATES>=MY_DATE",
            "<SINGLEDATES> and <DIFFDATES> cannot have identical values",
            id="identical_dates",
        ),
        pytest.param(
            "<GLOBVARFILE>=myfile.yml",
            "Provide at least one of <SINGLEDATES> or <DIFFDATES>",
            id="no_date_placeholders",
        ),
        pytest.param(
            "<SINGLEDATES>=MY_DATE, <DIFFDATES>=OTHER_DATE",
            "Required keyword <GLOBVARFILE> not found for forward model step"
            " CREATE_DATE_FILES",
            id="missing_globvarfile",
        ),
        pytest.param(
            "",
            "Required keyword <GLOBVARFILE> not found for forward model step"
            " CREATE_DATE_FILES",
            id="no_arguments",
        ),
    ],
)
def test_parameter_validation_create_date_files(
    tmp_path, monkeypatch, call_content, expected_failure
):
    monkeypatch.chdir(tmp_path)
    config = DEFAULT_CONFIG.format("CREATE_DATE_FILES", call_content)
    with open("config.ert", "w", encoding="utf-8") as file:
        file.write(config)

    with pytest.raises(ConfigValidationError, match=expected_failure):
        ErtConfig.with_plugins(
            ErtRuntimePlugins(
                installed_forward_model_steps={
                    "CREATE_DATE_FILES": fm_steps.CreateDateFiles()
                }
            )
        ).from_file("config.ert")
