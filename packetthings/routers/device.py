import logging
import sqlalchemy

import qrcode
import io
from starlette.responses import StreamingResponse

from enum import Enum
from typing import Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Response

from packetthings.database import database, device_table, mydevice_table, devsumm_table
from packetthings.dbpg import get_db_connection
from packetthings.dbscylla import get_session
from packetthings.models.device import (
    Device,
    DeviceSumm,
    FullDevice,
    DeviceUpdate,
    DeviceIn,
    DeviceOut,
    DeviceReg,
    DeviceRegToken,
    DeviceToken,
    DeviceDistance,
    TypeDetails,
    LatLong
)
from packetthings.models.user import User, SuccessMessage
from packetthings.models.packet import (
        Packet, 
        LatestPacket, 
        PacketQuery, 
        PacketQueryDates)
from packetthings.routers.location import find_location_by_id
from packetthings.routers.type import (
        find_type_by_id, 
        find_typedetail_by_type_id, 
        find_type_by_name
)
from packetthings.routers.role import find_role_by_id
from packetthings.routers.user import find_users_by_email
from packetthings.routers.measurement import find_measurement_by_id
# from packetthings.routers.packet import get_latest_packet2
from packetthings.security import (
        get_current_user, 
        create_deviceregister_token, 
        get_subject_for_token_type)

router = APIRouter()
logger = logging.getLogger(__name__)
session = get_session()


async def find_device_by_deveui(dev_eui: str):
    logger.info(f"Finding device with eui {dev_eui}")
    dev_eui = dev_eui.strip()
    query = device_table.select().where(device_table.c.dev_eui == dev_eui)
    #logger.debug(query)
    # dev = await database.fetch_one(query)
    # logger.debug(dev)
    # return dev
    return await database.fetch_one(query)


async def find_device_by_id(device_id: int):
    logger.info(f"Finding device with id {device_id}")
    query = device_table.select().where(device_table.c.id == device_id)
    #logger.debug(query)
    return await database.fetch_one(query)


async def find_device_by_location_id(location_id: int, user_id: int, role_nm: str):
    logger.info(f"Finding devices with location_id {location_id}")
    location = await find_location_by_id(location_id)
    if not location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location does not exist. " 
        )

    if role_nm != 'Admin':
        if location.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Location belongs to another user. " ,
            )

    query = device_table.select().where(device_table.c.location_id == location_id)
    #logger.debug(query)
    return await database.fetch_all(query)


async def find_device_by_type_id(type_id: int, user_id: int, role_nm: str):
    logger.info(f"Finding devices with type_id {type_id}")

    type = await find_type_by_id(device.type_id)
    type_nm = "Unknown"
    if type:
        type_nm = type.name
        inactivity = type.inactivity
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device type not found" ,
        )

    query = device_table.select().where(device_table.c.type_id == type_id)
    #logger.debug(query)
    return await database.fetch_all(query)


@router.get("/device", 
        response_model=list[Device], 
        tags=['Device API'])
async def get_all_devices(current_user: Annotated[User, Depends(get_current_user)]):
    """
    This returns a list of all devices registered under the logged in user.
    """

    logger.info("Getting all devices")
    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Current user has undefined role")

    if role.name != 'Admin':
        query = device_table.select().where(
                    device_table.c.user_id==current_user.id
                ).order_by(device_table.c.id)
    else:
        query = device_table.select().where().order_by(device_table.c.id)
 
    #logger.debug(query)
    return await database.fetch_all(query)


@router.get("/device_user/{email}",
        response_model=list[FullDevice],
        tags=['Device API'],
        description="This API returns all the devices registered under your user id")
