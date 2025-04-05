import logging
import sqlalchemy
import json
import calendar
import time

from enum import Enum
from typing import Annotated, Union
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from collections import defaultdict

# from packetthings.database import packet_table
from packetthings.dbscylla import get_session
from packetthings.models.packet import (
        Packet, 
        ThinPacket, 
        LatestPacket, 
        LatestPacketUnit, 
        PacketQuery, 
        PacketQueryDates, 
        PacketTotals)
from packetthings.models.user import User
from packetthings.routers.device import find_device_by_deveui
from packetthings.routers.role import find_role_by_id
from packetthings.routers.type import find_type_by_id
from packetthings.routers.typedetail import find_typedetail_by_type_id
from packetthings.routers.measurement import (
        find_measurement_by_id, 
        find_measurement_by_name,
        get_all_measurements)
from packetthings.routers.unit import (
        get_all_units, 
        find_unit_by_id, 
        find_unit_by_name)
from packetthings.security import get_current_user

router = APIRouter()

logger = logging.getLogger(__name__)
session = get_session()

# change to True to only send ts and valu  
thin_yn = False 

class PacketSorting(str, Enum):
    new = "new"
    old = "old"
    most_likes = "most_likes"


@router.get("/packet_dates/{dev_eui}/(fromdate}/{todate}", 
        response_model=list[Union[Packet, ThinPacket]],
        summary="Get Raw Packets For a Date Period",
        tags=['Packet API'])
async def get_packets_dates(dev_eui: str, 
        fromdate: date,
        todate: date,
        current_user: Annotated[User, Depends(get_current_user)]):
    """
    This returns a list of packets within a starting date until an end date.

    Path Parameters:\n
    dev_eui   - The Device EUI\n
    fromdate - Starting Date YYYY-MM-DD format\n
    todate - Ending Date YYYY-MM-DD format
    """

    logger.info(f"Finding packet with eui {dev_eui}")
    # logger.info(packet_query)

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Current user has undefined role")

    dev = await find_device_by_deveui(dev_eui)
    if dev:
        # check if device belong to this user of public
        if (role.name != 'Admin') and (dev.user_id != current_user.id):
            if (dev.domain != 'Public'):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                        detail="User is not allowed to view data from this device.")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                detail="A device with that deveui was not found")

    devtype = await find_type_by_id(dev.type_id)
    if devtype is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that type_id was not found",
        )

    devtypedetail = await find_typedetail_by_type_id(dev.type_id, current_user)
    if devtypedetail is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A typedetail with that type_id was not found",
        )

    retjson = []
    ctr = 1
    yearmonth = fromdate.strftime('%y%m')

    for dtl in devtypedetail:
        measurement = await find_measurement_by_id(dtl.measurement_id)

        if measurement:
            today = date.today()
            if thin_yn:
                sql_tx = "SELECT ts, value FROM device_data WHERE dev_eui = '" 
            else:
                sql_tx = "SELECT * FROM device_data WHERE dev_eui = '" 
            sql_tx = sql_tx + dev_eui + "' "
            sql_tx = sql_tx + "AND measurement = '" + measurement.name + "' "
            sql_tx = sql_tx + "AND yearmonth = " 
            sql_tx = sql_tx + str(yearmonth) + " "
            sql_tx = sql_tx + "AND ts >= '" 
            sql_tx = sql_tx + fromdate.strftime("%Y-%m-%d %H:%M:%S") + "' "
            sql_tx = sql_tx + "AND ts <= '" 
            sql_tx = sql_tx + todate.strftime("%Y-%m-%d %H:%M:%S") + "' "
            sql_tx = sql_tx + "ALLOW FILTERING; "
            #logger.info(sql_tx)
            rows = session.execute(sql_tx)
            if rows.current_rows:
                if ctr == 1:
                    retjson = rows.current_rows
                    ctr = 0
                else:
                    retjson.append(rows.current_rows[0])
                    # for rw in rows.current_rows:
                    #     retjson.append(rw)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Measurement ID not found")

    # if retjson == []:
    #    raise HTTPException(status_code=200,
    #            detail="No data available.")

    return retjson


@router.get("/packet_month/{dev_eui}/{yearmonth}", 
        response_model=list[Union[Packet, ThinPacket]], 
        summary="Get Raw Packets For a Given Month",
        tags=['Packet API'])
async def get_packets_months(dev_eui: str, 
        yearmonth: int, 
        current_user: Annotated[User, Depends(get_current_user)]):
    """
    This returns a list of packets within a given month.

    Path Parameters:\n
    dev_eui   - The Device EUI\n
    yearmonth - YYMM format
    """

    logger.info(f"Finding packet with eui {dev_eui}")
    # logger.info(packet_query)

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    dev = await find_device_by_deveui(dev_eui)
    if dev:
        # check if device belong to this user of public
        if (role.name != 'Admin') and (dev.user_id != current_user.id):
            if (dev.doman != 'Public'):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                        detail="User is not allowed to view data from this device.")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                detail="A device with that deveui was not found")

    devtype = await find_type_by_id(dev.type_id)
    if devtype is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that type_id was not found",
        )

    devtypedetail = await find_typedetail_by_type_id(dev.type_id, current_user)
    if devtypedetail is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A typedetail with that type_id was not found",
        )

    retjson = []
    ctr = 1

    for dtl in devtypedetail:
        measurement = await find_measurement_by_id(dtl.measurement_id)

        if measurement:
            if thin_yn:
                sql_tx = "SELECT ts, value FROM device_data WHERE dev_eui = '" 
            else:
                sql_tx = "SELECT * FROM device_data WHERE dev_eui = '" 
            sql_tx = sql_tx + dev_eui + "' "
            sql_tx = sql_tx + "AND measurement = '" + measurement.name + "' "
            sql_tx = sql_tx + "AND yearmonth = " + str(yearmonth) + " "
            sql_tx = sql_tx + "ALLOW FILTERING; "
            #logger.info(sql_tx)
            rows = session.execute(sql_tx)
            if rows.current_rows:
                if ctr == 1:
                    retjson = rows.current_rows
                    ctr = 0
                else:
                    retjson.append(rows.current_rows[0])
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Measurement ID not found")

    #if retjson == []:
    #    raise HTTPException(status_code=200,
    #            detail="No data available.")

    return retjson



@router.get("/latest_packet/{dev_eui}", 
        response_model=list[Union[LatestPacketUnit, ThinPacket]], 
        summary="Get the Latest Packets For a Device",
        tags=['Packet API'])
