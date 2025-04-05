from databases import Database
from sqlalchemy import create_engine, MetaData

DATABASE_URL = "postgresql://postgres:FireWall12%21%40@127.0.0.1/tts"

dbdatabase = Database(DATABASE_URL)
dbmetadata = MetaData()
dbengine = create_engine(DATABASE_URL)