async def get_all_devices_by_user(email: str, current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Getting all devices for a user")
    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Current user has undefined role")

    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only admins can user this API")

    
    user = await find_users_by_email(email)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    query = device_table.select().where(
            device_table.c.user_id==user.id
        ).order_by(device_table.c.id)
 
    retdevs = []
    #logger.debug(query)
    devs = await database.fetch_all(query)
    if devs:
        for dtl in devs:
            fdev = await get_fulldevice_with_deveui(dtl.dev_eui, current_user)
            if fdev:
                retdevs.append(fdev)

    return retdevs


# @router.get("/device/{dev_eui}", response_model=list[Device], tags=['Device API'])
# async def get_device_with_deveui(dev_eui: str):
#     logger.info(f"Getting device with dev_eui {dev_eui}")
#     device = await find_device_by_deveui(dev_eui)
#     if not device:
#         raise HTTPException(status_code=404, detail="Device not found")
#     return device


@router.get("/device/{dev_eui}", 
        response_model=FullDevice, 
        tags=['Device API'],
        description="This API returens a device with deveui with full details")
async def get_fulldevice_with_deveui(dev_eui: str, 
        current_user: Annotated[User, Depends(get_current_user)]):

    # from packetthings.routers.packet import get_latest_packet2

    logger.info(f"Getting device with dev_eui {dev_eui}")

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Current user has undefined role")

    dev_eui = dev_eui.strip()

    device = await find_device_by_deveui(dev_eui)
    if not device:
        raise HTTPException(status_code=400, detail="Device not found")

    if role.name != 'Admin':
        if device.user_id != 0 and device.user_id != current_user.id:
            if device.domain != 'Public':
                raise HTTPException(status_code=400, detail="This Device belongs to another user")

    type = await find_type_by_id(device.type_id)
    type_nm = "Unknown"
    if type:
        type_nm = type.name
        inactivity = type.inactivity

    typedtls = await find_typedetail_by_type_id(device.type_id) 
    dtls = []

    last_date = datetime.now()
    #latest_packets = await get_latest_packet2(device.dev_eui, current_user)
    #if latest_packets:
    #    for lastpack in latest_packets:
    #        try:
    #            # 2024-10-31T09:37:44
    #            last_date = datetime.now()
    #            # last_date = datetime.strptime(lastpacket.ts, "%Y-%m-%dT%H:%M:%S")
    #        except:
    #            continue
    ctr = 1

    if typedtls:
        for dtl_data in typedtls:
            if dtl_data.name != "pm10":
                measurement = await find_measurement_by_id(dtl_data.measurement_id)
                measurement_nm = "None" 
                if measurement:
                    measurement_nm = measurement.name
    
                    sql_tx = "SELECT * FROM latest_data WHERE dev_eui = '"
                    sql_tx = sql_tx + device.dev_eui + "' "
                    sql_tx = sql_tx + "AND measurement = '" + measurement.name + "' "
                    rows = session.execute(sql_tx)
                    if rows.current_rows:
                        for pktrow in rows.current_rows:
                            if ctr == 1:
                                ctr = 0 
                                last_date = pktrow["ts"]
                            else:
                                if last_date < pktrow["ts"]:
                                    last_date = pktrow["ts"]

                dtl = TypeDetails(id=dtl_data.id,
                        name=dtl_data.name,
                        description=dtl_data.description,
                        measurement_id=dtl_data.measurement_id,
                        measurement_nm=measurement_nm)
                dtls.append(dtl)

    location_nm = ""
    group_nm = ""
    group_id = 0
    location = await find_location_by_id(device.location_id)
    if location:
        location_nm = location.name
        group = await find_location_by_id(location.location_id)
        if group:
            group_nm = group.name
            group_id = group.id

    # packet = await get_latest_packet()
    time_difference = datetime.now() - last_date

    # Convert the difference to hours
    hours_difference = time_difference.total_seconds() / 3600

    status = "active"
    if inactivity > 0:
        if hours_difference > inactivity:
            status = "inactive"

    lastdate = last_date.strftime('%Y-%m-%d %H:%M')
    fulldevice = FullDevice(name=device.name, 
            dev_eui=device.dev_eui, 
            latitude=device.latitude,
            longitude=device.longitude,
            location_id=device.location_id,
            location_nm=location_nm,
            group_id=group_id,
            group_nm=group_nm,
            type_id=device.type_id,
            type_nm=type_nm,
            description=device.description,
            user_id=device.user_id,
            user_nm=current_user.name,
            domain=device.domain,
            lastactive=lastdate,
            status=status,
            typedtls=dtls)

    return fulldevice



@router.post("/device/register", 
        response_model=SuccessMessage, 
        status_code=201, tags=['Device API'])
async def register_deveui(device: DeviceReg, 
        current_user: Annotated[User, Depends(get_current_user)]):
    logger.info(f"Finding device with eui {device.dev_eui}")

    # check if private, if private then just assign user_id
    # if public then insert into mydevices
    dev_eui = device.dev_eui.strip()
    logger.debug(dev_eui)

    device2 = await find_device_by_deveui(dev_eui)
    if not device2:
        raise HTTPException(status_code=400, detail="Device with that EUI was not found")

    if device2.domain == 'Public':
        raise HTTPException(status_code=400, detail="Device is in the public domain.")

    # check if device is already owned by another user
    if device2.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You already own this device.")
    else:
        if device2.user_id != 1 and device2.user_id != 99 and device2.user_id != 0: 
            raise HTTPException(status_code=400, detail="Device is owned by another user.")

    loc = 1
    if device.location_id:
        if device.location_id !=0:
            location = await find_location_by_id(device.location_id)
            if not location:
                raise HTTPException(status_code=400, detail="Location was not found")

            if location.user_id != current_user.id:
                raise HTTPException(status_code=400, detail="Location belongs to another user")

            loc = device.location_id
    
    lat = 0
    lon = 0

    if loc == 0:
        loc = 1

    if device.longitude:
        lon = device.longitude

    if device.latitude:
        lat = device.latitude

    desc = ""
    if device.description:
        desc = device.description


    newdate = datetime.now()
    query = device_table.update().where(device_table.c.dev_eui == device.dev_eui).values(
            user_id=current_user.id, 
            name=device.name, 
            longitude=lon, 
            latitude=lat,
            description=desc, 
            updated=newdate, 
            location_id=loc)

    #logger.debug(query)
    last_record_id = await database.execute(query)

    newdate = datetime.now()
    query = mydevice_table.insert().values(
            device_id=device2.id,
            user_id=current_user.id,
			dev_eui=device.dev_eui,
            description=device.description,
            created=newdate,
            updated=newdate
        )
    #logger.debug(query)
    last_record_id = await database.execute(query)

    return {'success': True, 
            'status_code': status.HTTP_200_OK, 
            'message': 'Device Registration Successful!'}


@router.post("/device", response_model=DeviceOut, 
        status_code=201, 
        tags=['Device API'])
async def add_device(device: DeviceIn, 
        current_user: Annotated[User, Depends(get_current_user)]):
    logger.debug("Adding new device.")

    dev_eui = device.dev_eui.strip()
    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Current user has undefined role")

    dev_name = device.name.strip()
    if dev_name=="":
        raise HTTPException(status_code=400, detail="Device name cannot be blank")

    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can add devies")

    dev2 = await find_device_by_deveui(dev_eui)
    if dev2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A device with that EUI already exists",
        )

    #check type_id 
    type = await find_type_by_id(device.type_id)
    if not type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Type does not exist.",
        )

    # check location_id
    user_id = 0
    if device.location_id and device.location_id != 0:
        location = await find_location_by_id(device.location_id)
        if not location:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Location does not exist. " + str(device.location_id),
            )
        loc = device.location_id
        user_id = location.user_id
    else:
        loc = 1
        user_id = 0

    # check current_user.
    role = await find_role_by_id(current_user.role_id)
    if role:
        # is admin or only a reg user
        if role.name != 'Admin':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only admins can add devices.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user role.",
        )


    if device.user_id != 1 and device.user_id != 99 and device.user_id != 0:
        if user_id > 0:
            if user_id != device.user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Device user_id is not the same user as the location user.",
                )

    domain = device.domain
    if domain != "Public" and domain != "Private":
        domain = "Private"


    devtoken = create_deviceregister_token(dev_eui)
    newdate = datetime.now()
    logger.debug("dt: " + devtoken)
    query = device_table.insert().values(
            name=device.name,
            dev_eui=dev_eui,
            longitude=device.longitude,
            latitude=device.latitude,
            location_id=loc,
            type_id=device.type_id,
            description=device.description,
            user_id=device.user_id,
            domain=domain,
            created=newdate,
            updated=newdate
        )
    #logger.debug(query)
    last_record_id = await database.execute(query)
    data = {**device.model_dump()}
    return {**data, "id": last_record_id, "token": devtoken}