async def get_latest_packet(dev_eui: str, 
        current_user: Annotated[User, Depends(get_current_user)]):
    """
    This returns a the latest packet(s) for device.\n
    Path Parameters:\n
    dev_eui   - The Device EUI\n
    """

    thin_yn = False

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Current user has undefined role")

    dev = await find_device_by_deveui(dev_eui)
    if dev:
        # check if device belong to this user of public
        if (role.name != 'Admin') and (dev.user_id != current_user.id):
            if (dev.domain != 'Public'):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                        detail="User is not allowed to view data from this device.")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                detail="A device with that deveui was not found")

    devtype = await find_type_by_id(dev.type_id)
    if devtype is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that type_id was not found",
        )

    devtypedetail = await find_typedetail_by_type_id(dev.type_id, current_user)
    if devtypedetail is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A typedetail with that type_id was not found",
        )

    retjson = []
    ctr = 1

    for dtl in devtypedetail:
        measurement = await find_measurement_by_id(dtl.measurement_id)

        if measurement:
            unit = await find_unit_by_id(measurement.unit_id)
            unit_nm = measurement.name
            if unit:
                unit_nm = unit.name
            if thin_yn:
                sql_tx = "SELECT ts, value FROM latest_data WHERE dev_eui = " 
            else:
                sql_tx = "SELECT * FROM latest_data WHERE dev_eui = " 
            sql_tx = sql_tx + " '" + dev_eui + "' "
            sql_tx = sql_tx + "AND measurement = '" + measurement.name + "' "
            #logger.info(sql_tx)
            rows = session.execute(sql_tx)
            if rows.current_rows:
                if ctr == 1:
                    tstmp = rows.current_rows[0]['ts'].strftime('%Y-%m-%d %H:%M')
                    newmeasurement = measurement.name.replace("_", ".")
                    latestpacket = LatestPacketUnit(dev_eui=dev.dev_eui,
                        measurement=newmeasurement.upper(),
                        unit=unit_nm,
                        value=rows.current_rows[0]['value'],
                        source_application_id=tstmp,
                        ts=rows.current_rows[0]['ts'])

                    retjson = [latestpacket]
                    # retjson = rows.current_rows
                    ctr = 0
                else:
                    tstmp = rows.current_rows[0]['ts'].strftime('%Y-%m-%d %H:%M')
                    newmeasurement = measurement.name.replace("_", ".")
                    latestpacket = LatestPacketUnit(dev_eui=dev.dev_eui,
                        measurement=newmeasurement.upper(),
                        unit=unit_nm,
                        value=rows.current_rows[0]['value'],
                        source_application_id=tstmp,
                        ts=rows.current_rows[0]['ts'])

                    retjson.append(latestpacket)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Measurement ID not found")

    #if retjson == []:
    #    raise HTTPException(status_code=200,
    #            detail="No data available.")

    return retjson


@router.get("/latest_packet_measurement/{dev_eui}/{measurement}", 
        response_model=list[Union[LatestPacketUnit, ThinPacket]], 
        summary="Get the Latest Packets For a Device for a Specific Measurement",
        tags=['Packet API'])
async def get_latest_packet_measurement(dev_eui: str,
        measurement: str,
        current_user: Annotated[User, Depends(get_current_user)]):
    """
    This returns the latest packwt for a device and measurement\n
    Path Parameters:\n
    dev_eui   - The Device EUI\n
    measurement - the speific measurement (temperature, pm2_5, humidity)
    """

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current user has undefined role")

    dev = await find_device_by_deveui(dev_eui)
    if dev:
        # check if device belong to this user of public
        if (role.name != 'Admin') and (dev.user_id != current_user.id):
            if (dev.domain != 'Public'):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User is not allowed to view data from this device.")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="A device with that deveui was not found")

    devtype = await find_type_by_id(dev.type_id)
    if devtype is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that type_id was not found",
        )

    devtypedetail = await find_typedetail_by_type_id(dev.type_id, current_user)
    if devtypedetail is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A typedetail with that type_id was not found",
        )

    retjson = []

    measure = await find_measurement_by_name(measurement)
    if not measure:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Measurement name not found")


    if thin_yn:
        sql_tx = "SELECT ts, value FROM latest_data WHERE dev_eui = "
    else:
        sql_tx = "SELECT * FROM latest_data WHERE dev_eui = "
    sql_tx = sql_tx + " '" + dev_eui + "' "
    sql_tx = sql_tx + "AND measurement = '" + measurement + "' "
    #logger.info(sql_tx)
    rows = session.execute(sql_tx)
    if rows.current_rows:
        tstmp = rows.current_rows[0]['ts'].strftime('%Y-%m-%d %H:%M')

        unit = await find_unit_by_id(measure.unit_id)
        unit_nm = measure.name
        if unit:
            unit_nm = unit.name

        latestpacket = LatestPacketUnit(dev_eui=dev.dev_eui,
            measurement=measure.name.replace('_', '.').upper(),
            value=rows.current_rows[0]['value'],
            unit=unit_nm,
            source_application_id=tstmp,
            ts=rows.current_rows[0]['ts'])

        retjson = [latestpacket]
    return retjson



@router.post("/latest_packet", 
        response_model=list[Union[LatestPacket, ThinPacket]], 
        summary="Get the Latest Packets For a Device Using the Post Method",
        tags=['Packet API'])
async def post_latest_packet(packet_query: PacketQuery, 
        current_user: Annotated[User, Depends(get_current_user)]):
    """
    This returns the latest packet(s) for a device

    Body Parameters: as json\n
    dev_eui   - The Device EUI\n
    measurement - the speific measurement (temperature, pm2_5, humidity)\n
    yearmonth - YYMM Format\n
    aggregate -  not used, string\n
    """

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current user has undefined role")

    dev = await find_device_by_deveui(packet_query.dev_eui)
    if dev:
        if (role.name != 'Admin') and (dev.user_id != current_user.id):
            if (dev.domain != 'Public'):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User is not allowed to view data from this device.")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                detail="A device with that deveui was not found")

    devtype = await find_type_by_id(dev.type_id)
    if devtype is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that type_id was not found",
        )

    devtypedetail = await find_typedetail_by_type_id(dev.type_id, current_user)
    if devtypedetail is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A typedetail with that type_id was not found",
        )

    retjson = []
    ctr = 1

    for dtl in devtypedetail:
        measurement = await find_measurement_by_id(dtl.measurement_id)
        if measurement: 
            if (packet_query.measurement=='') or (packet_query.measurement==measurement.name):  
                if thin_yn:
                    sql_tx = "SELECT ts, value FROM latest_data " 
                else:
                    sql_tx = "SELECT * FROM latest_data " 
                sql_tx = sql_tx + "WHERE dev_eui = '"+packet_query.dev_eui+"' "
                sql_tx = sql_tx + "AND measurement = '" + measurement.name + "' "
                #logger.info(sql_tx)
                rows = session.execute(sql_tx)
                if rows.current_rows:
                    if ctr == 1:
                        retjson = rows.current_rows
                        ctr = 0
                    else:
                        retjson.append(rows.current_rows[0])
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Measurement ID not found")

    #if retjson == []:
    #    raise HTTPException(status_code=200,
    #            detail="No data available.")

    return retjson


@router.post("/packet_month", 
        response_model=list[Union[Packet, ThinPacket]], 
        summary="Get Raw Packets For a Given Month Using the Post Method",
        tags=['Packet API'])
async def post_packets_months(packet_query: PacketQuery,
        current_user: Annotated[User, Depends(get_current_user)]):
    """
    This returns a list of packet(s) for a given month

    Body Parameters: as json\n
    dev_eui   - The Device EUI\n
    measurement - the speific measurement (temperature, pm2_5, humidity)\n
    yearmonth - YYMM Format\n
    aggregate -  not used, string\n
    """


    logger.info(f"Finding packet with eui {packet_query.dev_eui}")
    #logger.info(packet_query)

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    dev = await find_device_by_deveui(packet_query.dev_eui)
    if dev:
        # check if device belong to this user of public
        if (role.name != 'Admin') and dev.user_id != current_user.id:
            if (dev.user_id != current_user.id) and (dev.doman != 'Public'):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User is not allowed to view data from this device.")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="A device with that deveui was not found")

    devtype = await find_type_by_id(dev.type_id)
    if devtype is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that type_id was not found",
        )

    devtypedetail = await find_typedetail_by_type_id(dev.type_id, current_user)
    if devtypedetail is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A typedetail with that type_id was not found",
        )

    retjson = []
    ctr = 1

    for dtl in devtypedetail:
        measurement = await find_measurement_by_id(dtl.measurement_id)

        if measurement:
            if (packet_query.measurement=='') or (packet_query.measurement==measurement.name):
                if thin_yn:
                    sql_tx = "SELECT ts, value FROM device_data WHERE dev_eui = '"
                else:
                    sql_tx = "SELECT * FROM device_data WHERE dev_eui = '"
                sql_tx = sql_tx + packet_query.dev_eui + "' "
                sql_tx = sql_tx + "AND measurement = '" + measurement.name + "' "
                sql_tx = sql_tx + "AND yearmonth = " + str(packet_query.yearmonth) + " "
                sql_tx = sql_tx + "ALLOW FILTERING; "
                #logger.info(sql_tx)
                rows = session.execute(sql_tx)
                if rows.current_rows:
                    if ctr == 1:
                        retjson = rows.current_rows
                        ctr = 0
                    else:
                        retjson.append(rows.current_rows[0])
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Measurement ID not found")

    #if retjson == []:
    #    raise HTTPException(status_code=200,
    #            detail="No data available.")

    return retjson


