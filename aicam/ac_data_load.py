from confluent_kafka import Consumer, KafkaError, KafkaException, TopicPartition
import configparser
import socket
import logging
import requests as req
import json
import sys
from ast import literal_eval
from datetime import datetime
import sys
import schedule
import time
#import pandas as pd
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import BatchStatement, SimpleStatement, ConsistencyLevel

# Cassandra connection details
cassandra_host = ['103.247.39.52']  # Replace with your Cassandra host(s)
cassandra_port = 9042           # Default port is 9042
keyspace = 'packets'      # Replace with your keyspace
data_table = 'device_data'            # Replace with your table name
latest_table = 'latest_data'
cassandra_user = "cassandra"
cassandra_pass = "FireWall12!@"

partition_number = int(sys.argv[1]) 
#FLUSH_LIMIT = 100
LOAD_DATA_INTERVAL_SECONDS = 15
PING_MONITOR_INTERVAL_SECONDS = 60
config = configparser.ConfigParser()
config.read('config.ini')


log_path = config.get('cplogs', 'log_path')
kafka_broker = config.get('kafka', 'broker')
kafka_topic = "ptdata_prod"
kafka_groupid = "ptdata_prod"
target_auth = config.get('target', 'auth')
target_url = config.get('target', 'url')
monitor_urls = config.get('monitor-info', 'urls').split(",")

logging.basicConfig(filename=log_path,
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)

logger = logging.getLogger()
logger.setLevel(logging.WARNING)

# Connect to the Cassandra cluster
auth_provider = PlainTextAuthProvider(username=cassandra_user, password=cassandra_pass)
cluster = Cluster(cassandra_host, port=cassandra_port, auth_provider=auth_provider, protocol_version = 4)
session = cluster.connect()
print(session)
# Use the keyspace
session.set_keyspace(keyspace)

data_query = f"INSERT INTO {data_table} (dev_eui, measurement, yearmonth, ts, source_application_id, value) VALUES (?, ?, ?, ?, ?, ?)"
data_prepared = session.prepare(data_query)

latest_query = f"INSERT INTO {latest_table} (dev_eui, measurement, ts, source_application_id, value) VALUES (?, ?, ?, ?, ?)"
latest_prepared = session.prepare(latest_query)

data_batch = BatchStatement(consistency_level=ConsistencyLevel.ONE)
latest_batch = BatchStatement(consistency_level=ConsistencyLevel.ONE)


def commit_completed(err, partitions):
    if err:
        print(str(err))

conf = {'bootstrap.servers': f"{kafka_broker}",
        'group.id': f"{kafka_groupid}",
        'enable.auto.commit': False,
        'default.topic.config': {'auto.offset.reset': 'earliest'},
        'on_commit': commit_completed}

file_name = f"/tmp/packetthings-{partition_number}.csv"


payload_dict = {
    "Active_Energy_Delivered" : "energy",
    "Ambient_Air_Temperature" : "temperature",
    "Ambient_Humidity" : "humidity",
    "Ambient_Temperature" : "temperature",
    "Door_status" : "state",
    "Export_Active_Energy_L3" : "energy",
    "LLVD1_Voltage" : "voltage_L1",
    "Load_Voltage" : "voltage_L1",
    "Mains_total_watts" : "energy",
    "Positive_Active_Energy_Total" : "energy",
    "SolarVoltage" : "voltage_L1",
    "Total_Active_Power" : "energy",
    "Turbo_Temperature" : "temperature",
    "Voltage_AB" : "voltage_L1",
    "Voltage_L1N" : "voltage_L1",
    "Voltage_LN" : "voltage_L1",
    "Voltage_L_L_Avg" : "voltage_L1",
    "battery" : "battery",
    "co2" : "co2",
    "count" : "count",
    "daily_volume" : "volume",
    "distance" : "distance_m",
    "distance_m" : "distance_m",
    "door" : "state",
    "door_state" : "state",
    "door_trigger_num" : "trigger",
    "energy" : "energy",
    "hcho" : "hcho",
    "hum" : "humidity",
    "humidity" : "humidity",
    "in" : "in",
    "light_level" : "light_level",
    "pm1" : "pm1",
    "pm_1_0" : "pm1",
    "pm10" : "pm10",
    "pm_2_5" : "pm2_5",
    "pm2_5" : "pm2_5",
    "pressure" : "psi",
    "rh" : "humidity",
    "state" : "state",
    "temp" : "temperature",
    "temperature" : "temperature",
    "tvoc" : "tvoc",
    "tvoc_index" : "tvoc",
    "voltage" : "voltage_L1",
    "voltage_l1" : "voltage_L1",
    "volume" : "volume"
}


running = True
conn = ""
cursor = ""

row_count = 0

conn_prod =""
cursor_prod=""


def ping_monitor():
    for monitor_url in monitor_urls:
        tries = 0
        success = 0 
        while tries < 5 and success == 0:
            try:
                res = req.get(monitor_url)
                # print("#######################################################################")
                # print(f"{datetime.now()} Pinged {monitor_url}")
                # print("#######################################################################")
                success = 1
            except:
                tries += 1
                pass
        if tries > 5:
            print(f"{datetime.now()} Could not reach {monitor_url}")


