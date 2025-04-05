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

# from database import dbdatabase, dbengine, dbmetadata
from models import cam_data, cam_summ
from sqlalchemy import create_engine, select, and_, delete, update, or_, func, join
from sqlalchemy.orm import aliased, sessionmaker
from sqlalchemy.sql import func


partition_number = int(sys.argv[1]) 
LOAD_DATA_INTERVAL_SECONDS = 15
PING_MONITOR_INTERVAL_SECONDS = 60
config = configparser.ConfigParser()
config.read('config.ini')

log_path = config.get('cplogs', 'log_path')
kafka_broker = config.get('kafka', 'broker')
kafka_topic = "minsait5gcam"
kafka_groupid = "aicam_prod"
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

DATABASE_URL = "postgresql://mu:Lkh6qa6YN5YS9aHqkjD@127.0.0.1/aicam"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def commit_completed(err, partitions):
    if err:
        print(str(err))

conf = {'bootstrap.servers': f"{kafka_broker}",
        'group.id': f"{kafka_groupid}",
        'enable.auto.commit': False,
        'default.topic.config': {'auto.offset.reset': 'earliest'},
        'on_commit': commit_completed}


running = True
row_count = 0

def msg_process(msg):
    m_go_yn = 0
    # print(msg)
    try: 
        data = json.loads(msg)
    except:
        data = literal_eval(msg)

    try:
        # payload = data["payload"]
        # pt_to_db(payload)
        #  print(data)
        if 'key' in data:
            m_go_yn = 1

        m_event_tx = ""
        m_device_tx = ""
        m_line_no =0
        m_in_no = 0
        o_in_no = 0
        m_out_no = 0
        o_out_no = 0
        m_tenant_tx =""
        m_capacity_no = 0
        m_sum_no = 0
        m_data_ts = ""

        if m_go_yn == 1:
            #print("Key is here")
            if data["key"] == "makati_people_counter":
                # print("Key is imakati people counter")
                if 'payload' in data:
                    # print("payload is here")
                    payload = data["payload"]
                    # print("payload is here")
                    m_event_tx = payload["event"]
                    m_device_tx = payload["device"]
                    m_line_no = int(payload["line"])
                    m_in_no = int(payload["In"])
                    m_out_no = int(payload["Out"])
                    m_capacity_no = int(payload["Capacity"])
                    m_sum_no = int(payload["Sum"])
                    m_data_ts = payload["time"]
                    #print("in:" + str(m_in_no))
                    #print("out:" + str(m_out_no))
                    
        if m_line_no == 1:
            print(m_device_tx)
            orecord = (
                session.query(cam_data)
                .filter(cam_data.device_tx==m_device_tx)  # Apply filter
                .order_by(cam_data.id.desc())       # Order by descending ID
                .first()                           # Get the first result
            )
            #print("2222")
            if orecord:
                o_in_no = orecord.in_no
                #print(f"Last record: ID={orecord.id}")                
                o_out_no = orecord.out_no
                print(f"Last record: In={orecord.in_no}, Out={orecord.out_no}")
                print(f"Current record: In={m_in_no}, Out={m_out_no}")
                #print("333")

            #print("inserting")
            new_record = cam_data(tenant_tx=m_event_tx, 
                event_tx=m_event_tx,
                device_tx=m_device_tx,
                line_no=1,
                in_no=m_in_no,
                out_no=m_out_no,
                capacity_no=m_capacity_no,
                sum_no=m_sum_no,
                data_ts=m_data_ts)
            session.add(new_record)
            session.commit()
            #print(m_device_tx)


            #with engine.connect() as conn:
            #    print(f"About to update")
            #    result = conn.execute("UPDATE cam_summ SET count_no = 88 WHERE id = 1")
            #    print(f"Rows updated: {result.rowcount}")

            #oldrecord = session.query(cam_summ).filter(cam_summ.device_tx==m_device_tx).last()
            #if oldrecord:
            #    oldrecord.name = "Updated Name"  # Update the field

            try:
                m_new_no = 0
                m_new_no = (m_in_no - o_in_no) - (m_out_no - o_out_no)
                session.query(cam_summ).filter(
                        cam_summ.device_tx == m_device_tx
                        ).update({"count_no": cam_summ.count_no + m_new_no})
                session.commit()
                print("Update successful. " + str(m_new_no))
            except Exception as e:
                session.rollback()
                print(f"Error during update: {e}")

            #record = session.query(cam_summ).filter(cam_summ.device_tx == m_device_tx).first()
            #if record:
            #    record.people_no = m_sum_no
            #    session.commit()             # Commit the transaction
            #    print(f"Record updated: {record.name}")
            #else:
            #    print("Record not found.")

            #stmt = update(cam_summ).where(
            #        cam_summ.c.device_tx == m_device_tx
            #        ).values(people_no = people_no + 1)
            #with engine.connect() as conn:
                #print(stmt)
            #    result = conn.execute(stmt)
            #    print("updated...")
            #    conn.commit()

    except:
        pass
    
        
MIN_COMMIT_COUNT = 1   

def consume_loop(consumer, topics):
    try:
        consumer.subscribe(topics)

        msg_count = 0
        while running:
            # schedule.run_pending()
            # print("looping..")
            msg = consumer.poll(timeout=1.0)
            if msg is None: continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logger.info('%% %s [%d] reached end at offset %d\n' %
                                     (msg.topic(), msg.partition(), msg.offset()))
                elif msg.error():
                    raise KafkaException(msg.error())
                                 
            else:
                # print("looping..")
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