@router.post("/packet_dates", 
        response_model=list[Union[Packet, ThinPacket]], 
        tags=['Packet API'])
async def get_packets_dates(packet_query: PacketQueryDates,
        current_user: Annotated[User, Depends(get_current_user)]):
    """
    This returns a list of packet(s) for a specific period

    Body Parameters: as json\n
    dev_eui   - The Device EUI\n
    measurement - the speific measurement (temperature, pm2_5, humidity)\n
    yearmonth - YYMM Format\n
    aggregate -  not used, string\n
    fromdate - Starting Date YYYY-MM-DD format\n
    todate - Ending Date YYYY-MM-DD format
    """

    logger.info(f"Finding packet with eui {packet_query.dev_eui}")
    #logger.info(packet_query)

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    dev = await find_device_by_deveui(packet_query.dev_eui)
    if dev:
        # check if device belong to this user of public
        if (role.name != 'Admin') and (dev.user_id != current_user.id):
            if (dev.domain != 'Public'):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User is not allowed to view data from this device.")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="A device with that deveui was not found")


    devtype = await find_type_by_id(dev.type_id)
    if devtype is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that type_id was not found",
        )

    devtypedetail = await find_typedetail_by_type_id(dev.type_id, current_user)
    if devtypedetail is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A typedetail with that type_id was not found",
        )

    retjson = []
    ctr = 1

    for dtl in devtypedetail:
        measurement = await find_measurement_by_id(dtl.measurement_id)

        if measurement:
            if (packet_query.measurement=='') or (packet_query.measurement==measurement.name):
                today = date.today()
                if thin_yn:
                    sql_tx = "SELECT ts, value FROM device_data WHERE dev_eui = '"
                else:
                    sql_tx = "SELECT * FROM device_data WHERE dev_eui = '"
                sql_tx = sql_tx + packet_query.dev_eui + "' "
                sql_tx = sql_tx + "AND measurement = '" + measurement.name + "' "
                sql_tx = sql_tx + "AND yearmonth = "
                sql_tx = sql_tx + str(packet_query.yearmonth) + " "
                sql_tx = sql_tx + "AND ts >= '"
                sql_tx = sql_tx + packet_query.fromdate.strftime("%Y-%m-%d %H:%M:%S") + "' "
                sql_tx = sql_tx + "AND ts <= '"
                sql_tx = sql_tx + packet_query.todate.strftime("%Y-%m-%d %H:%M:%S") + "' "
                sql_tx = sql_tx + "ALLOW FILTERING; "
                #logger.info(sql_tx)
                rows = session.execute(sql_tx)
                if rows.current_rows:
                    if ctr == 1:
                        retjson = rows.current_rows
                        ctr = 0
                    else:
                        retjson.append(rows.current_rows[0])
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Measurement ID not found")

    #if retjson == []:
    #    raise HTTPException(status_code=200,
    #            detail="No data available.")

    return retjson


@router.get("/packet_hours/{dev_eui}/{measurement}/{hours}",
        response_model=list[Union[Packet, ThinPacket]], 
        tags=['Packet API'])
async def get_packets_dates_lasthours(dev_eui: str,
        measure: str,
        hrs: int,
        current_user: Annotated[User, Depends(get_current_user)]):
    """
    This returns a list of packet(s) for a device and measurement for the past hour(s)\n
    Path Parameters:\n
    dev_eui   - The Device EUI\n
    measurement - the speific measurement (temperature, pm2_5, humidity)
    hours   - number of hors\n
    """

    logger.info(f"Finding packet with eui {dev_eui}")
    # logger.info(packet_query)

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current user has undefined role")

    dev = await find_device_by_deveui(dev_eui)
    if dev:
        # check if device belong to this user of public
        if (role.name != 'Admin') and (dev.user_id != current_user.id):
            if (dev.domain != 'Public'):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User is not allowed to view data from this device.")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="A device with that deveui was not found")

    devtype = await find_type_by_id(dev.type_id)
    if devtype is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that type_id was not found",
        )

    devtypedetail = await find_typedetail_by_type_id(dev.type_id, current_user)
    if devtypedetail is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A typedetail with that type_id was not found",
        )

    retjson = []
    ctr = 1
    todate = datetime.now()
    yearmonth = todate.strftime('%y%m')
    fromdate = todate - timedelta(hours=hrs)
    for dtl in devtypedetail:
        measurement = await find_measurement_by_id(dtl.measurement_id)

        if measurement:
            if (measurement.name==measure):
            
                today = date.today()
                if thin_yn:
                    sql_tx = "SELECT ts, value FROM device_data WHERE dev_eui = '"
                else:
                    sql_tx = "SELECT * FROM device_data WHERE dev_eui = '"
                sql_tx = sql_tx + dev_eui + "' "
                sql_tx = sql_tx + "AND measurement = '" + measurement.name + "' "
                sql_tx = sql_tx + "AND yearmonth = "
                sql_tx = sql_tx + str(yearmonth) + " "
                sql_tx = sql_tx + "AND ts >= '"
                sql_tx = sql_tx + fromdate.strftime("%Y-%m-%d %H:%M:%S") + "' "
                sql_tx = sql_tx + "AND ts <= '"
                sql_tx = sql_tx + todate.strftime("%Y-%m-%d %H:%M:%S") + "' "
                sql_tx = sql_tx + "ALLOW FILTERING; "
                #logger.info(sql_tx)
                rows = session.execute(sql_tx)
                if rows.current_rows:
                    if ctr == 1:
                        retjson = rows.current_rows
                        ctr = 0
                    else:
                        retjson.append(rows.current_rows[0])
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Measurement ID not found")

    #if retjson == []:
    #    raise HTTPException(status_code=200,
    #            detail="No data available.")

    return retjson



@router.get("/packet_days/{dev_eui}/{measurement}/{numdays}",
        response_model=list[Union[LatestPacket, PacketTotals, ThinPacket]], 
        tags=['Packet API'])
