from typing import Optional
from pydantic import BaseModel, ConfigDict, model_validator, Field
from datetime import datetime, timezone


class MyDeviceIn(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    device_id: Optional[int] = 0
    user_id: int
    dev_eui: Optional[str] = ""
    type_id: int
    type_nm: str
    status: str
    description: Optional[str] = ""

class MyDevice(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    dev_eui: str
    type_id: int
    type_nm: str
    


