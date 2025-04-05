import databases
import sqlalchemy
from typing import List

# from sqlalchemy import create_engine
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker

from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from packetthings.config import config
from packetthings.models.device import FullDevice

metadata = sqlalchemy.MetaData()

type_table = sqlalchemy.Table(
    "types",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String, unique=True),
    sqlalchemy.Column("description", sqlalchemy.String),
    sqlalchemy.Column("inactivity", sqlalchemy.Integer),
    sqlalchemy.Column("image", sqlalchemy.String),
    sqlalchemy.Column("created", sqlalchemy.DateTime),
    sqlalchemy.Column("updated", sqlalchemy.DateTime),
)


typedetail_table = sqlalchemy.Table(
    "typedetails",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String, unique=True),
    sqlalchemy.Column("description", sqlalchemy.String),
    sqlalchemy.Column("type_id", sqlalchemy.ForeignKey("types.id"), nullable=True),
    sqlalchemy.Column("measurement_id", sqlalchemy.ForeignKey("measurements.id"), nullable=True),
    sqlalchemy.Column("rank", sqlalchemy.Integer),
    sqlalchemy.Column("created", sqlalchemy.DateTime),
    sqlalchemy.Column("updated", sqlalchemy.DateTime),
)



location_table = sqlalchemy.Table(
    "locations",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String, unique=True),
    sqlalchemy.Column("description", sqlalchemy.String),
    sqlalchemy.Column("user_id", sqlalchemy.ForeignKey("users.id"), nullable=True),
    sqlalchemy.Column("location_id", sqlalchemy.ForeignKey("locations.id"), nullable=True),
    sqlalchemy.Column("image", sqlalchemy.String),
    sqlalchemy.Column("created", sqlalchemy.DateTime),
    sqlalchemy.Column("updated", sqlalchemy.DateTime),
)



role_table = sqlalchemy.Table(
    "roles",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String, unique=True),
    sqlalchemy.Column("description", sqlalchemy.String),
    sqlalchemy.Column("status", sqlalchemy.String),
    sqlalchemy.Column("created", sqlalchemy.DateTime),
    sqlalchemy.Column("updated", sqlalchemy.DateTime),
)



measurement_table = sqlalchemy.Table(
    "measurements",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String, unique=True),
    sqlalchemy.Column("description", sqlalchemy.String),
    sqlalchemy.Column("unit_id",  sqlalchemy.ForeignKey("units.id"), nullable=True),
    sqlalchemy.Column("created", sqlalchemy.DateTime),
    sqlalchemy.Column("updated", sqlalchemy.DateTime),
)


unit_table = sqlalchemy.Table(
    "units",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String, unique=True),
    sqlalchemy.Column("description", sqlalchemy.String),
    sqlalchemy.Column("created", sqlalchemy.DateTime),
    sqlalchemy.Column("updated", sqlalchemy.DateTime),
)



user_table = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("email", sqlalchemy.String, unique=True),
    sqlalchemy.Column("name", sqlalchemy.String),
    sqlalchemy.Column("password", sqlalchemy.String),
    sqlalchemy.Column("confirmed", sqlalchemy.Boolean, default=False),
    sqlalchemy.Column("source", sqlalchemy.String),
    sqlalchemy.Column("status", sqlalchemy.String),
    sqlalchemy.Column("role_id",  sqlalchemy.ForeignKey("roles.id"), nullable=True),
    sqlalchemy.Column("created", sqlalchemy.DateTime),
    sqlalchemy.Column("updated", sqlalchemy.DateTime),
)


device_table = sqlalchemy.Table(
    "devices",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String),
    sqlalchemy.Column("dev_eui", sqlalchemy.String, index=True, unique=True),
    sqlalchemy.Column("longitude", sqlalchemy.Float),
    sqlalchemy.Column("latitude", sqlalchemy.Float),
    # sqlalchemy.Column("group_id",  sqlalchemy.ForeignKey("locations.id"), nullable=True),
    sqlalchemy.Column("location_id",  sqlalchemy.ForeignKey("locations.id"), nullable=True),
    sqlalchemy.Column("type_id",  sqlalchemy.ForeignKey("types.id"), nullable=True),
    sqlalchemy.Column("description", sqlalchemy.String),
    sqlalchemy.Column("user_id", sqlalchemy.ForeignKey("users.id"), nullable=True),
    sqlalchemy.Column("domain", sqlalchemy.String),
    sqlalchemy.Column("created", sqlalchemy.DateTime),
    sqlalchemy.Column("updated", sqlalchemy.DateTime),
)


mydevice_table = sqlalchemy.Table(
    "mydevices",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("device_id", sqlalchemy.ForeignKey("devices.id")),
    sqlalchemy.Column("type_id", sqlalchemy.ForeignKey("types.id")),
    sqlalchemy.Column("user_id", sqlalchemy.ForeignKey("users.id")),
    sqlalchemy.Column("dev_eui", sqlalchemy.ForeignKey("devices.dev_eui")),
    sqlalchemy.Column("type_nm", sqlalchemy.String),
    sqlalchemy.Column("description", sqlalchemy.String),
    sqlalchemy.Column("created", sqlalchemy.DateTime),
    sqlalchemy.Column("updated", sqlalchemy.DateTime),
)


devsumm_table = sqlalchemy.Table(
    "device_summ",
    metadata,
    sqlalchemy.Column("dev_eui", sqlalchemy.String),
    sqlalchemy.Column("measurement", sqlalchemy.String),
    sqlalchemy.Column("yearmonth", sqlalchemy.Integer),
    sqlalchemy.Column("count", sqlalchemy.Integer),
)


# ********************************************************************

post_table = sqlalchemy.Table(
    "posts",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("body", sqlalchemy.String),
    sqlalchemy.Column("user_id", sqlalchemy.ForeignKey("users.id"), nullable=False),
)

comment_table = sqlalchemy.Table(
    "comments",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("body", sqlalchemy.String),
    sqlalchemy.Column("post_id", sqlalchemy.ForeignKey("posts.id"), nullable=False),
    sqlalchemy.Column("user_id", sqlalchemy.ForeignKey("users.id"), nullable=False),
)



like_table = sqlalchemy.Table(
    "likes",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("post_id", sqlalchemy.ForeignKey("posts.id"), nullable=False),
    sqlalchemy.Column("user_id", sqlalchemy.ForeignKey("users.id"), nullable=False)
)


engine = sqlalchemy.create_engine(
    config.DATABASE_URL
)

metadata.create_all(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

database = databases.Database(
    config.DATABASE_URL, force_rollback=config.DB_FORCE_ROLL_BACK
)

async def execute_raw_sql(db: Session, sql_query: str) -> List[FullDevice]:
    # Execute the raw SQL query
    result = db.execute(text(sql_query))
    
    # Fetch all rows from the result
    rows = result.fetchall()
    
    # Map the rows to Pydantic models
    users = []
    for row in rows:
        user = FullDevice(
            id=row.id,
            name=row.name,
            created=row.created
        )
        users.append(user)
    
    return users