async def get_packets_dates_lastdays(dev_eui: str,
        measure: str,
        numdays: int,
        current_user: Annotated[User, Depends(get_current_user)]):
    """
    This returns a list of packet(s) for a device and measurement for the past day(s)\n
    Path Parameters:\n
    dev_eui   - The Device EUI\n
    measurement - the speific measurement (temperature, pm2_5, humidity)
    days   - number of days\n
    """

    logger.info(f"Finding packet with eui {dev_eui}")
    # logger.info(packet_query)

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current user has undefined role")

    dev = await find_device_by_deveui(dev_eui)
    if dev:
        # check if device belong to this user of public
        if (role.name != 'Admin') and (dev.user_id != current_user.id):
            if (dev.domain != 'Public'):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User is not allowed to view data from this device.")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="A device with that deveui was not found")

    devtype = await find_type_by_id(dev.type_id)
    if devtype is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that type_id was not found",
        )

    devtypedetail = await find_typedetail_by_type_id(dev.type_id, current_user)
    if devtypedetail is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A typedetail with that type_id was not found",
        )

    retjson = []
    ctr = 1
    todate = datetime.now()
    yearmonth = todate.strftime('%y%m')
    fromdate = todate - timedelta(days=numdays)
    for dtl in devtypedetail:
        measurement = await find_measurement_by_id(dtl.measurement_id)

        if measurement:
            if (measurement.name==measure):

                today = date.today()
                if numdays == 1:
                    sql_tx = "SELECT * FROM device_data WHERE dev_eui = '"
                    sql_tx = sql_tx + dev_eui + "' "
                    sql_tx = sql_tx + "AND measurement = '" + measurement.name + "' "
                    sql_tx = sql_tx + "AND yearmonth = "
                    sql_tx = sql_tx + str(yearmonth) + " "
                    sql_tx = sql_tx + "AND ts >= '"
                    sql_tx = sql_tx + fromdate.strftime("%Y-%m-%d %H:%M:%S") + "' "
                    sql_tx = sql_tx + "AND ts <= '"
                    sql_tx = sql_tx + todate.strftime("%Y-%m-%d %H:%M:%S") + "' ORDER BY ts "
                    sql_tx = sql_tx + "ALLOW FILTERING; "
                    #logger.info(sql_tx)
                    rows = session.execute(sql_tx)
                    if rows.current_rows:
                        for pkt in rows.current_rows:
                            tstmp = pkt['ts'].strftime('%Y-%m-%d %H:%M')
                            if measure=="pm2_5":
                                newmeasurement = measure.replace("_", ".")
                            else:
                                newmeasurement = measure
                            latestpacket = LatestPacket(dev_eui=dev_eui,
                                measurement=newmeasurement,
                                value=pkt['value'],
                                source_application_id=tstmp,
                                ts=pkt['ts'])

                            retjson.append(latestpacket)
                else:
                    daily_sums = defaultdict(float)
                    daily_count = defaultdict(int)
                    daily_max = defaultdict(float)
                    daily_min = defaultdict(float)
                    daily_ave = defaultdict(int)
                    daily_date = defaultdict(str)

                    current_date = fromdate
                    day_key = 0
                    while current_date < todate:
                        day_key = day_key + 1
                        daily_date[day_key] = current_date.strftime('%Y-%m-%d')
                        daily_sums[day_key] = 0
                        daily_count[day_key] = 0
                        daily_max[day_key] = 0
                        daily_ave[day_key] = 0
                        daily_min[day_key] = 0
                        current_date += timedelta(days=1)

                        yearmonth = current_date.strftime('%y%m')

                        sql_tx = "SELECT * FROM device_data WHERE dev_eui = '"
                        sql_tx = sql_tx + dev_eui + "' "
                        sql_tx = sql_tx + "AND measurement = '" + measurement.name + "' "
                        sql_tx = sql_tx + "AND yearmonth = "
                        sql_tx = sql_tx + str(yearmonth) + " "
                        sql_tx = sql_tx + "AND ts >= '"
                        sql_tx = sql_tx + current_date.strftime("%Y-%m-%d") + " 00:00:00' "
                        sql_tx = sql_tx + "AND ts <= '"
                        sql_tx = sql_tx + current_date.strftime("%Y-%m-%d") + " 23:59:59' "
                        sql_tx = sql_tx + "ALLOW FILTERING; "
                        #logger.info(sql_tx)
                        rows = session.execute(sql_tx)

                        for pkt in rows:
                            timestamp = pkt["ts"]
                            daily_sums[day_key] += pkt["value"]
                            daily_count[day_key] += 1
                            if daily_max[day_key] < pkt["value"]:
                                daily_max[day_key] = pkt["value"]
                            if daily_count[day_key] > 0:
                                daily_ave[day_key] = daily_sums[day_key] / daily_count[day_key]
                            if daily_count[day_key] == 0:
                                daily_min[day_key] = pkt["value"]
                            else:
                                if daily_min[day_key] > pkt["value"]:
                                    daily_min[day_key] = pkt["value"]

                    ctr = 1
                    if measure=="pm2_5":
                        newmeasurement = measure.replace("_", ".")
                    else:
                        newmeasurement = measure
                    
                    for key in daily_sums:
                        total = LatestPacket(dev_eui=dev_eui,
                            measurement=newmeasurement,
                            value=daily_ave[key],
                            source_application_id=daily_date[key],
                            ts=daily_date[key])
                        ctr += 1
                        retjson.append(total)

        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Measurement ID not found")

    if retjson == []:
        totals = []
        dayname = datetime.strftime(datetime.now(), '%Y-%m-%d')
        total = LatestPacket(dev_eui=dev_eui,
            measurement=measure,
            value=0,
            source_application_id=dayname,
            ts=dayname)
        # total = ThinPacket(ts=dayname, value=0)
        totals.append(total)
        return totals

    return retjson


@router.get("/packet_perday/{dev_eui}/{measurement}/{yearmonth}",
        response_model=list[PacketTotals],
        tags=['Packet API'])
async def get_packets_days(dev_eui: str,
        measure: str,
        yearmonth: int,
        current_user: Annotated[User, Depends(get_current_user)]):
    """
    This returns a list of packet(s) for a device and measurement for a given month\n
    summarized per day (average, min, max, count)\n
    Path Parameters:\n
    dev_eui   - The Device EUI\n
    measurement - the specific measurement (temperature, pm2_5, humidity)\n
    yearrmonth   - YYMM\n
    """


    # we need to find out if this query ha been done befoire
    # and stored in a table so we do not get from the raw data
    # this will save a lot of resources

    logger.info(f"Getting totals pero month for device with eui {dev_eui}")
    # logger.info(packet_query)

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current user has undefined role")

    dev = await find_device_by_deveui(dev_eui)
    if dev:
        # check if device belong to this user of public
        if (role.name != 'Admin') and (dev.user_id != current_user.id):
            if (dev.domain != 'Public'):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User is not allowed to view data from this device.")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="A device with that deveui was not found")

    devtype = await find_type_by_id(dev.type_id)
    if devtype is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This device has an invalid device type",
        )

    devtypedetail = await find_typedetail_by_type_id(dev.type_id, current_user)
    if devtypedetail is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device type has no type deatils",
        )

    retjson = []
    ctr = 1
    todate = datetime.now()
    thisyearmonth = todate.strftime('%y%m')
    
    # fromdate = todate - timedelta(days=numdays)
    for dtl in devtypedetail:
        measurement = await find_measurement_by_id(dtl.measurement_id)
        if measurement:
            if (measurement.name==measure):
                ctr = 0 

    if ctr == 0:
        sql_tx = "SELECT * FROM device_data WHERE dev_eui = '"
        sql_tx = sql_tx + dev_eui + "' "
        sql_tx = sql_tx + "AND measurement = '" + measure + "' "
        sql_tx = sql_tx + "AND yearmonth = "
        sql_tx = sql_tx + str(yearmonth) + " "
        # logger.info(sql_tx)
        rows = session.execute(sql_tx)
        if rows.current_rows:
            retjson = rows.current_rows
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Measurement not found")
        
    # Generate all days in the month and set their sum to 0
    ym = str(yearmonth)
    year = int(ym[:2])
    month = int(ym[2:4])
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    daily_sums = defaultdict(int)
    daily_count = defaultdict(int)
    daily_max = defaultdict(int)
    daily_min = defaultdict(int)
    daily_ave = defaultdict(int)
    daily_date = defaultdict(str)

    current_date = start_date
    while current_date < end_date:
        day_key = current_date.day  # Get just the date part
        daily_date[day_key] = current_date.strftime('%Y-%m-%d')
        daily_sums[day_key] = 0
        daily_count[day_key] = 0
        daily_max[day_key] = 0
        daily_ave[day_key] = 0
        daily_min[day_key] = 0
        daily_min[day_key] = 0
        current_date += timedelta(days=1)

    for pkt in retjson:
        #if pkt["value"] != 0:
        timestamp = pkt["ts"]
        day_key = timestamp.day  # Get just the date part
        daily_sums[day_key] += pkt["value"]    
        daily_count[day_key] += 1
        if daily_max[day_key] < pkt["value"]:
            daily_max[day_key] = pkt["value"]
        if daily_count[day_key] > 0:
            daily_ave[day_key] = daily_sums[day_key] / daily_count[day_key]
        if daily_count[day_key] == 0:
            daily_min[day_key] = pkt["value"]
        else:
            if daily_min[day_key] > pkt["value"]:
                daily_min[day_key] = pkt["value"]

    # print(daily_sums)
    totals = []
    ctr = 1
    logger.debug("len : " + str(len(daily_sums)))
    for key in daily_sums:
        # print(f"Key: {key}, Value: {daily_sums[key]}")
        # lastdate = key.strftime('%Y-%m-%d')
        total = PacketTotals(seq=ctr,
            name=daily_date[key],
            total=daily_sums[key],
            max=daily_max[key],
            min=daily_min[key],
            count=daily_count[key],
            aveint=int(daily_ave[key]),
            ave=daily_ave[key])
        ctr += 1
        totals.append(total)

    sorted_totals = sorted(totals, key=lambda x: getattr(x, "seq"))
    return sorted_totals
    # return totals


