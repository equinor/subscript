from enum import Enum
from typing import List, Union
from pydantic import (
    BaseModel,
    Field,
    RootModel,
    ConfigDict,
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
        description="path to file containing observations",
    )
    default_error: Union[str, float, int] = Field(
        default=None,
        description="Error to be used\n. Used only when"
        + "no error column present or where error column is empty",
    )

    min_error: Union[int, float] = Field(
        default=None,
        description="minimum error, only allowed when default_error is in percent",
    )
    max_error: Union[int, float] = Field(
        default=None,
        description="maximum error, only allowed when default_error is in percent",
    )


class ObservationsConfig(RootModel):
    """Root model for config file

    Args:
        RootModel (Rootmodel): pydantic root model
    """

    root: List[ConfigElement]
