from pydantic import BaseModel, ConfigDict
from typing import Optional, List
import datetime

class RawJson(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    device_name: str
    yymmdd: int
    ts: datetime.datetime
    app_name: str
    raw_json: str