@router.get("/packet_perhour/{dev_eui}/{measurement}/{date}",
        response_model=list[PacketTotals],
        tags=['Packet API'])
async def get_packets_hours(dev_eui: str,
        measure: str,
        datestr: str,
        current_user: Annotated[User, Depends(get_current_user)]):
    """
    This returns a list of packet(s) for a device and measurement for a given idate\n
    summarized per hour (average, min, max, count)\n
    Path Parameters:\n
    dev_eui   - The Device EUI\n
    measurement - the speific measurement (temperature, pm2_5, humidity)\n
    date   - YYYY-MM-DD\n
    """

    logger.info(f"Finding packet with eui {dev_eui}")
    # logger.info(packet_query)
    dev_eui = dev_eui.strip()
    datestr = datestr.strip()
    measure = measure.strip()

    try:
        pktdate = datetime.strptime(datestr, "%m/%d/%Y")
        # Adjust format as needed
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid date format")

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current user has undefined role")

    dev = await find_device_by_deveui(dev_eui)
    if dev:
        # check if device belong to this user of public
        if (role.name != 'Admin') and (dev.user_id != current_user.id):
            if (dev.domain != 'Public'):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User is not allowed to view data from this device.")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="A device with that deveui was not found")

    devtype = await find_type_by_id(dev.type_id)
    if devtype is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that type_id was not found",
        )

    retjson = []
    ctr = 1
    yearmonth = pktdate.strftime('%y%m')
    fromdate = datetime(pktdate.year, pktdate.month, pktdate.day, 0, 0, 0)
    todate = datetime(pktdate.year, pktdate.month, pktdate.day, 23, 59, 59)    

    devtypedetail = await find_typedetail_by_type_id(dev.type_id, current_user)
    for dtl in devtypedetail:
        measurement = await find_measurement_by_id(dtl.measurement_id)
        if measurement:
            if (measurement.name==measure):
                ctr = 0

    if ctr == 0:
        sql_tx = "SELECT * FROM device_data WHERE dev_eui = '"
        sql_tx = sql_tx + dev_eui + "' "
        sql_tx = sql_tx + "AND measurement = '" + measure + "' "
        sql_tx = sql_tx + "AND yearmonth = "
        sql_tx = sql_tx + str(yearmonth) + " "
        sql_tx = sql_tx + "AND ts >= '"
        sql_tx = sql_tx + fromdate.strftime("%Y-%m-%d %H:%M:%S") + "' "
        sql_tx = sql_tx + "AND ts <= '"
        sql_tx = sql_tx + todate.strftime("%Y-%m-%d %H:%M:%S") + "' "
        sql_tx = sql_tx + "ALLOW FILTERING; "
        #logger.info(sql_tx)
        rows = session.execute(sql_tx)
        if rows.current_rows:
            retjson = rows.current_rows
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Measurement not found")

    hourly_sums = defaultdict(int)
    hourly_count = defaultdict(int)
    hourly_max = defaultdict(int)
    hourly_min = defaultdict(int)
    hourly_ave = defaultdict(int)

    for hour in range(24):
        hourly_sums[hour] = 0
        hourly_count[hour] = 0
        hourly_max[hour] = 0
        hourly_min[hour] = 0
        hourly_ave[hour] = 0

    for pkt in retjson:
        # if pkt["value"] != 0:
        hour = pkt["ts"].hour
        hourly_sums[hour] += pkt["value"]
        hourly_count[hour] += 1
        if hourly_max[hour] < pkt["value"]:
            hourly_max[hour] = pkt["value"]
        if hourly_count[hour] > 0:
            hourly_ave[hour] = hourly_sums[hour] / hourly_count[hour]
        if hourly_count[hour] == 0:
            hourly_min[hour] = pkt["value"]
        else:
            if hourly_min[hour] > pkt["value"]:
                hourly_min[hour] = pkt["value"]

    # print(daily_sums)
    totals = []
    for hour in range(24):
        time = datetime.strptime(f"{hour}", "%H")
        formatted_time = time.strftime("%I:%M %p")
        total = PacketTotals(seq=hour,
            name=formatted_time,
            total=hourly_sums[hour],
            max=hourly_max[hour],
            min=hourly_min[hour],
            count=hourly_count[hour],
            aveint=int(hourly_ave[hour]),
            ave=hourly_ave[hour])
        totals.append(total)

    # sorted_totals = sorted(totals, key=lambda totals: (totals.key,totals.total))
    # return sorted_totals
    return totals



@router.get("/packet_permonth/{dev_eui}/{measurement}/{year}",
        response_model=list[PacketTotals],
        tags=['Packet API'])
