from enum import Enum
from pathlib import Path
import logging
from typing import List, Union
from pydantic import (
    BaseModel,
    Field,
    RootModel,
    ConfigDict,
    model_validator,
    field_validator,
)
import warnings


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
    logger = logging.getLogger(__file__ + ".is_percent_range")
    logger.debug("Input is %s", string)
    number = float(string.replace("%", ""))
    if 0 < number < 100:
        return True

    if number > 50:
        warnings.warn(
            "It seems weird to have an error of more than 50%"
            f" ({number}, is this correct?)"
        )
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
    logger = logging.getLogger(__file__ + ".is_string_convertible_2_percent")
    try:
        if not is_number(error[:-1]):
            raise TypeError(f"This: {error} is not convertible to a number")
    except TypeError:
        pass

    if not error.endswith("%"):
        raise ValueError(
            f"When default_error ({error}) given as string it must end with a % sign"
        )

    if not is_percent_range(error):
        raise ValueError(f"The number {error} is not in the valid range 0-100")


def check_error_limits(error, err_min, err_max):
    """Check error limits

    Args:
        error (Union[str,int,float]): the error to check against
        err_min (Union[int,float,None]): the lower limit
        err_max (Union[int,float,None]): the higher limit


    Raises:
        ValueError: if err_min is not None when error is not in percent
        ValueError: if err_max is not None when error is not in percent
        ValueError: if err_min >= max
    """
    logger = logging.getLogger(__file__ + ".check_error_limits")
    logger.debug("Checking with error: %s, and limits %s-%s", error, err_min, err_max)
    if isinstance(error, (float, int)):
        if err_min is not None:
            raise ValueError(
                "default_error specified as an absolute number,"
                f" doesn't make sense to set a lower limit ({err_min})"
            )
        if err_max is not None:
            raise ValueError(
                "default_error specified as an absolute number,"
                f" doesn't make sense to set a higher limit ({err_max})"
            )
    else:
        if err_min is not None and err_max is not None:
            if err_min >= err_max:
                raise ValueError(
                    f"When using limits, the minimum must be lower than the maximum\n"
                    f"{err_min}-{err_max}"
                )


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
        return observation_path

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
            if error < 0:
                raise ValueError(
                    f"default error cannot be negative {error}"
                )  # pylint: ignore
        return error

    @model_validator(mode="after")
    def check_when_default_is_number(self):
        """Check

        Returns:
            Self: self
        """
        check_error_limits(self.default_error, self.min_error, self.max_error)
        return self


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
