from pydantic import BaseModel, ConfigDict
from typing import Optional, List
import datetime


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