async def get_packets_months(dev_eui: str,
        measure: str,
        year: int,
        current_user: Annotated[User, Depends(get_current_user)]):
    """
    This returns a list of packet(s) for a device and measurement for a given year\n
    summarized per month (average, min, max, count)\n
    Path Parameters:\n
    dev_eui   - The Device EUI\n
    measurement - the speific measurement (temperature, pm2_5, humidity)\n
    year   - YY\n
    """

    logger.info(f"Finding packet with eui {dev_eui}")
    # logger.info(packet_query)

    if year < 10 or year > 99:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Enter a two digit year please")


    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current user has undefined role")

    dev = await find_device_by_deveui(dev_eui)
    if dev:
        # check if device belong to this user of public
        if (role.name != 'Admin') and (dev.user_id != current_user.id):
            if (dev.domain != 'Public'):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User is not allowed to view data from this device.")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="A device with that deveui was not found")

    devtype = await find_type_by_id(dev.type_id)
    if devtype is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that type_id was not found",
        )

    ctr = 1
    devtypedetail = await find_typedetail_by_type_id(dev.type_id, current_user)
    for dtl in devtypedetail:
        measurement = await find_measurement_by_id(dtl.measurement_id)
        if measurement:
            if (measurement.name==measure):
                ctr = 0

    retjson = []
    if ctr == 0:
        ctr = 1
        for month in range(1, 13):
            yearmonth = f"{year:02}" + f"{month:02}"
            sql_tx = "SELECT * FROM device_data WHERE dev_eui = '"
            sql_tx = sql_tx + dev_eui + "' "
            sql_tx = sql_tx + "AND measurement = '" + measure + "' "
            sql_tx = sql_tx + "AND yearmonth = "
            sql_tx = sql_tx + yearmonth + " "
            #logger.info(sql_tx)
            rows = session.execute(sql_tx)
            if rows.current_rows:
                # retjson = rows.current_rows
                if ctr == 1:
                    retjson = rows.current_rows
                    ctr = 0
                else:
                    retjson.append(rows.current_rows[0])
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Measurement not found")

    monthly_sums = defaultdict(int)
    monthly_count = defaultdict(int)
    monthly_max = defaultdict(int)
    monthly_min = defaultdict(int)
    monthly_ave = defaultdict(int)

    for hour in range(1, 13):
        monthly_sums[hour] = 0
        monthly_count[hour] = 0
        monthly_max[hour] = 0
        monthly_min[hour] = 0
        monthly_ave[hour] = 0

    for pkt in retjson:
        # if pkt["value"] != 0:
        month = pkt["ts"].month
        monthly_sums[month] += pkt["value"]
        monthly_count[month] += 1
        if monthly_max[month] < pkt["value"]:
            monthly_max[month] = pkt["value"]
        if monthly_count[month] > 0:
            monthly_ave[month] = monthly_sums[month] / monthly_count[month]
        if monthly_count[month] == 0:
            monthly_min[month] = pkt["value"]
        else:
            if monthly_min[month] > pkt["value"]:
                monthly_min[month] = pkt["value"]

    # print(daily_sums)
    totals = []
    for month in range(1, 13):
        time = datetime(year, month, 1)
        formatted_time = time.strftime('%y-%m')
        total = PacketTotals(seq=month,
            name=formatted_time,
            total=monthly_sums[month],
            max=monthly_max[month],
            min=monthly_min[month],
            count=monthly_count[month],
            aveint=int(monthly_ave[month]),
            ave=monthly_ave[month])
        totals.append(total)

    # sorted_totals = sorted(totals, key=lambda totals: (totals.key,totals.total))
    # return sorted_totals
    return totals



@router.get("/latest_packet2/{dev_eui}",
        response_model=list[LatestPacketUnit],
        tags=['Packet API'])
async def get_latest_packet2(dev_eui: str,
        current_user: Annotated[User, Depends(get_current_user)]):
    """
    This returns a list of packets within a starting date until an end date.
    The difference from letest_packet is that this does not look at the device
    definition for the measurements.  It looks for hard coded measurements.
    Path Parameters:\n
    dev_eui   - The Device EUI\n
    fromdate - Starting Date YYYY-MM-DD format\n
    todate - Ending Date YYYY-MM-DD format
    """

    thin_yn = False

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current user has undefined role")

    if (role.name != 'Admin'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only admins can use this API.")

    retjson = []

    #units = await get_all_units(current_user)

    measures = ["battery",
                "co2",
                "distance_m",
                "energy", 
                "humidity",
                "hcho",
                "in",
                "light_level",
                "pm1",
                "pm2_5",
                "pm10",
                "psi",
                "state",
                "temperature",
                "tvoc",
                "voltage_L1",
                "volume"]

    for measure in measures:
        sql_tx = "SELECT * FROM latest_data WHERE dev_eui = "
        sql_tx = sql_tx + " '" + dev_eui + "' "
        sql_tx = sql_tx + "AND measurement = '" + measure + "' "

        unit_nm = measure
        measurement = await find_measurement_by_name(measure)
        if measurement:
            unit = await find_unit_by_id(measurement.unit_id)
            if unit:
                unit_nm = unit.name

        rows = session.execute(sql_tx)
        if rows.current_rows:
            tstmp = rows.current_rows[0]['ts'].strftime('%Y-%m-%d %H:%M')
            latestpacket = LatestPacketUnit(dev_eui=dev_eui,
                measurement=measure,
                unit=unit_nm,
                value=rows.current_rows[0]['value'],
                source_application_id=tstmp,
                ts=rows.current_rows[0]['ts'])

            retjson.append(latestpacket)

    return retjson


@router.get("/latest_packet3/{dev_eui}",
        response_model=list[LatestPacketUnit],
        tags=['Packet API'])
async def get_latest_packet3(dev_eui: str,
        current_user: Annotated[User, Depends(get_current_user)]):
    """
    This returns a list of packets within a starting date until an end date.
    The difference from letest_packet is that this does not look at the device
    definition for the measurements.  This gets the measurements from the packets received.
    Path Parameters:\n
    dev_eui   - The Device EUI\n
    fromdate - Starting Date YYYY-MM-DD format\n
    todate - Ending Date YYYY-MM-DD format
    """

    thin_yn = False

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current user has undefined role")

    if (role.name != 'Admin'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only admins can use this API.")

    retjson = []

    measures = await get_all_measurements(current_user)

    for measure in measures:
        sql_tx = "SELECT * FROM latest_data WHERE dev_eui = "
        sql_tx = sql_tx + " '" + dev_eui + "' "
        sql_tx = sql_tx + "AND measurement = '" + measure.name + "' "

        unit = await find_unit_by_id(measure.unit_id)
        unit_nm = measure.name
        if unit:
            unit_nm = unit.name

        rows = session.execute(sql_tx)
        if rows.current_rows:
            tstmp = rows.current_rows[0]['ts'].strftime('%Y-%m-%d %H:%M')
            latestpacket = LatestPacketUnit(dev_eui=dev_eui,
                measurement=measure.name,
                unit=unit_nm,
                value=rows.current_rows[0]['value'],
                source_application_id=tstmp,
                ts=rows.current_rows[0]['ts'])

            retjson.append(latestpacket)

    return retjson


@router.post("/aggregator/{period_cd}",
        tags=['Packet API'])
async def aggregator(period_cd: str,
        current_user: Annotated[User, Depends(get_current_user)]):

    retjson = []

    return retjson




@router.get("/packet_days2/{dev_eui}/{measurement}/{numdays}",
        # response_model=list[Union[LatestPacket, PacketTotals, ThinPacket]],
        tags=['Packet API'])
async def get_packets_dates_lastdays2(dev_eui: str,
        measure: str,
        numdays: int,
        current_user: Annotated[User, Depends(get_current_user)]):
    """
    This returns a list of packets the last number of days summarized per day.  
    The differece of this from packet_days is that this gets from the summarized daily table
    instead of processing the raw packets
    Path Parameters:\n
    dev_eui   - The Device EUI\n
    measurement - the speific measurement (temperature, pm2_5, humidity)\n
    numdays  - number of days\n
    """

    logger.info(f"Finding packet with eui {dev_eui}")
    # logger.info(packet_query)

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current user has undefined role")

    dev = await find_device_by_deveui(dev_eui)
    if dev:
        # check if device belong to this user of public
        if (role.name != 'Admin') and (dev.user_id != current_user.id):
            if (dev.domain != 'Public'):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User is not allowed to view data from this device.")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="A device with that deveui was not found")

    devtype = await find_type_by_id(dev.type_id)
    if devtype is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that type_id was not found",
        )

    devtypedetail = await find_typedetail_by_type_id(dev.type_id, current_user)
    if devtypedetail is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A typedetail with that type_id was not found",
        )

    retjson = []
    ctr = 1
    todate = datetime.now()
    yearmonth = todate.strftime('%y%m')
    fromdate = todate - timedelta(days=numdays)
    for dtl in devtypedetail:
        measurement = await find_measurement_by_id(dtl.measurement_id)

        if measurement:
            if (measurement.name==measure):

                today = date.today()
                if numdays == 1:
                    sql_tx = "SELECT * FROM device_data WHERE dev_eui = '"
                    sql_tx = sql_tx + dev_eui + "' "
                    sql_tx = sql_tx + "AND measurement = '" + measurement.name + "' "
                    sql_tx = sql_tx + "AND yearmonth = "
                    sql_tx = sql_tx + str(yearmonth) + " "
                    sql_tx = sql_tx + "AND ts >= '"
                    sql_tx = sql_tx + fromdate.strftime("%Y-%m-%d %H:%M:%S") + "' "
                    sql_tx = sql_tx + "AND ts <= '"
                    sql_tx = sql_tx + todate.strftime("%Y-%m-%d %H:%M:%S") + "' ORDER BY ts "
                    sql_tx = sql_tx + "ALLOW FILTERING; "
                    #logger.info(sql_tx)
                    rows = session.execute(sql_tx)
                    if rows.current_rows:
                        for pkt in rows.current_rows:
                            tstmp = pkt['ts'].strftime('%Y-%m-%d %H:%M')
                            if measure=="pm2_5":
                                newmeasurement = measure.replace("_", ".")
                            else:
                                newmeasurement = measure
                            latestpacket = LatestPacket(dev_eui=dev_eui,
                                measurement=newmeasurement,
                                value=pkt['value'],
                                source_application_id=tstmp,
                                ts=pkt['ts'])

                            retjson.append(latestpacket)
                else:
                    daily_ave = defaultdict(int)
                    daily_date = defaultdict(str)

                    current_date = fromdate
                    day_key = 0
                    while current_date < todate:
                        day_key = day_key + 1
                        daily_date[day_key] = current_date.strftime('%Y-%m-%d')
                        daily_ave[day_key] = 0
                        current_date += timedelta(days=1)

                    firstdoy = fromdate.timetuple().tm_yday
                    fryear = fromdate.year % 100
                    toyear = todate.year % 100
                    lastdoy = todate.timetuple().tm_yday
                    fryearday = fryear * 1000 + firstdoy
                    toyearday = toyear * 1000 + lastdoy

                    sql_tx = "SELECT yearday, ave FROM daily_data "
                    sql_tx = sql_tx + " WHERE yearday >= " + str(fryearday)
                    sql_tx = sql_tx + " AND yearday <= " + str(toyearday)
                    sql_tx = sql_tx + " AND dev_eui = '" + dev_eui + "' "
                    sql_tx = sql_tx + " AND measurement = '" +  measurement.name + "' "
                    sql_tx = sql_tx + " ALLOW FILTERING; "
                    rows = session.execute(sql_tx)
                    logger.info(sql_tx)
                    # return rows.current_rows

                    if rows.current_rows:
                        sorted_rows = sorted(rows.current_rows, key=lambda x: (x["yearday"]))
                        # Convert to dict of dicts (using id as key)
                        row_by_yearday = {row['yearday']: row for row in sorted_rows}
                        
                        current_date = fromdate
                        day_key = 0
                        while current_date < todate:
                            day_key = day_key + 1
                            firstdoy = current_date.timetuple().tm_yday
                            curryear = current_date.year % 100
                            curryearday = curryear * 1000 + firstdoy
                            curr = row_by_yearday.get(curryearday)
                            if curr is not None:
                                daily_ave[day_key] = curr["ave"]
                            current_date += timedelta(days=1)

                    ctr = 1
                    if measure=="pm2_5":
                        newmeasurement = measure.replace("_", ".")
                    else:
                        newmeasurement = measure

                    for key in daily_ave:
                        total = LatestPacket(dev_eui=dev_eui,
                            measurement=newmeasurement,
                            value=daily_ave[key],
                            source_application_id=daily_date[key],
                            ts=daily_date[key])
                        ctr += 1
                        retjson.append(total)

        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Measurement ID not found")

    if retjson == []:
        totals = []
        dayname = datetime.strftime(datetime.now(), '%Y-%m-%d')
        total = ThinPacket(ts=dayname, value=0)
        totals.append(total)
        return totals

    return retjson




