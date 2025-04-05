import time
import random
import requests
import json
from datetime import datetime,  timezone, timedelta


from models import cam_data, cam_summ
from sqlalchemy import create_engine, select, and_, delete, update, or_, func, join
from sqlalchemy.orm import aliased, sessionmaker
from sqlalchemy.sql import func

DATABASE_URL = "postgresql://mu:Lkh6qa6YN5YS9aHqkjD@127.0.0.1/aicam"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Initialize people_count

location_names = ["Makati City Hall Bldg 1 Main Lobby", 
                "Makati City Hall Bldg 1 Health Department Right Wing", 
                "Makati City Hall Bldg 1 Health Department Left Wing", 
                "Makati City Hall Bldg 2 Main Lobby", 
                "Ospital ng Makati A Main Lobby", 
                "Ospital ng Makati B Main Lobby"]

locations = [{"name" : a, "people_count" : 0} for a in location_names]

# print(locations)

people_count = 0
INTERVAL_SECONDS = 60

# External URL to send the data
# external_url = "https://requestbin.kanbanbox.com/packetworx"  # Replace with your actual URL
external_url = "https://smartcity.packetworx.com/api-manager/server/api/v1/dev5gAiCameras"  # Replace with your actual URL
headers = { "Content-Type": "application/json", "X-OP-APIKey" : "60da7c1e485845b1b809904af60c8bed" }

while True:
    utc_now = datetime.now(timezone.utc)
    utc8_timestamp = utc_now.astimezone(timezone(timedelta(hours=8))).isoformat()
    for location in locations:
        # Generate random number between -10 and 10
        # random_change = random.randint(-10, 10)

        # Update people_count
        # location["people_count"] += random_change
        # if location["people_count"] < 0:
        #     location["people_count"] = 0

        print("processing: " + location["name"])
        # get people count from pgsql
        m_count_no = 0
        orecord = (
            session.query(cam_summ.location_tx, func.sum(cam_summ.count_no).label("total_count"))
            .filter(cam_summ.location_tx == location["name"])  # Filter condition
            .group_by(cam_summ.location_tx)
            .all()
        )        
        if orecord:
            #print(orecord)
            m_count_no = orecord[0][1]
            #print(f"Last record: ID={orecord.id}")


        # Create JSON payload
        payload = {
            "location" : location["name"],
            "people_count": m_count_no,
            "timestamp": utc8_timestamp
        }
        print("payload")
        print(payload)

        # Send POST request
        try:
            response = requests.post(external_url, json=payload, headers=headers)
            response.raise_for_status()  # Raise an exception for bad status codes
            print(f"Data sent successfully at {utc8_timestamp}. Response: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error sending data: {e}")

    # Wait for 1 minute
    time.sleep(INTERVAL_SECONDS)


