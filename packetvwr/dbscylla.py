import pathlib
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.cqlengine import connection
from cassandra import ConsistencyLevel

# from packetthings.config import config

# ASTRADB_CONNECT_BUNDLE = BASE_DIR / "unencrypted" / "astradb_connect.zip"
# ASTRADB_CLIENT_ID = settings.db_client_id
# ASTRADB_CLIENT_SECRET = settings.db_client_secret

node_ips = ['127.0.0.1']

def get_session():
    # auth_provider = PlainTextAuthProvider(username=config.SCYLLA_USER, password=config.SCYLLA_PASSWD)
    auth_provider = PlainTextAuthProvider(username='cassandra', password='cassandra')
    cluster = Cluster(node_ips, auth_provider=auth_provider)
    session = cluster.connect('packets')
    connection.register_connection(str(session), session=session)
    connection.set_default_connection(str(session))
    return session