@router.get("/packet_permonth2/{dev_eui}/{measurement}/{year}",
        response_model=list[PacketTotals],
        tags=['Packet API'])
async def get_packets_months2(dev_eui: str,
        measure: str,
        year: int,
        current_user: Annotated[User, Depends(get_current_user)]):
    """
    This returns a list of summarized packets per month for a given year.
    The differece of this from packet_month is that this gets from the summarized monthly table
    instead of processing the raw packets
    Path Parameters:\n
    dev_eui   - The Device EUI\n
    measurement - the speific measurement (temperature, pm2_5, humidity)\n
    year  - YY\n
    """


    logger.info(f"Finding packet with eui {dev_eui}")
    # logger.info(packet_query)

    if year < 10 or year > 99:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Enter a two digit year please")


    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current user has undefined role")

    dev = await find_device_by_deveui(dev_eui)
    if dev:
        # check if device belong to this user of public
        if (role.name != 'Admin') and (dev.user_id != current_user.id):
            if (dev.domain != 'Public'):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User is not allowed to view data from this device.")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="A device with that deveui was not found")

    devtype = await find_type_by_id(dev.type_id)
    if devtype is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that type_id was not found",
        )

    ctr = 1
    devtypedetail = await find_typedetail_by_type_id(dev.type_id, current_user)
    for dtl in devtypedetail:
        measurement = await find_measurement_by_id(dtl.measurement_id)
        if measurement:
            if (measurement.name==measure):
                ctr = 0

    retjson = []
    if ctr == 0:
        fryearmonth = f"{year:02}" + "01"
        toyearmonth = f"{year:02}" + "12"

        sql_tx = "SELECT * FROM monthly_data WHERE dev_eui = '"
        sql_tx = sql_tx + dev_eui + "' "
        sql_tx = sql_tx + "AND measurement = '" + measure + "' "
        sql_tx = sql_tx + "AND yearmonth >= " + fryearmonth + " "
        sql_tx = sql_tx + "AND yearmonth <= " + toyearmonth + " "
        sql_tx = sql_tx + "ALLOW FILTERING; "
        #logger.info(sql_tx)
        rows = session.execute(sql_tx)
        if rows.current_rows:
            logger.info("jackpot")
            retjson = sorted(rows.current_rows, key=lambda x: (x["yearmonth"]))
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Measurement not found")

    monthly_sums = defaultdict(int)
    monthly_count = defaultdict(int)
    monthly_max = defaultdict(int)
    monthly_min = defaultdict(int)
    monthly_ave = defaultdict(int)

    for hour in range(1, 13):
        monthly_sums[hour] = 0
        monthly_count[hour] = 0
        monthly_max[hour] = 0
        monthly_min[hour] = 0
        monthly_ave[hour] = 0

    for month in range(1, 13):
        fryearmonth = int(f"{year:02}" + f"{month:02}")
        for row in retjson:
            # logger.info("frym:  " + str(fryearmonth) + " - " +  str(row["yearmonth"]))
            if row["yearmonth"] == fryearmonth:
                logger.info("matched")
                monthly_sums[month] = row["sum"]
                monthly_count[month] = row["count"]
                monthly_max[month] = row["max"]
                monthly_ave[month] =row["ave"]
                monthly_min[month] = row["min"]


    logger.info("creating totals")
    # print(daily_sums)
    totals = []
    for month in range(1, 13):
        time = datetime(year, month, 1)
        formatted_time = time.strftime('%y-%m')
        total = PacketTotals(seq=month,
            name=formatted_time,
            total=monthly_sums[month],
            max=monthly_max[month],
            min=monthly_min[month],
            count=monthly_count[month],
            aveint=int(monthly_ave[month]),
            ave=monthly_ave[month])
        totals.append(total)

    # sorted_totals = sorted(totals, key=lambda totals: (totals.key,totals.total))
    # return sorted_totals
    return totals



