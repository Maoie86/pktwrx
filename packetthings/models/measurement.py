from typing import Optional
from pydantic import BaseModel, ConfigDict, model_validator, Field
from datetime import datetime, timezone


class MeasurementIn(BaseModel):
    name: str
    description: Optional[str]
    unit_id: int
    #vcreated: datetime = Field(default_factory=lambda: datetime.now())
    # updated: datetime = Field(default_factory=lambda: datetime.now())

class Measurement(MeasurementIn):
    model_config = ConfigDict(from_attributes=True, validate_assignment=True, arbitrary_types_allowed=True)
    id: int

class MeasurementUpdate(BaseModel):
    id: int
    name: str
    unit_id: int
    description: Optional[str]
    # updated: datetime = Field(default_factory=lambda: datetime.now())

class MeasurementFull(BaseModel):
    id: int
    name: str
    description: Optional[str]
    unit_id: int
    unit_nm: str


