from sqlalchemy import Table, Column, Integer, String, Boolean, Float, Text
from pydantic import BaseModel
from database import dbmetadata


gwdata = Table(
    "gateway_data",
    dbmetadata,
    Column("id", String, primary_key=True),
    Column("name", String),
    Column("longitude", Float),
    Column("latitude", Float),
    Column("tags", Integer),
    Column("monitoring_on", Boolean, default=False)
)


tagsdata = Table(
    "gateway_tags",
    dbmetadata,
    Column("gateway_id", String),
    Column("tag", String)
)


class GWSUpdate(BaseModel):
    id: str