@router.get("/packet_perhour2/{dev_eui}/{measurement}/{date}",
        response_model=list[PacketTotals],
        tags=['Packet API'])
async def get_packets_hours2(dev_eui: str,
        measure: str,
        datestr: str,
        current_user: Annotated[User, Depends(get_current_user)]):
    """
    This returns a list of summarized packets per hour for a given date.
    The differece of this from packet_perhour is that this gets from the summarized hourly table
    instead of processing the raw packets
    Path Parameters:\n
    dev_eui   - The Device EUI\n
    measurement - the speific measurement (temperature, pm2_5, humidity)\n
    date  - YYYY-MM-DD\n
    """

    logger.info(f"Get packets per per hour for eui {dev_eui}")
    # logger.info(packet_query)
    dev_eui = dev_eui.strip()
    datestr = datestr.strip()
    measure = measure.strip()

    try:
        pktdate = datetime.strptime(datestr, "%m/%d/%Y")
        # Adjust format as needed
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format")

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current user has undefined role")

    dev = await find_device_by_deveui(dev_eui)
    if dev:
        # check if device belong to this user of public
        if (role.name != 'Admin') and (dev.user_id != current_user.id):
            if (dev.domain != 'Public'):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User is not allowed to view data from this device.")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="A device with that deveui was not found")

    devtype = await find_type_by_id(dev.type_id)
    if devtype is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that type_id was not found",
        )

    retjson = []
    ctr = 1
    day = pktdate.timetuple().tm_yday
    year = pktdate.year % 100
    wholeyear = pktdate.year
    month = pktdate.month
    yearday = year * 1000 + day
    yearmonth = year * 100 + month

    devtypedetail = await find_typedetail_by_type_id(dev.type_id, current_user)
    for dtl in devtypedetail:
        measurement = await find_measurement_by_id(dtl.measurement_id)
        if measurement:
            if (measurement.name==measure):
                ctr = 0

    if ctr == 0:
        sql_tx = "SELECT * FROM hourly_data WHERE dev_eui = '"
        sql_tx = sql_tx + dev_eui + "' "
        sql_tx = sql_tx + "AND measurement = '" + measure + "' "
        sql_tx = sql_tx + "AND yearday = " + str(yearday) + " "
        sql_tx = sql_tx + "ALLOW FILTERING; "
        #logger.info(sql_tx)
        rows = session.execute(sql_tx)
        if rows.current_rows:
            retjson = sorted(rows.current_rows, key=lambda x: (x["hour"]))
            retjson = rows.current_rows
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Measurement not found")

    hourly_sums = defaultdict(int)
    hourly_count = defaultdict(int)
    hourly_max = defaultdict(int)
    hourly_min = defaultdict(int)
    hourly_ave = defaultdict(int)

    for hour in range(24):
        hourly_sums[hour] = 0
        hourly_count[hour] = 0
        hourly_max[hour] = 0
        hourly_min[hour] = 0
        hourly_ave[hour] = 0

    for hour in range(24):
        for row in retjson:
            if row["hour"] == hour:
                hourly_sums[hour] = row["sum"]
                hourly_count[hour] = row["count"]
                hourly_max[hour] = row["max"]
                hourly_ave[hour] = row["ave"]
                hourly_min[hour] = row["min"]

    # print(daily_sums)
    totals = []
    for hour in range(24):
        time = datetime.strptime(f"{hour}", "%H")
        formatted_time = time.strftime("%I:%M %p")
        total = PacketTotals(seq=hour,
            name=formatted_time,
            total=hourly_sums[hour],
            max=hourly_max[hour],
            min=hourly_min[hour],
            count=hourly_count[hour],
            aveint=int(hourly_ave[hour]),
            ave=hourly_ave[hour])
        totals.append(total)

    # sorted_totals = sorted(totals, key=lambda totals: (totals.key,totals.total))
    # return sorted_totals
    return totals


@router.get("/packet_perweek2/{dev_eui}/{measurement}/{year}",
        response_model=list[PacketTotals],
        tags=['Packet API'])
async def get_packets_weeks2(dev_eui: str,
        measure: str,
        year: int,
        current_user: Annotated[User, Depends(get_current_user)]):
    """
    This returns a list of summarized packets per week for a given year.
    This gets from the weekly summarized table  instead of processing the raw packets
    Path Parameters:\n
    dev_eui   - The Device EUI\n
    measurement - the speific measurement (temperature, pm2_5, humidity)\n
    year  - YY\n
    """

    logger.info(f"Finding packet with eui {dev_eui}")
    # logger.info(packet_query)

    if year < 10 or year > 99:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Enter a two digit year please")


    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current user has undefined role")

    dev = await find_device_by_deveui(dev_eui)
    if dev:
        # check if device belong to this user of public
        if (role.name != 'Admin') and (dev.user_id != current_user.id):
            if (dev.domain != 'Public'):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User is not allowed to view data from this device.")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="A device with that deveui was not found")

    devtype = await find_type_by_id(dev.type_id)
    if devtype is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that type_id was not found",
        )

    ctr = 1
    devtypedetail = await find_typedetail_by_type_id(dev.type_id, current_user)
    for dtl in devtypedetail:
        measurement = await find_measurement_by_id(dtl.measurement_id)
        if measurement:
            if (measurement.name==measure):
                ctr = 0

    retjson = []
    if ctr == 0:
        fryearweek = f"{year:02}" + "01"
        toyearweek = f"{year:02}" + "52"

        sql_tx = "SELECT * FROM weekly_data WHERE dev_eui = '"
        sql_tx = sql_tx + dev_eui + "' "
        sql_tx = sql_tx + "AND measurement = '" + measure + "' "
        sql_tx = sql_tx + "AND yearweek >= " + fryearweek + " "
        sql_tx = sql_tx + "AND yearweek <= " + toyearweek + " "
        sql_tx = sql_tx + "ALLOW FILTERING; "
        #logger.info(sql_tx)
        rows = session.execute(sql_tx)
        if rows.current_rows:
            retjson = sorted(rows.current_rows, key=lambda x: (x["yearweek"]))
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail="Measurement not found")

    weekly_sums = defaultdict(int)
    weekly_count = defaultdict(int)
    weekly_max = defaultdict(int)
    weekly_min = defaultdict(int)
    weekly_ave = defaultdict(int)

    for week in range(1, 53):
        weekly_sums[week] = 0
        weekly_count[week] = 0
        weekly_max[week] = 0
        weekly_min[week] = 0
        weekly_ave[week] = 0

    for week in range(1, 53):
        fryearweek = int(f"{year:02}" + f"{week:02}")
        for row in retjson:
            if row["yearweek"] == fryearweek:
                weekly_sums[week] = row["sum"]
                weekly_count[week] = row["count"]
                weekly_max[week] = row["max"]
                weekly_ave[week] =row["ave"]
                weekly_min[week] = row["min"]


    # print(daily_sums)
    totals = []
    # fdoy = datetime(year, 1, 1)
    for week in range(1, 53):
        # time = fdoy + timedelta(weeks=week-1, days=-fdoy.weekday(), days=day_of_week-1)
        # time = datetime(year, week, 1)
        formatted_time = f"{year:02}" + f"{week:02}"
        # formatted_time = time.strftime('%y-%m')
        total = PacketTotals(seq=week,
            name=formatted_time,
            total=weekly_sums[week],
            max=weekly_max[week],
            min=weekly_min[week],
            count=weekly_count[week],
            aveint=int(weekly_ave[week]),
            ave=weekly_ave[week])
        totals.append(total)

    # sorted_totals = sorted(totals, key=lambda totals: (totals.key,totals.total))
    # return sorted_totals
    return totals


