import os
import yaml
import pytest
from subscript.genertobs_unstable import _config as conf
from pandas import DataFrame


def test_read_yaml_config(yaml_config_file):
    """Test function read_yaml_config"""
    config = conf.read_yaml_config(yaml_config_file)
    assert isinstance(config, list)
    len_config = len(config)
    assert len_config > 0
    print("Length of configuration:", len_config)


VALID_FORMATS = [
    "depth",
    "facies_thickness",
    "fault_lines",
    "field_outline",
    "field_region",
    "fluid_contact",
    "inplace_volumes",
    "khproduct",
    "lift_curves",
    "parameters",
    "pinchout",
    "property",
    "pvt",
    "regions",
    "relperm",
    "rft",
    "seismic",
    "subcrop",
    "thickness",
    "time",
    "timeseries",
    "transmissibilities",
    "velocity",
    "volumes",
    "volumetrics",
    "wellpicks",
]


@pytest.mark.parametrize(
    "invalid_config,exception,error_mess",
    [
        (
            {"type": "timeseries"},
            KeyError,
            "Key name not in obs number 0",
        ),
        (
            {"name": "banana", "type": "timeseries"},
            AssertionError,
            "banana, does not contain all of ['name', 'observation', 'type'], only ['name', 'type']",
        ),
        (
            {"name": "banana", "type": "banana", "observation": "dummy.csv"},
            AssertionError,
            f"banana not in {VALID_FORMATS}",
        ),
        (
            {
                "name": "banana",
                "type": "rft",
                "observation": "dummy.csv",
                "hulahoop": "kefir",
            },
            AssertionError,
            "{'hulahoop'} are found in config, these are not allowed",
        ),
    ],
)
def test_validate_config_exceptions(invalid_config, exception, error_mess):
    """Test function validate_config"""
    config = [invalid_config]
    with pytest.raises(exception) as exception_info:
        conf.validate_config(config)

    extracted_mess = str(exception_info.value.args[0])
    print(len(extracted_mess))
    print(len(error_mess))
    print(error_mess)
    print(extracted_mess)
    assert extracted_mess == error_mess


def test_generate_data_from_config(yaml_config, drogon_project):
    ert_path = drogon_project / "ert/model"
    os.chdir(ert_path)
    data, summary_to_fmuobs = conf.generate_data_from_config(
        yaml_config, ert_path  #  / "../input/observations"
    )
    assert isinstance(data, list), f"Data should be list, but is {type(data)}"
    assert isinstance(
        summary_to_fmuobs, DataFrame
    ), f"summary should be dataframe but is {type(summary_to_fmuobs)}"
    print("\n\n", data)
