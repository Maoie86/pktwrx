from pydantic import BaseModel, ConfigDict
from typing import Optional, List
import datetime


class Packet(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    dev_eui: str
    measurement: str
    yearmonth: int
    ts: datetime.datetime
    value: float
    source_application_id: str


class ThinPacket(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ts: datetime.datetime
    value: float


class PacketQuery(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    yearmonth: int
    dev_eui: str
    measurement: str
    aggregate: Optional[str] = ""


class PacketQueryDates(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    yearmonth: int
    dev_eui: str
    measurement: str
    aggregate: Optional[str] = ""
    fromdate: datetime.datetime
    todate: datetime.datetime


class LatestPacket(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    dev_eui: str
    measurement: str
    ts: datetime.datetime
    value: float
    source_application_id: str


class LatestPacketUnit(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    dev_eui: str
    measurement: str
    unit: str
    ts: datetime.datetime
    value: float
    source_application_id: str



class PacketTotals(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    seq: int
    name: str
    total: float
    max: float
    min: float
    aveint: int
    ave: float
    count: int


class LatestPacketUnit(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    dev_eui: str
    measurement: str
    unit: str
    ts: datetime.datetime
    value: float
    source_application_id: str


