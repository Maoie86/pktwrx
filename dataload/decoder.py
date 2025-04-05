import json
import sys
from datetime import datetime


test = '{"end_device_ids": {"device_id": "md-0000000000026640", "application_ids": {"application_id": "pt_modbus"}, "dev_eui": "0000000000026640", "join_eui": "", "dev_addr": "E0251FAD"}, "received_at": "2024-10-23T04:35:29+0000", "uplink_message": {"f_cnt": 7700, "f_port": 16, "decoded_payload": {"raw_payload": "01 03 10 43 72 05 1f 43 e1 e3 d7 43 a8 87 ae 44 80 af 5c a3 de", "Positive_Active_Energy_L10": 242.02000427246094, "Positive_Active_Energy_L11": 451.7799987792969, "Positive_Active_Energy_L12": 337.05999755859375, "Positive_Active_Energy_Total_4": 1029.47998046875}, "received_at": "2024-10-23T04:35:29+0000", "payload_hex": "0103104372051f43e1e3d743a887ae4480af5ca3de"}, "actility_customer_id": "100001330", "actility_customer_data": {"loc": None, "alr": {"pro": None, "ver": None}, "tags": [], "doms": [], "name": "md-0000000000026640"}}' 

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
    "daily_volume" : "volume",
    "distance" : "distance_m",
    "distance_m" : "distance_m",
    "door" : "state",
    "door_state" : "state",
    "energy" : "energy",
    "hum" : "humidity",
    "humidity" : "humidity",
    "in" : "in",
    "pm1" : "pm1",
    "pm_1_0" : "pm1",
    "pm10" : "pm10",
    "pm_2_5" : "pm2_5",
    "pm2_5" : "pm2_5",
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


def pt_to_db(payload):
    global row_count
    ts_str = payload["uplink_message"]["received_at"].split("Z")[0][0:26]
    dev_eui = payload["end_device_ids"]["dev_eui"]
    application_id = payload["end_device_ids"]["application_ids"]["application_id"]
    ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S.%f")
    year = ts.year % 100
    month = ts.month
    yearmonth = year * 100 + month

    if "decoded_payload" not in payload["uplink_message"] or "received_at" not in payload["uplink_message"]:
        return

    values = []
    with open(file_name,'a') as temp_file: #, open(other_file_name,'a') as other_temp_file:
        for key, value in payload["uplink_message"]["decoded_payload"].items():
            if isinstance(value, (int, float)) :  
                try:
                    key = payload_dict[key.lower()]
                    data_batch.add(data_prepared, (dev_eui, key, yearmonth, ts, application_id, value))
                    latest_batch.add(latest_prepared, (dev_eui, key, ts, application_id, value))
                    print(data_batch)
                except:
                    continue
  

def msg_process(msg):
    data = json.loads(msg)

    try:
        payload = data["payload"]
        print(payload)
        # pt_to_db(payload)
    except:
        pass
    

def main():
    print(1)
    msg_process(test)
    print(2)

if __name__ == "__main__":
    main()
