from typing import Optional, List
from pydantic import BaseModel, ConfigDict, model_validator, Field
from datetime import datetime, timezone


class DeviceIn(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    dev_eui: str
    longitude: float
    latitude: float
    location_id: int
    type_id: int
    description: Optional[str] = None
    user_id: int
    domain: str
    # created: datetime = Field(default_factory=lambda: datetime.now())
    # updated: datetime = Field(default_factory=lambda: datetime.now())


class Device(DeviceIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    # token: str


class DeviceOut(DeviceIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    token: str


class LatLong(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    latitude: float
    longitude: float


class DevEUI(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    dev_eui: str


class DeviceReg(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    dev_eui: str
    longitude: Optional[float] = 0
    latitude: Optional[float] = 0
    location_id: Optional[int] = 0
    description: Optional[str] = None


class DeviceRegToken(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    dev_eui: str
    longitude: float
    latitude: float
    location_id: int
    description: str
    devtoken: str


class TypeDetails(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str]
    measurement_id: int 
    measurement_nm: Optional[str] = ""



class FullDevice(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    dev_eui: str
    longitude: float
    latitude: float
    location_id: int
    location_nm: str
    group_id: int
    group_nm: str
    type_id: int
    type_nm: str
    description: str
    user_id: int
    user_nm: str
    domain: str
    status: str
    lastactive: str
    typedtls: List[TypeDetails] = []


class DeviceUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    dev_eui: str
    longitude: float
    latitude: float
    location_id: int
    domain: str
    type_id: int
    user_id: int
    description: str


class DeviceToken(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    dev_eui: str
    token: str


class DeviceSumm(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    dev_eui: str
    measurement: str
    count: int
    yearmonth: int



class DeviceDistance(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    dev_eui: str
    longitude: float
    latitude: float
    location_id: int
    type_id: int
    description: str
    user_id: int
    domain: str


