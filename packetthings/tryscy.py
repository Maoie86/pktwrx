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
        #session.execute("CREATE table device_data(id int PRIMARY KEY, ts timestamp, dev_eui varchar, measurement varchar, value decimal, source_application_id varchar)")

        # create keyspace
        # session.execute("CREATE KEYSPACE IF NOT EXISTS packets WITH REPLICATION={'class':'SimpleStrategy','replication_factor':2}")
        # session.execute('USE packets')

        # list keyspaces
        # row = session.execute("SELECT * FROM system_schema.keyspaces")

        # insert into table 
        sql = "INSERT INTO latest_data(id, ts, dev_eui, measurement, value, source_application_id, yearmonth) VALUES(13, '2024-02-04 04:05+0000', 'D1234567', 'temp', 8.88, 'test1@example.com', '2402')"
        session.execute(sql)
        sql = "INSERT INTO latest_data(id, ts, dev_eui, measurement, value, source_application_id, yearmonth) VALUES(14, '2024-03-04 04:05+0000', 'D1234567', 'temp', 9.88, 'test1@example.com', '2403')"
        session.execute(sql)
        sql = "INSERT INTO latest_data(id, ts, dev_eui, measurement, value, source_application_id, yearmonth) VALUES(15, '2024-04-04 04:05+0000', 'D1234567', 'temp', 1.88, 'test2@example.com', '2404')"
        session.execute(sql)
        sql = "INSERT INTO latest_data(id, ts, dev_eui, measurement, value, source_application_id, yearmonth) VALUES(16, '2024-05-04 04:05+0000', 'D1234567', 'temp', 2.88, 'test2@example.com', '2405')"
        session.execute(sql)
        sql = "INSERT INTO latest_data(id, ts, dev_eui, measurement, value, source_application_id, yearmonth) VALUES(17, '2024-05-07 04:05+0000', 'D1234568', 'temp', 1.88, 'test2@example.com', '2405')"
        session.execute(sql)
        sql = "INSERT INTO latest_data(id, ts, dev_eui, measurement, value, source_application_id, yearmonth) VALUES(18, '2024-06-02 04:05+0000', 'D1234568', 'temp', 2.88, 'test2@example.com', '2406')"
        session.execute(sql)


        #select from table
        row = session.execute("SELECT * FROM latest_data")
        print(row.current_rows)
 

