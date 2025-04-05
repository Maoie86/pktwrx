from databases import Database
from sqlalchemy import create_engine, MetaData

DATABASE_URL = "postgresql://noc_user:Lkh6qa6YN5YS9aHqkjD@127.0.0.1/noc"


connection_params = {
            'dbname': 'noc',
            'user': 'noc_user',
            'password': 'Lkh6qa6YN5YS9aHqkjD',
            'host': '127.0.0.1',
            'port': '5432'  # usually 5432 for PostgreSQL
}



dbdatabase = Database(DATABASE_URL)
dbmetadata = MetaData()
dbengine = create_engine(DATABASE_URL)


