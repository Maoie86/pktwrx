import sys
import schedule
import time
import pathlib
import pytz
from datetime import datetime

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import BatchStatement, SimpleStatement, ConsistencyLevel
from cassandra.auth import PlainTextAuthProvider
from cassandra.cqlengine import connection
from cassandra import ConsistencyLevel
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
RUN_INTERVAL_SECONDS = 3600


def main():
    try:
        auth_provider = PlainTextAuthProvider(username=cassandra_user, password=cassandra_pass)
        cluster = Cluster(cassandra_host, port=cassandra_port, auth_provider=auth_provider, protocol_version = 4)
        session = cluster.connect()
        # print(session)
        session.set_keyspace(keyspace)

        timezone = pytz.timezone('Asia/Singapore')

        ts = datetime.now()
        # print(ts)
        # ts = datetime.now(timezone)
        # print(ts)
        year = ts.year % 100
        wholeyear = ts.year
        day = ts.day 
        month = ts.month
        yearday = year * 1000 + day
        yearmonth = year * 100 + month
        hour = ts.hour - 1
        if hour == 0:
            hour = 23

        frhour = datetime(wholeyear, month, day, hour, 0, 0)
        tohour = datetime(wholeyear, month, day, hour, 59, 59)

        print(ts, yearday, hour, frhour, tohour)

        sql_tx = "SELECT * FROM device_data  "
        sql_tx = sql_tx + "WHERE ts >= '"
        sql_tx = sql_tx + frhour.strftime("%Y-%m-%d %H:%M:%S") + "' "
        sql_tx = sql_tx + "AND ts <= '"
        sql_tx = sql_tx + tohour.strftime("%Y-%m-%d %H:%M:%S") + "' "
        sql_tx = sql_tx + "ALLOW FILTERING; "
        rows = session.execute(sql_tx)
        # print(sql_tx)
        sorted_rows = sorted(rows, key=lambda x: (x.dev_eui, x.measurement, x.ts), reverse=False)

        hourly_devs = defaultdict(str)
        hourly_measurement = defaultdict(str)
        hourly_sums = defaultdict(int)
        hourly_count = defaultdict(int)
        hourly_max = defaultdict(int)
        hourly_min = defaultdict(int)
        hourly_ave = defaultdict(int)

        cntr = 0
        dev_eui = ""
        # recs = 0
        for row in sorted_rows:
            if dev_eui != row.dev_eui or measurement != row.measurement:
                dev_eui = row.dev_eui
                measurement = row.measurement
                cntr += 1

                hourly_devs[cntr] = dev_eui
                hourly_measurement[cntr] = measurement
                hourly_sums[cntr] = 0
                hourly_count[cntr] = 0
                hourly_max[cntr] = 0
                hourly_min[cntr] = 0
                hourly_ave[cntr] = 0

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

            hourly_sums[cntr] += row.value
            hourly_count[cntr] += 1
            if hourly_max[cntr] < row.value:
                hourly_max[cntr] = row.value
            if hourly_count[cntr] > 0:
                hourly_ave[cntr] = hourly_sums[cntr] / hourly_count[cntr]
            if hourly_count[cntr] == 0:
                hourly_min[cntr] = row.value
            else:
                if hourly_min[cntr] > row.value:
                    hourly_min[cntr] = row.value
            # recs += 1
            # print(f"cntr: {recs}, User ID: {row.dev_eui}, Time: {row.ts}, Measure: {row.measurement}")              

        # print(cntr)
        # count = len(hourle_devs)        

        sql_tx = """
            INSERT INTO hourly_data (dev_eui, measurement, min, max, ave, sum, count, yearday, hour)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        for key in hourly_devs:
            cntr += 1
            # session.execute(sql_tx, (hourly_devs[key], hourly_measurement[key], hourly_min[key], 
            #                        hourly_max[key], hourly_ave[key], hourly_sums[key], hourly_count[key],
            #                        yearday, hour))

        cluster.shutdown()
    except Exception as e:
        # Code to handle the exception
        print(f"An error occurred: {e}")
        


if __name__ == "__main__":
    main()


