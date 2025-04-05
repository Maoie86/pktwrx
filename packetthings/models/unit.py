from typing import Optional
from pydantic import BaseModel, ConfigDict, model_validator, Field
from datetime import datetime, timezone


class UnitIn(BaseModel):
    name: str
    description: Optional[str]
    # created: datetime = Field(default_factory=lambda: datetime.now())
    # updated: datetime = Field(default_factory=lambda: datetime.now())

class Unit(UnitIn):
    model_config = ConfigDict(from_attributes=True, 
            validate_assignment=True, 
            arbitrary_types_allowed=True)
    id: int

class UnitUpdate(BaseModel):
    id: int
    name: str
    description: Optional[str]
    # updated: datetime = Field(default_factory=lambda: datetime.now())

class UnitList(BaseModel):
    data: list[UnitIn]
    # data: dict[str, list[UnitIn]]


class UnitDict(BaseModel):
    data: dict[str, list[UnitIn]]
    # data: dict[str, list[UnitIn]]


class UnitError(BaseModel):
    name: str
    description: Optional[str]
 