@router.get("/nearme/{dist}/{lat}/{lon}", 
        response_model=list[DeviceDistance], status_code=201, tags=['Device API'])
async def nearby_devices(dist: float, lat: float, lon: float, 
        current_user: Annotated[User, Depends(get_current_user)]):

    logger.debug(F"Finding devices nearme. {dist} -- {lon} -- {lat}")

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Current user has undefined role")

    query = "SELECT *,  (ST_Distance( "
    query = query + " ST_SetSRID(ST_MakePoint(" + str(lon) + ", " + str(lat)
    query = query + "), 4326)::geography, "
    query = query + " ST_SetSRID(ST_MakePoint(longitude,latitude), 4326)::geography "
    query = query + " ) / 1000) as dist "
    query = query + " FROM devices WHERE ("
    query = query + "(ST_Distance(ST_SetSRID(ST_MakePoint("+str(lon)+"," + str(lat)
    query = query + "), 4326)::geography, "
    query = query + " ST_SetSRID(ST_MakePoint(longitude,latitude), 4326)::geography "
    query = query + " ) / 1000) "
    query = query + " <= " + str(dist) + ") "
    if role.name != 'Admin':
        query = query + " AND ((domain = 'Public')"
        query = query + " OR (user_id = " + str(current_user.id) + "))"
    #logger.debug(query)
    devices = await database.fetch_all(query)
    retjson = []
    if devices:
        for dtl in devices:
            devdist = DeviceDistance(
                id=dtl.id,
                name=dtl.name,
                dev_eui=dtl.dev_eui,
                location_id=dtl.location_id,
                type_id=dtl.type_id,
                description=dtl.description,
                user_id=dtl.user_id,
                domain=dtl.domain,
                latitude=dtl.latitude,
                longitude=dtl.longitude,
                distance=dtl.dist)
            retjson.append(devdist)
    return retjson



