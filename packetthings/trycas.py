from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra import ConsistencyLevel
import ssl

node_ips = ['127.0.0.1']
ap = PlainTextAuthProvider(username="packetworx", password="FireWall12!@")

with Cluster(node_ips, port=9042, auth_provider=ap) as cluster:
    with cluster.connect('packets') as session:
        # get cassandra version
        # row = session.execute("SELECT release_version FROM system.local").one()

        # keyspace selection or change
        # session.set_keyspace('packets')
        # or you can do this instead
        # session.execute('USE packets')

        # create table in current keyspace
        # session.execute("CREATE table emp(id int PRIMARY KEY, name text, email text, salray varint, city text)")

        # create keyspace
        # session.execute("CREATE KEYSPACE IF NOT EXISTS packets WITH REPLICATION = {'class':'SimpleStrategy'}")

        # list keyspaces
        # row = session.execute("SELECT * FROM system_schema.keyspaces")

        # insert into table 
        # sql = "INSERT INTO emp(id, name, city, salray, email) VALUES(2, 'John Q', 'QC', 99, 'test1@example.com')"
        # session.execute(sql)

        #select from table
        row = session.execute("SELECT * FROM emp")
        print(row.current_rows)
 

