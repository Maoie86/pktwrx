import sys
import schedule
import time
import pathlib
import pytz
import logging
import calendar

from datetime import datetime, timedelta, date

from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import BatchStatement, SimpleStatement, ConsistencyLevel
from cassandra.auth import PlainTextAuthProvider
from cassandra.cqlengine import connection
from cassandra import ConsistencyLevel
from cassandra.policies import TokenAwarePolicy, DCAwareRoundRobinPolicy

from collections import defaultdict

from models import PacketTotals

node_ips = ['192.168.97.252']
cassandra_host = ['192.168.97.252'] 
cassandra_port = 9042           
keyspace = 'packets'     
data_table = 'device_data' 
latest_table = 'latest_data'
cassandra_user = "cassandra"
cassandra_pass = "FireWall12!@"

hourly_table = "hourly_data"
RUN_INTERVAL_SECONDS = 3600 * 24 * 7


def main():
    try:

        logging.basicConfig(
            filename='/home/mu/aggregator/logs/weekly.log',          # Log file name
            level=logging.INFO,          # Log level
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        logging.info("Weekly Aggregator Startup")

        # Default execution profile
        default_profile = ExecutionProfile(
            consistency_level=ConsistencyLevel.QUORUM,  # Example consistency level
            load_balancing_policy=TokenAwarePolicy(DCAwareRoundRobinPolicy(local_dc='datacenter1')),
            request_timeout=10.0                        # Timeout in seconds
        )

        # Custom execution profile for another use case
        custom_profile = ExecutionProfile(
            consistency_level=ConsistencyLevel.ONE,
            load_balancing_policy=TokenAwarePolicy(DCAwareRoundRobinPolicy(local_dc='datacenter1')),
            request_timeout=5.0
        )

        auth_provider = PlainTextAuthProvider(username=cassandra_user, password=cassandra_pass)
        #cluster = Cluster(cassandra_host,
        #            load_balancing_policy=TokenAwarePolicy(DCAwareRoundRobinPolicy(local_dc='datacenter1')),
        #            port=cassandra_port, 
        #            auth_provider=auth_provider, 
        #            protocol_version = 4)

        cluster = Cluster(
            contact_points=node_ips,   # Replace with your contact points
            auth_provider=auth_provider, 
            protocol_version = 4,
            execution_profiles={
                EXEC_PROFILE_DEFAULT: default_profile,  # Assign default profile
                'custom': custom_profile                # Assign a named custom profile
            }
        )

        
        session = cluster.connect()
        # print(session)
        logging.info("Connected to Cassandra")
        session.set_keyspace(keyspace)

        timezone = pytz.timezone('Asia/Singapore')

        ts = datetime.now()
        yesterday = ts - timedelta(days=1)           
        ts = yesterday

        
        week = ts.isocalendar()[1]
        day = ts.timetuple().tm_yday
        year = ts.year % 100
        wholeyear = ts.year
        month = ts.month
        yearday = year * 1000 + day
        yearmonth = year * 100 + month
        yearweek = year * 100 + week

        wkstart = ts - timedelta(days=ts.weekday())
        wkend = wkstart + timedelta(days=6)

        firstdow = wkstart.timetuple().tm_yday
        lastdow = wkend.timetuple().tm_yday
        fryearday = year * 1000 + firstdow
        toyearday = year * 1000 + lastdow
        logging.info("date: " + str(ts) + " - " + str(yearmonth) + " - " +  str(fryearday) + " - " + str(toyearday))

        sql_tx = "SELECT * FROM daily_data "
        sql_tx = sql_tx + " WHERE yearday >= " + str(fryearday)
        sql_tx = sql_tx + " AND yearday <= " + str(toyearday)
        sql_tx = sql_tx + " ALLOW FILTERING; "
        rows = session.execute(sql_tx)
        logging.info(sql_tx)
        # print(sql_tx)
        sorted_rows = sorted(rows, key=lambda x: (x.dev_eui, x.measurement), reverse=False)

        aggr_devs = defaultdict(str)
        aggr_measurement = defaultdict(str)
        aggr_sums = defaultdict(int)
        aggr_count = defaultdict(int)
        aggr_max = defaultdict(int)
        aggr_min = defaultdict(int)
        aggr_ave = defaultdict(int)

        cntr = 0
        dev_eui = ""
        # recs = 0
        for row in sorted_rows:
            if dev_eui != row.dev_eui or measurement != row.measurement:
                dev_eui = row.dev_eui
                measurement = row.measurement
                cntr += 1

                aggr_devs[cntr] = dev_eui
                aggr_measurement[cntr] = measurement
                aggr_sums[cntr] = 0
                aggr_count[cntr] = 0
                aggr_max[cntr] = 0
                aggr_min[cntr] = 0
                aggr_ave[cntr] = 0

        logging.info("rows: " + str(cntr))
        # print(cntr)
        cntr = 0
        dev_eui = ""
        measurement = ""
        # recs = 0
        for row in sorted_rows:
            if dev_eui != row.dev_eui or measurement != row.measurement:
                dev_eui = row.dev_eui
                measurement = row.measurement
                cntr += 1

            aggr_sums[cntr] += row.sum
            aggr_count[cntr] += row.count
            if aggr_max[cntr] < row.max:
                aggr_max[cntr] = row.max
            if aggr_count[cntr] > 0:
                aggr_ave[cntr] = aggr_sums[cntr] / aggr_count[cntr]
            if aggr_count[cntr] == 0:
                aggr_min[cntr] = aggr.min
            else:
                if aggr_min[cntr] > row.min:
                    aggr_min[cntr] = row.min

        sql_tx = """
            INSERT INTO weekly_data (dev_eui, measurement, min, max, ave, sum, count, yearweek)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
        for key in aggr_devs:
            cntr += 1
            session.execute(sql_tx, (aggr_devs[key], aggr_measurement[key], aggr_min[key], 
                            aggr_max[key], aggr_ave[key], aggr_sums[key], aggr_count[key],
                            yearweek))

        cluster.shutdown()

        logging.info("Inserted: " + str(cntr) + " records.. " )

    except Exception as e:
        # Code to handle the exception
        logging.error(f"An error occurred: {e}")
        

if __name__ == "__main__":
    print(__name__)
    main()


