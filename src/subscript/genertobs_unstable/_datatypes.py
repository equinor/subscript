from enum import Enum
from pathlib import Path
from typing import List, Union
from pydantic import (
    BaseModel,
    Field,
    RootModel,
    ConfigDict,
    field_validator,
)


def is_number(tocheck):
    """Check that variable can be converted to number

    Args:
        tocheck (something): what shall be checked

    Returns:
        bool: check passed or not
    """
    try:
        float(tocheck)
        return True
    except TypeError:
        return False


def is_percent_range(string):
    """Check if string ending with % is between  0 and 100

    Args:
        string (str): the string to check

    Returns:
        bool: True if number is in the range
    """
    number = float(string.replace("%", ""))
    if (number > 0) and (number < 100):
        return True
    else:
        return False


def is_string_convertible_2_percent(error):
    """Check string

    Args:
        error (str): string to check

    Raises:
        ValueError: if string does not end with a percent sign
        TypeError: if string cannot be converted to a number
        ValueError: if the number ends with %, but is not between 0 and 100
    """
    if not is_number(error[:-1]):
        raise TypeError(f"This: {error} is not convertible to a number")

    if not error.endswith("%"):
        raise ValueError(
            f"When default_error ({error}) given as string it must end with a % sign"
        )

    if not is_percent_range(error):
        raise ValueError(f"The number {error} is not in the valid range 0-100")


class ObservationType(Enum):
    """The valid datatypes in a config file

    Args:
        Enum (Enum): Enumerator
    """

    SUMMARY = "summary"
    RFT = "rft"


class ConfigElement(BaseModel):
    """Element in a config file"""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=5, description="Name of observation")
    type: ObservationType = Field(description="Type of observation")
    observation: str = Field(
        description="path to file containing observations, this can be any csv"
        " like file,\n i.e textfile or spreadsheet",
    )
    default_error: Union[str, float, int] = Field(
        default=None,
        description="Optional argument. Error to be used\n. Used only when"
        "no error column present or where error column is empty."
        " Can be supplied as any number, and even with a percentage sign",
    )

    min_error: Union[int, float] = Field(
        default=None,
        description="Optional argument. Minimum error, only allowed "
        "when default_error is in percent",
    )
    max_error: Union[int, float] = Field(
        default=None,
        description="Optional argument. Maximum error, only allowed "
        "when default_error is in percent",
    )

    @field_validator("observation")
    @classmethod
    def validate_path_exists(cls, observation_path: str):
        """Check that observation file exists

        Args:
            observation_path (str): the path to check

        Raises:
            OSError: if observation_path does not exist
        """
        if not Path(observation_path).exists():
            raise OSError(f"Input observation file {observation_path}, does not exist")

    @field_validator("default_error")
    @classmethod
    def validate_default_error(cls, error: Union[str, int, float]):
        """Check that if error is string, and if so then check that it is in %

        Args:
            observation_path (str): the path to check

        Raises:
            OSError: if observation_path does not exist
        """
        try:
            is_string_convertible_2_percent(error)
        except AttributeError:
            pass


class ObservationsConfig(RootModel):
    """Root model for config file

    Args:
        RootModel (Rootmodel): pydantic root model
    """

    root: List[ConfigElement]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]