def call_load_sql():
    global row_count, data_batch, latest_batch
    #print(row_count, datetime.now())
    if row_count > 0:
        try:
            session.execute(data_batch)
            session.execute(latest_batch)
            data_batch = BatchStatement(consistency_level=ConsistencyLevel.ONE)
            latest_batch = BatchStatement(consistency_level=ConsistencyLevel.ONE)
            print(row_count, datetime.now())
            # print("", row_count, " rows inserted")
            temp_file = open(file_name,'w')
            temp_file.close()
            row_count = 0
            #time.sleep(2)
        except Exception as e:
            print(e)
            pass



def pt_to_db(payload):
    global row_count
    #print(payload)
    #print("#########################################################################")
    dev_eui = ""
    try:
        dev_eui = payload["end_device_ids"]["dev_eui"]
    except Exception as error:
        print("An exception occurred:", error)
    application_id = "" 
    try:
        application_id = payload["end_device_ids"]["application_ids"]["application_id"]
    except Exception as error:
        print("An exception occurred:", error)

    ts_str = payload["uplink_message"]["received_at"].split("Z")[0][0:26]
    try:
        ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S.%f")
    except Exception as error:
        #print("An exception occurred:", error)
        pass

    try:
        ts_str = ts_str[0:19]
        #print(ts_str)
        ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S")
    except Exception as error:
        #print("An exception occurred:", error)
        pass

    try:
        year = ts.year % 100
        month = ts.month
        yearmonth = year * 100 + month
    except Exception as error:
        print("An exception occurred:", error)

    #print(payload)
    #print("#########################################################################")
    #length = len(application_id)
    #if length > 6:
    #    app_id = application_id[length - 6:]

    #if application_id[length - 6:] != "modbus":
    #    print(application_id)
    
    #if application_id=="pt_iaq":
    #    print(payload)
    #    print("#########################################################################")
    if dev_eui == "":
        return
    if application_id == "":
        return

    if "decoded_payload" not in payload["uplink_message"]:
        #if application_id == 'pt_iaq':
        #    print("no decoded payload : " + dev_eui + ":" + application_id)
        return

    if "received_at" not in payload["uplink_message"]:
        #if application_id == 'pt_iaq':
        #    print("no received_at : " + dev_eui + ":" + application_id)
        return
    #print(payload)
    #print("#########################################################################")

    values = []
    with open(file_name,'a') as temp_file: #, open(other_file_name,'a') as other_temp_file:
        for key, value in payload["uplink_message"]["decoded_payload"].items():
            # print(key, value)
            if isinstance(value, (int, float)) :  
                #key2 = payload_dict[key.lower()]
                #if application_id == 'pt_iaq':
                print(f"{row_count}: {dev_eui}, {key}, {value}, {application_id}")
                try:
                    key = payload_dict[key.lower()]
                    data_batch.add(data_prepared, (dev_eui, key, yearmonth, ts, application_id, value))
                    latest_batch.add(latest_prepared, (dev_eui, key, ts, application_id, value))
                    # print(data_batch)
                    row_count += 1
                    length = len(application_id)
                    # print("I", end="")
                except Exception as error:
                    #print(".", end="")
                    #print("An exception occurred:", error)
                    continue
            #else:
                # print("value not float nor int: " + value)
  

def msg_process(msg):
    try: 
        data = json.loads(msg)
    except:
        data = literal_eval(msg)

    try:
        payload = data["payload"]
        pt_to_db(payload)
    except:
        pass
    
        
MIN_COMMIT_COUNT = 1   

schedule.every(LOAD_DATA_INTERVAL_SECONDS).seconds.do(call_load_sql)
schedule.every(PING_MONITOR_INTERVAL_SECONDS).seconds.do(ping_monitor)

def consume_loop(consumer, topics):
    try:
        consumer.subscribe(topics)

        msg_count = 0
        while running:
            schedule.run_pending()

            msg = consumer.poll(timeout=1.0)
            if msg is None: continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition event
                    logger.info('%% %s [%d] reached end at offset %d\n' %
                                     (msg.topic(), msg.partition(), msg.offset()))
                elif msg.error():
                    raise KafkaException(msg.error())
                                 
            else:
                msg_process(msg.value().decode("utf-8"))
                msg_count += 1
                if msg_count % MIN_COMMIT_COUNT == 0:
                    consumer.commit(asynchronous=True)
    except KafkaException as e:
        print(f"Caught Kafka exception: {str(e)}")
        raise
    finally:
        # Close down consumer to commit final offsets.
        consumer.close()

def main():
    consumer = Consumer(conf)
    while True:
        try:
            consume_loop(consumer, [str(kafka_topic)])
        except KafkaException as e:
            print(f"Error occurred: {e}. Reconnecting...")
            time.sleep(5)
            consumer = Consumer(conf)

if __name__ == "__main__":
    main()


