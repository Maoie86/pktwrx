from sqlalchemy import Table, Column, Integer, String, Boolean, Float, Text
from database import dbmetadata
from pydantic import BaseModel

gwdata = Table(
    "gateways",
    dbmetadata,
    Column("lrr_uuid", String, primary_key=True),
    Column("lrr_id", String),
    Column("name", String),
    Column("lon", String),
    Column("lat", String),
    Column("tags", Integer),
    Column("monitored", Boolean, default=False)
)

tagsdata = Table(
    "gateway_tags",
    dbmetadata,
    Column("lrr_id", String, primary_key=True),
    Column("tag", String)
)


class GWSUpdate(BaseModel):
    lrr_uuid: str

class GetTags(BaseModel):
    lrr_id: str


class AddTag(BaseModel):
    tag: str
    lrr_id: str