@router.get("/nearmetype/{devtypename}/{dist}/{lat}/{lon}",
        response_model=list[DeviceDistance], status_code=201, tags=['Device API'])
async def nearby_devices_by_type(devtypename: str, dist: float, lat: float, lon: float,
        current_user: Annotated[User, Depends(get_current_user)]):

    logger.info(F"Finding devices nearme. (devtpye) -- {dist} -- {lon} -- {lat}")

    devtype = await find_type_by_name(devtypename)
    if not devtype:
        raise HTTPException(status_code=400, detail="Device type name not found")

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Current user has undefined role")

    query = "SELECT *,  (ST_Distance( "
    query = query + " ST_SetSRID(ST_MakePoint(" + str(lon) + ", " + str(lat) 
    query = query + "), 4326)::geography, "
    query = query + " ST_SetSRID(ST_MakePoint(longitude,latitude), 4326)::geography "
    query = query + " ) / 1000) as dist "
    query = query + " FROM devices WHERE ("
    query = query + "(ST_Distance(ST_SetSRID(ST_MakePoint("+str(lon)+"," + str(lat)
    query = query + "), 4326)::geography, "
    query = query + " ST_SetSRID(ST_MakePoint(longitude,latitude), 4326)::geography "
    query = query + " ) / 1000) "
    query = query + " <= " + str(dist) + ") "
    query = query + " AND (type_id = " + str(devtype.id) + ")"
    if role.name != 'Admin':
        query = query + " AND ((domain = 'Public')"
        query = query + " OR (user_id = " + str(current_user.id) + "))"
    #logger.debug(query)
    devices = await database.fetch_all(query)
    retjson = []
    if devices:
        for dtl in devices:
            devdist = DeviceDistance(
                id=dtl.id,
                name=dtl.name,
                dev_eui=dtl.dev_eui,
                location_id=dtl.location_id,
                type_id=dtl.type_id,
                description=dtl.description,
                user_id=dtl.user_id,
                domain=dtl.domain,
                latitude=dtl.latitude,
                longitude=dtl.longitude,
                distance=dtl.dist)
            retjson.append(devdist)
    return retjson



