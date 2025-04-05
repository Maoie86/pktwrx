from uuid import uuid1
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, model_validator, Field
from datetime import datetime, timezone


class TypeIn(BaseModel):
    name: str
    description: Optional[str] = None
    image: Optional[str] = None
    inactivity: int
    # created: datetime = Field(default_factory=lambda: datetime.now())
    # updated: datetime = Field(default_factory=lambda: datetime.now())


class Type(TypeIn):
    model_config = ConfigDict(from_attributes=True, validate_assignment=True, arbitrary_types_allowed=True)
    id: int


class TypeUpdate(BaseModel):
    id: int
    name: str
    inactivity: int
    description: Optional[str]
    # updated: datetime = Field(default_factory=lambda: datetime.now())


class TypeDetails(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str]
    measurement_id: int
    measurement_nm: Optional[str] = ""


class FullType(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    inactivity: int
    description: str
    image: Optional[str] = None
    typedtls: List[TypeDetails] = []

