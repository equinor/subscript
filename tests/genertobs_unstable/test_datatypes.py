from pathlib import Path
import re
import pytest
import subscript.genertobs_unstable._datatypes as dt
from pydantic_core._pydantic_core import ValidationError


@pytest.mark.parametrize(
    "input_element,nrerr,class_type",
    [
        ({"name": "du"}, 1, "list"),
        (["name", "du"], 2, "dictionary"),
        ("tut", 1, "list"),
    ],
)
def test_configroot_failure(input_element, nrerr, class_type):

    with pytest.raises(ValidationError) as excinfo:
        dt.ObservationsConfig(input_element)
    except_mess = str(excinfo.value)
    print(except_mess)
    validation_errors = re.compile(r"Input should be a valid\s+([\w]+)")
    errors = validation_errors.findall(except_mess)
    assert len(errors) == nrerr
    assert errors[0] == class_type


def test_configroot_success(config_element, observations_input):

    config = [
        {
            "name": "this is something",
            "type": "summary",
            "observation": str(observations_input / "drogon_summary_input.txt"),
        },
        config_element,
    ]
    valid_config = dt.ObservationsConfig.model_validate(config)

    for i, observation in enumerate(valid_config):
        assert observation.name == config[i]["name"]

    print(valid_config[1])


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
