from sqlalchemy import Table, Column, Integer, String, Boolean, Float, Text, DateTime
from database import dbmetadata
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base



from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class cam_data(Base):
    __tablename__ = "cam_data"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_tx = Column(String(200), nullable=False)
    device_tx = Column(String(200), nullable=False)
    event_tx = Column(String(200), nullable=False)
    data_ts = Column(DateTime, default=func.now())
    line_no = Column(Integer)
    in_no = Column(Integer)
    out_no = Column(Integer)
    capacity_no = Column(Integer)
    sum_no = Column(Integer)

class cam_summ(Base):
    __tablename__ = "cam_summ"
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_tx = Column(String(200), nullable=False)
    location_tx = Column(String(200), nullable=False)
    count_no = Column(Integer)



#cam_data = Table(
#    "cam_data",
#    dbmetadata,
#    Column("id", Integer, primary_key=True, autoincrement=True)    
#    Column("tenant_tx", String),
#    Column("event_tx", String),
#    Column("device_tx", String),
#    Column("data_ts", DateTime),
#    Column("line_no", Integer)
#    Column("in_no", Integer)
#    Column("out_no", Integer)
#    Column("capacity_no", Integer)
#    Column("sum_no", Integer)
#)



