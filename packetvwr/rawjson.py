import logging
import sqlalchemy
import json

from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query

# from packetthings.database import packet_table
from dbscylla import get_session
from models import RawJson, RJQuery


router = APIRouter()
session = get_session()


@router.get("/rawjson/{app_name}/{yyyymmdd}",
        tags=['Packet API'])
async def get_rawjson(app_name: str,
        yyyymmdd: str):

    sql_tx = "SELECT * FROM rawjson_data WHERE app_name = "
    sql_tx = sql_tx + " '" + app_name + "' "
    sql_tx = sql_tx + "AND yyyymmdd = " + yyyymmdd + " "
    # sql_tx = sql_tx + "ALLOW FILTERING "
    print(sql_tx)
    rows = session.execute(sql_tx)
    retjson = []
    if rows.current_rows:
        retjson = rows.current_rows
    print(retjson)
    return retjson



@router.post("/pkts",
        status_code=200, tags=['Packet API'])
async def register_deveui(rjquery: RJQuery):

    dev_name = ""
    if rjquery.device_name:
        dev_name = rjquery.device_name

    frtime = ""
    if rjquery.frtime:
        date_obj = datetime.strptime(rjquery.yyyymmdd, "%Y%m%d").date()
        time_obj = datetime.strptime(rjquery.frtime, "%H:%M").time()       
        frdate = datetime.combine(date_obj, time_obj)
        frtime = frdate.strftime("%Y-%m-%d %H:%M:%S")
        print(frtime)

    totime = ""
    if rjquery.totime:
        date_obj = datetime.strptime(rjquery.yyyymmdd, "%Y%m%d").date()
        time_obj = datetime.strptime(rjquery.totime, "%H:%M").time()
        todate = datetime.combine(date_obj, time_obj)
        totime = todate.strftime("%Y-%m-%d %H:%M:%S") 
        print(totime)

    sql_tx = "SELECT * FROM rawjson_data WHERE (app_name = "
    sql_tx = sql_tx + " '" + rjquery.app_name + "') "
    sql_tx = sql_tx + "AND (yyyymmdd = " + rjquery.yyyymmdd + ") "
    if frtime:
        sql_tx = sql_tx + "AND (ts >= '" + frtime + "') "
    if totime:
        sql_tx = sql_tx + "AND (ts <= '" + totime + "') "
    if dev_name:
        sql_tx = sql_tx + "AND (device_name = '" + dev_name + "') "
    sql_tx = sql_tx + "ALLOW FILTERING "
    print(sql_tx)
    rows = session.execute(sql_tx)
    retjson = []
    if rows.current_rows:
        retjson = rows.current_rows
    # print(retjson)
    return retjson




