from uuid import uuid1
from typing import Optional
from pydantic import BaseModel, ConfigDict, model_validator, Field
from datetime import datetime, timezone


class TypeDetailIn(BaseModel):
    name: str
    description: Optional[str] = None
    type_id: int = 0
    measurement_id: int = 0
    rank: int = 0
    # created: datetime = Field(default_factory=lambda: datetime.now())
    # updated: datetime = Field(default_factory=lambda: datetime.now())


class TypeDetail(TypeDetailIn):
    model_config = ConfigDict(from_attributes=True, validate_assignment=True, arbitrary_types_allowed=True)
    id: int


class TypeDetailUpdate(BaseModel):
    id: int
    name: str
    description: Optional[str]
    measurement_id: int = 0
    rank: int = 0
    # updated: datetime = Field(default_factory=lambda: datetime.now())


