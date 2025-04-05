# db_utils.py

import psycopg2
from psycopg2 import sql
from packetthings.config import config


def get_db_connection():
    return psycopg2.connect(config.DATABASE_URL)