@router.get("/alldevices", response_model=list[Device], tags=['Device API'])
async def get_all_devices(current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Getting all devices registered to me.")
    query = device_table.select().where(
            device_table.c.user_id==current_user.id).order_by(device_table.c.id)
    #logger.debug(query)
    return await database.fetch_all(query)


@router.get("/device_by_id/{device_id}", response_model=Device, tags=['Device API'])
async def get_device_by_id(dev_id: int, 
        current_user: Annotated[User, Depends(get_current_user)]):

    logger.info(F"Finding devices with id: {dev_id}")

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Current user has undefined role")

    device = await find_device_by_id(dev_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device with that id was not found.",
        )

    if device.user_id != current_user.id and role.name != 'Admin':
        if device.domain != 'Public':
            raise HTTPException(status_code=400, detail="This Device belongs to another user")

    return device


@router.get("/device_by_location_id/{location_id}", 
        response_model=list[Device], 
        tags=['Device API'])
async def get_device_by_locationid(location_id: int, 
        current_user: Annotated[User, Depends(get_current_user)]):
    
    logger.info(F"Finding devices with location id: {location_id}")

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Current user has undefined role")

    devices = await find_device_by_location_id(location_id, current_user.id, role.name)
    if not devices:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device with that location id was not found.",
        )
    return devices


@router.delete("/device/{dev_eui}", response_model=Device, tags=['Device API'])
async def delete_device(dev_eui: str, 
        current_user: Annotated[User, Depends(get_current_user)]):

    dev_eui = dev_eui.strip()

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")
    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can delete devices")

    dev = await find_device_by_deveui(dev_eui)
    if not dev:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A unit with that ID was not found.",
        )

    query = (
        mydevice_table.delete().where(mydevice_table.c.device_id == dev.id)
    )
    #logger.debug(query)
    mydev = await database.execute(query)

    logger.info("Deleting device with dev_eui: {dev_eui}")
    query = (
        device_table.delete().where(device_table.c.id == dev.id)
    )
    #logger.debug(query)
    await database.execute(query)

    return dev 


@router.patch("/device", response_model=Device, tags=['Device API'])
async def update_device(device: DeviceUpdate,
        current_user: Annotated[User, Depends(get_current_user)]):

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    dev_eui = device.dev_eui.strip()
    dev2 = await find_device_by_deveui(dev_eui)
    if not dev2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A device with that EUI was not found.",
        )

    if role.name != 'Admin':
        if dev2.user_id != current_user.id:
            raise HTTPException(status_code=400, detail="Device is owned by another user.")


    logger.info(f"Updating device with eui: {device.dev_eui}")
    newdate = datetime.now()
    if role.name != 'Admin':
        query = (
            device_table.update().where(device_table.c.dev_eui == dev_eui).values(
                name=device.name,
                description=device.description,
                longitude=device.longitude,
                latitude=device.latitude,
                location_id=device.location_id,
                updated=newdate
            )
        )
    else:
        query = (
            device_table.update().where(device_table.c.dev_eui == dev_eui).values(
                name=device.name,
                description=device.description,
                longitude=device.longitude,
                latitude=device.latitude,
                type_id=device.type_id,
                location_id=device.location_id,
                updated=newdate
            )
        )

    #logger.debug(query)
    await database.execute(query)
    return await find_device_by_deveui(dev_eui)



