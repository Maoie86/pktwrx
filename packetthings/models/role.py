from typing import Optional
from pydantic import BaseModel, ConfigDict, model_validator, Field
from datetime import datetime, timezone


class RoleIn(BaseModel):
    name: str
    description: Optional[str]
    status: Optional[str]
    # created: datetime = Field(default_factory=lambda: datetime.now())
    # updated: datetime = Field(default_factory=lambda: datetime.now())

class Role(RoleIn):
    model_config = ConfigDict(from_attributes=True, validate_assignment=True, arbitrary_types_allowed=True)
    id: int

class RoleUpdate(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: Optional[str]
    # updated: datetime = Field(default_factory=lambda: datetime.now())


