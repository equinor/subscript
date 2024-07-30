"""Pydantic models for genertobs"""

from enum import Enum
from pathlib import Path
import logging
from typing import List, Union, Dict
from pydantic import (
    BaseModel,
    Field,
    RootModel,
    ConfigDict,
    model_validator,
    field_validator,
    computed_field,
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
    logger.debug("Checking this string %s", error)
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


class RftType(Enum):
    """Valid Rft types

    Args:
        Enum (Enum): Enumerator
    """

    PRESSURE = "pressure"
    SWAT = "saturation_water"
    SOIL = "saturation_oil"
    SGAS = "saturation_gas"


class ElementMetaData(BaseModel):
    """Pattern for Metadata element for observations

    Args:
        BaseModel (BaseModel): pydantic BaseModel
    """

    subtype: RftType = Field(
        default=RftType.PRESSURE,
        description=f"Type of rft observation, can be any of {RftType.__members__}",
    )

    @computed_field
    @property
    def columns(self) -> Dict[str, Dict[str, str]]:
        """Define columns to expect

        Returns:
            Dict[str, Dict[str, str]]: the expected column with units
        """
        if self.subtype == RftType.PRESSURE:
            out_dict = {self.subtype: {"unit:bar"}}
        else:
            out_dict = {self.subtype: {"unit:fraction"}}
        return out_dict


class PluginArguments(RootModel):
    """Plugin arguments for config element"""

    root: Dict[str, str]

    def __getitem__(self, item):
        return self.root[item]

    def keys(self):
        """Fake .keys method

        Returns:
            dict.keys: the root dict.keys()
        """
        # TODO: check if this is the only way
        return self.root.keys()

    def items(self):
        """Fake .items method

        Returns:
            dict.items: the root dict.items()
        """
        # TODO: check if this is the only way
        return self.root.items()


class ConfigElement(BaseModel):
    """Element in a config file"""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=5, description="Name of observation")
    type: ObservationType = Field(description="Type of observation")
    observation: str = Field(
        description="path to file containing observations, this can be any csv"
        " like file,\n i.e textfile or spreadsheet",
    )
    active: bool = Field(
        default=True,
        description="If the observation element shall be used in\n "
        "generation of ert observations",
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
                )  #  pylint: disable=raise-missing-from
        return error

    @model_validator(mode="after")
    def check_when_default_is_number(self):
        """Check

        Returns:
            Self: self
        """
        check_error_limits(self.default_error, self.min_error, self.max_error)
        return self


class RftConfigElement(ConfigElement):
    """Config element with extras for rft

    Args:
        ConfigElement (pydantic model): observation config element
    """

    plugin_arguments: PluginArguments = Field(default=None)
    metadata: ElementMetaData = Field(
        default={"subtype": RftType.PRESSURE, "columns": {"pressure": {"unit:bar"}}},
        description="Metadata describing the type",
    )

    alias_file: str = Field(default=None, description="Name of file with aliases")

    # @field_validator("type")
    # @classmethod
    # def validate_of_rft_type(cls, observation_type: ObservationType):
    #     """validate that type is rft

    #     Args:
    #         observation_type (ObservationType): the type of observation

    #     Raises:
    #         TypeError: if type is not RFT

    #     Returns:
    #         ObservationType: type of observations
    #     """
    #     if observation_type != ObservationType.RFT:
    #         raise TypeError(f"This is not rft type, but {observation_type}")
    #     return observation_type


class ObservationsConfig(RootModel):
    """Root model for config file

    Args:
        RootModel (Rootmodel): pydantic root model
    """

    root: List[Union[RftConfigElement, RftConfigElement]] = Field(
        description="What type of observation",
    )

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def __len__(self):
        return len(self.root)