@router.get("/devicetoken/{dev_eui}", status_code=201, tags=['Device API'])
async def get_devicetoken_with_deveui(dev_eui: str,
        current_user: Annotated[User, Depends(get_current_user)]):

    logger.info(f"Getting device with dev_eui {dev_eui}")
    dev_eui = dev_eui.strip()

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Current user has undefined role")

    if role.name != "Admin":
        raise HTTPException(status_code=400, detail="Only admins can get devtokens")

    device = await find_device_by_deveui(dev_eui)
    if not device:
        raise HTTPException(status_code=400, detail="Device not found")

    logger.info("Getting new device token")
    try:
        #logger.debug(current_user)
        devtoken = create_deviceregister_token(dev_eui)
        return {"devtoken": devtoken, "token_type": "device"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token",
        )


@router.post("/devicetoken", status_code=201, tags=['Device API'])
async def verifytoken(devtoken: DeviceToken, 
        current_user: Annotated[User, Depends(get_current_user)]):

    try:
        logger.debug("Verifying Device Token")

        dev_eui = get_subject_for_token_type(devtoken.token, "devicetoken")
        if dev_eui is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid device token",
            )
        return {'success': True, 
                'status_code': status.HTTP_200_OK, 
                'message': dev_eui}

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail="Some thing unexpected happened!")


#@router.post("/device2/regwithtoken",
#        response_model=SuccessMessage,
#        status_code=201, tags=['Device API'])
async def register_deveui_with_token2(device: DeviceRegToken,
        current_user: Annotated[User, Depends(get_current_user)]):
		
    try:
        logger.debug("Verifying Device Token")

        dev_eui = get_subject_for_token_type(devtoken.token, "devicetoken")
        if dev_eui is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid device token",
            )
        logger.debug("Verifying Device EUI: " + dev_eui)

        device2 = await find_device_by_deveui(dev_eui)
        if not device2:
	        raise HTTPException(status_code=400, detail="Device with that EUI was not found")

        if device2.domain == 'Public':
            raise HTTPException(status_code=400, detail="Device is in the public domain.")

		# check if device is already owned by another user
        if device2.user_id != 1 and device2.user_id != 99 and device2.user_id != 0:
	        raise HTTPException(status_code=400, detail="Device is owned by another user.")

        location = await find_location_by_id(device2.location_id)
        if not location:
            raise HTTPException(status_code=400, detail="Location was not found")

        if location.user_id != current_user.id:
            raise HTTPException(status_code=400, detail="Location belongs to another user")

        logger.debug("Registering to CurrrentUser")

        newdate = datetime.now()
        query = device_table.update().where(device_table.c.dev_eui == device2.dev_eui).values(
				user_id=current_user.id,
				updated=newdate)

        #logger.debug(query)
        await database.execute(query)

        logger.debug("Adding to MyDevices")

        newdate = datetime.now()
        query = mydevice_table.insert().values(
                device_id=device2.id,
                user_id=current_user.id,
                dev_eui=device2.dev_eui,
                description=device2.description,
                created=newdate,
                updated=newdate
            )
        #logger.debug(query)
        last_record_id = await database.execute(query)

        return {'success': True,
                'status_code': status.HTTP_200_OK,
                'message': 'Device Registration Successful!'}

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail="Some thing unexpected happened!")



@router.post("/device/unregister/{dev_eui}", 
        response_model=SuccessMessage, 
        status_code=201, tags=['Device API'])
