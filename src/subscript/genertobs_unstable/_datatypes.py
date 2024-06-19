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
