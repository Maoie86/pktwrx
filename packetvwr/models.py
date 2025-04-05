from pydantic import BaseModel, ConfigDict
from typing import Optional, List
import datetime

class RawJson(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    device_name: str
    yyyymmdd: int
    ts: datetime.datetime
    app_name: str
    tts_json: str
    actility_json: str


class RJQuery(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    app_name: str
    yyyymmdd: str
    frtime: Optional[str] = None
    totime: Optional[str] = None
    device_name: Optional[str] = None