async def unregister_deveui(dev_eui: str, 
        current_user: Annotated[User, Depends(get_current_user)]):

    logger.info(f"Finding device with eui {dev_eui}")
    dev_eui = dev_eui.strip()

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Current user has undefined role")

    device2 = await find_device_by_deveui(dev_eui)
    if not device2:
        raise HTTPException(status_code=400, detail="Device with that EUI was not found")

    if device2.domain == 'Public':
        raise HTTPException(status_code=400, detail="Device is in the public domain.")

    if device2.user_id != current_user.id:
        if role.name != 'Admin':
           raise HTTPException(status_code=400, detail="Device is owned by another user.")

    query = (
        mydevice_table.delete().where(mydevice_table.c.device_id == device2.id)
    )
    #logger.debug(query)
    mydev = await database.execute(query)

    logger.info(f"Unregistering device with eui {dev_eui}")
    newdate = datetime.now()
    query = device_table.update().where(device_table.c.dev_eui == device2.dev_eui).values(
            user_id=0, 
            location_id=1)
    #logger.debug(query)
    last_record_id = await database.execute(query)

    return {'success': True, 
            'status_code': status.HTTP_200_OK, 
            'message': 'Device Unregistration Successful!'}


@router.get("/generate_qrcode/{dev_eui}", status_code=201, tags=['Device API'])
async def generate_qrcode(dev_eui: str,
         current_user: Annotated[User, Depends(get_current_user)]):

    logger.info(f"Getting QR Code for dev_eui {dev_eui}")
    dev_eui = dev_eui.strip()

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Current user has undefined role")

    if role.name != "Admin":
        raise HTTPException(status_code=400, detail="Only admins can get devtokens")

    device = await find_device_by_deveui(dev_eui)
    if not device:
        raise HTTPException(status_code=400, detail="Device not found")

    if device:
        if device.domain == "Public":
            raise HTTPException(status_code=400, detail="Device is public")

    logger.info("Getting new device token")
    try:
        # devtoken = "https://api.things.packetworx.net/devicereg/" 
        # devtoken = devtoken + create_deviceregister_token(dev_eui)
        devtoken = create_deviceregister_token(dev_eui)
        img = qrcode.make(devtoken)
        buf = io.BytesIO()
        img.save(buf)
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token",
        )


# @router.get("/generate_qrcode2/{dev_eui}", status_code=201, tags=['Device API'])
async def generate_qrcode2(dev_eui: str,
         current_user: Annotated[User, Depends(get_current_user)]):

    logger.info(f"Getting QR Code for dev_eui {dev_eui}")
    dev_eui = dev_eui.strip()

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Current user has undefined role")

    if role.name != "Admin":
        raise HTTPException(status_code=400, detail="Only admins can get devtokens")

    device = await find_device_by_deveui(dev_eui)
    if not device:
        raise HTTPException(status_code=400, detail="Device not found")

    if device:
        if device.domain == "Public":
            raise HTTPException(status_code=400, detail="Device is public")

    logger.info("Getting new device token")
    try:
        devtoken = "https://api.things.packetworx.net/devicereg/"
        devtoken = devtoken + create_deviceregister_token(dev_eui)
        img = qrcode.make(devtoken)
        buf = io.BytesIO()
        img.save(buf)
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token",
        )




@router.get("/devicereg/{devtoken}",
        response_model=SuccessMessage,
        status_code=201, 
        tags=['Device API'],
        description="This API register a device under your user id")
