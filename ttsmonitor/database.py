from databases import Database
from sqlalchemy import create_engine, MetaData

DATABASE_URL = "postgresql://gwmonitor:yu4Tp3SXv1RhwbT1wrBs@172.16.23.89/gateway_monitoring"

dbdatabase = Database(DATABASE_URL)
dbmetadata = MetaData()
dbengine = create_engine(DATABASE_URL)





