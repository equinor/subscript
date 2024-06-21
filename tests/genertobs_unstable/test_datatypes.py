from pathlib import Path
import re
import pytest
import subscript.genertobs_unstable._datatypes as dt
from subscript.genertobs_unstable.parse_config import read_yaml_config
from pydantic_core._pydantic_core import ValidationError


def test_elementmetadata():
    test_element = {"columns": {"md": {"unit": "m"}}}
    dt.ElementMetaData.model_validate(test_element)


def test_pluginarguments():
    test_element = {"billig": "pai", "dudels": "loo"}
    plugin = dt.PluginArguments.model_validate(test_element)
    for key, value in plugin.items():
        print(key, value)


def test_configroot_success(config_element, observations_input):

    config = [
        {
            "name": "this is something",
            "type": "summary",
            "observation": str(observations_input / "drogon_summary_input.txt"),
        },
        config_element,
    ]
    dumped_element = {
        "name": "This is something other",
        "type": dt.ObservationType.RFT,
        "observation": str(observations_input / "summary_gor.csv"),
        "active": True,
        "default_error": 5,
        "min_error": None,
        "max_error": None,
    }
    valid_config = dt.ObservationsConfig.model_validate(config)

    # assert valid_config.model_dump()[1] == dumped_element

    for i, observation in enumerate(valid_config):
        assert observation.name == config[i]["name"]

    assert valid_config[0].type == dt.ObservationType.SUMMARY
    assert valid_config[1].type == dt.ObservationType.RFT


def test_rftconfigelement(observations_input):
    config_element = {
        "name": "This is something other",
        "type": "rft",
        "observation": str(observations_input / "summary_gor.csv"),
    }
    valid_config = dt.RftConfigElement.model_validate(config_element)
    print(valid_config)


def test_validate_observation_path(config_element):
    config_element["observation"] = "nopath"
    with pytest.raises(OSError) as excinfo:
        dt.ConfigElement.model_validate(config_element)
    except_mess = str(excinfo.value)
    print(except_mess)
    assert except_mess == "Input observation file nopath, does not exist"


@pytest.mark.parametrize(
    "default_error,exception",
    [
        ("2050%", ValidationError),
        ("2.34", ValueError),
        ("banana", ValidationError),
        (-1, ValueError),
    ],
)
def test_validate_default_error(config_element, default_error, exception):
    config_element["default_error"] = default_error
    with pytest.raises(exception) as excinfo:
        dt.ConfigElement.model_validate(config_element)

    except_mess = str(excinfo.value)
    print(except_mess)


# # assert except_mess == message


def test_check_error_limits():
    mess = "default_error specified as an absolute number, doesn't make sense to set a lower limit (1)"
    with pytest.raises(ValueError) as excinfo:
        dt.check_error_limits(5, 1, 6)
    except_mess = str(excinfo.value)
    assert except_mess == mess
