from pathlib import Path
import re
import pytest
import subscript.genertobs_unstable._datatypes as dt
from pydantic_core._pydantic_core import ValidationError


OBSERVATIONS_INPUT = Path(__file__).parent / "data/drogon/ert/input/observations/"


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


def test_configroot_success():
    second_element = {
        "name": "This is something other",
        "type": "rft",
        "observation": str(OBSERVATIONS_INPUT / "summary_gor.csv"),
        "default_error": 5,
        "min_error": 3,
        "max_error": 6,
    }
    config = [
        {
            "name": "this is something",
            "type": "summary",
            "observation": str(OBSERVATIONS_INPUT / "drogon_summary_input.txt"),
        },
        second_element,
    ]
    valid_config = dt.ObservationsConfig.model_validate(config)

    for i, observation in enumerate(valid_config):
        assert observation.name == config[i]["name"]

    print(valid_config[1])