async def register_with_token(devtoken: str,
        current_user: Annotated[User, Depends(get_current_user)]):

    logger.info(f"Finding device with token {devtoken}")

    dev_eui = get_subject_for_token_type(devtoken, "devicetoken")
    if dev_eui is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device token",
        )
    dev_eui = dev_eui.strip()
    #logger.info("111111")
        
    device = await find_device_by_deveui(dev_eui)
    if not device:
        raise HTTPException(status_code=400, detail="Device with that EUI was not found")
    #logger.info("22222")

    if device.domain == 'Public':
        raise HTTPException(status_code=400, detail="Device is in the public domain.")
    #logger.info("3333")

    if device.user_id != 1 and device.user_id != 0:
        raise HTTPException(status_code=400, detail="Device is owned by another user.")
    #logger.info("wwwww")

    location = await find_location_by_id(device.location_id)
    if not location:
        raise HTTPException(status_code=400, detail="Location was not found")

    if location.user_id != 1 and location.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Location belongs to another user")

    newdate = datetime.now()
    query = device_table.update().where(device_table.c.dev_eui == device.dev_eui).values(
            user_id=current_user.id,
            updated=newdate)
    #logger.info("wwwww")

    #logger.debug(query)
    await database.execute(query)

    newdate = datetime.now()
    query = mydevice_table.insert().values(
            device_id=device.id,
            user_id=current_user.id,
            dev_eui=device.dev_eui,
            description=device.description,
            created=newdate,
            updated=newdate
        )
    #logger.debug(query)
    last_record_id = await database.execute(query)

    return {'success': True,
            'status_code': status.HTTP_200_OK,
            'message': 'Device Registration Successful!'}

    #except Exception as e:
    #    logger.info(e)
    #    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #          detail="Some thing unexpected happened!")




@router.get("/device_summary/{dev_eui}", 
        status_code=201, 
        tags=['Device API'])
async def get_devsumm(dev_eui: str,
         current_user: Annotated[User, Depends(get_current_user)]):

    # response_model=list[DeviceSumm], 

    logger.info(f"Getting Device Summary for dev_eui {dev_eui}")
    dev_eui = dev_eui.strip()

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Current user has undefined role")

    device = await find_device_by_deveui(dev_eui)
    if not device:
        raise HTTPException(status_code=400, detail="Device not found")

    query = devsumm_table.select().where(
            devsumm_table.c.dev_eui==dev_eui).order_by(
                    devsumm_table.c.measurement,
                    devsumm_table.c.yearmonth
                    )

    retdevs = []
    #logger.debug(query)
    summs = await database.fetch_all(query)
    return summs



# GET route (automatically supports HEAD as well)
@router.get("/example", tags=['Device API'])
async def get_example():
    return {"message": "This is a GET request"}


# Explicitly define OPTIONS for the same route
@router.options("/example", tags=['Device API'])
async def options_example():
    headers = {
        "Allow": "GET, POST, OPTIONS, HEAD",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS, HEAD",
        "Access-Control-Allow-Headers": "*",
    }
    return Response(status_code=204, headers=headers)


# Define HEAD explicitly if needed (optional)
@router.head("/example", tags=['Device API'])
async def head_example():
    headers = {
        "X-Example-Header": "ExampleHeaderContent",
    }
    return Response(status_code=200, headers=headers)


@router.get("/public_device",
        response_model=list[FullDevice],
        tags=['Device API'],
        description="This API returns all the public devices")
async def get_all_public_devices(current_user: Annotated[User, Depends(get_current_user)]):

    logger.info("Getting all public devices")
    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Current user has undefined role")

    query = device_table.select().where(
            device_table.c.domain=='Public'
        ).order_by(device_table.c.id)

    retdevs = []
    #logger.debug(query)
    devs = await database.fetch_all(query)
    if devs:
        for dtl in devs:
            fdev = await get_fulldevice_with_deveui(dtl.dev_eui, current_user)
            if fdev:
                retdevs.append(fdev)

    return retdevs



@router.get("/fulldevices",
        response_model=list[FullDevice],
        tags=['Device API'],
        description="This API returns all the devices iwith full details")
async def get_all_devices_full(current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Getting all devices for a user")
    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Current user has undefined role")

    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only admins can user this API")


    query = device_table.select().where().order_by(device_table.c.id)

    retdevs = []
    #logger.debug(query)
    devs = await database.fetch_all(query)
    if devs:
        for dtl in devs:
            fdev = await get_fulldevice_with_deveui(dtl.dev_eui, current_user)
            if fdev:
                retdevs.append(fdev)

    return retdevs




