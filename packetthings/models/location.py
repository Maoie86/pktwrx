from typing import Optional, Union
from pydantic import BaseModel, ConfigDict, model_validator, Field
from datetime import datetime, timezone


class LocationIn(BaseModel):
    name: str
    description: Optional[str]
    user_id: int = 0
    location_id: Union[int, None] = None
    image: Optional[str] = None
    # created: datetime = Field(default_factory=lambda: datetime.now())
    # updated: datetime = Field(default_factory=lambda: datetime.now())

class Location(LocationIn):
    model_config = ConfigDict(from_attributes=True, 
            validate_assignment=True, 
            arbitrary_types_allowed=True
        )
    id: int

class LocationUpdate(BaseModel):
    id: int
    name: str
    description: Optional[str]
    location_id: int = 0
    # updated: datetime = Field(default_factory=lambda: datetime.now())


