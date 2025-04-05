import logging
from enum import Enum
from typing import Annotated
from datetime import datetime, timezone

import sqlalchemy
from fastapi import APIRouter, Depends, HTTPException, status
from packetthings.database import database, mydevice_table
from packetthings.routers.device import (
        find_device_by_id, 
        find_device_by_deveui, 
        get_fulldevice_with_deveui 
)
from packetthings.routers.location import find_location_by_id
from packetthings.models.device import Device, FullDevice 
from packetthings.models.mydevice import (
    MyDevice,
    MyDeviceIn,
)
from packetthings.models.user import User, SuccessMessage
from packetthings.security import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


async def find_mydevice_by_id(mydevice_id: int):
    logger.info(f"Finding mydevice with eui {device_id}")
    query = mydevice_table.select().where(mydevice_table.c.id == mydevice_id)
    #logger.debug(query)
    return await database.fetch_one(query)


async def find_mydevice_by_deviceid(device_id: int):
    logger.info(f"Finding mydevice with eui {device_id}")
    query = mydevice_table.select().where(mydevice_table.c.device_id == device_id)
    #logger.debug(query)
    return await database.fetch_one(query)


async def find_mydevice_by_dev_eui(dev_eui: str):
    logger.info(f"Finding mydevice with eui {dev_eui}")
    query = mydevice_table.select().where(mydevice_table.c.dev_eui == dev_eui)
    #logger.debug(query)
    return await database.fetch_one(query)


@router.get("/mydevices", response_model=list[MyDevice], tags=['MyDevice API'])
async def get_all_mydevices(current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Getting all mydevices")
    query = mydevice_table.select().where(
            mydevice_table.c.user_id == current_user.id).order_by(mydevice_table.c.id)
    #logger.debug(query)
    devs = await database.fetch_all(query)

    dtls = []
    if devs:
        for dtl_data in devs:
            dev = await get_fulldevice_with_deveui(dtl_data.dev_eui, current_user)
            if dev:
                devdtl = MyDevice(dev_eui = dev.dev_eui, 
                        type_id = dev.type_id, 
                        type_nm = dev.type_nm)
                dtls.append(devdtl)
            else:
                # the device eui was not found, delete
                query = mydevice_table.delete().where(mydevice_table.c.dev_eui == dev.dev_eui)
                #logger.debug(query)
                await database.execute(query)
    return dtls


@router.get("/mydevices_by_type", response_model=list[MyDevice], tags=['MyDevice API'])
async def get_all_mydevices_by_type(type_id: int, current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Getting all mydevices")
    query = mydevice_table.select().where(
            mydevice_table.c.user_id == current_user.id).order_by(mydevice_table.c.id)
    #logger.debug(query)
    devs = await database.fetch_all(query)

    dtls = []
    if devs:
        for dtl_data in devs:
            dev = await get_fulldevice_with_deveui(dtl_data.dev_eui, current_user)
            if dev:
                if dev.type_id == type_id:
                    devdtl = MyDevice(dev_eui = dev.dev_eui,
                            type_id = dev.type_id,
                            type_nm = dev.type_nm)
                    dtls.append(devdtl)
    return dtls


@router.get("/mydevices_by_type_nm", response_model=list[MyDevice], tags=['MyDevice API'])
async def get_all_mydevices_by_type_nm(type_nm: str, current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Getting all mydevices")

    query = mydevice_table.select().where(
            mydevice_table.c.user_id == current_user.id).order_by(mydevice_table.c.id)
    #logger.debug(query)
    devs = await database.fetch_all(query)

    type_nm = type_nm.strip()

    dtls = []
    if devs:
        for dtl_data in devs:
            dev = await get_fulldevice_with_deveui(dtl_data.dev_eui, current_user)
            if dev:
                if dev.type_nm == type_nm:
                    devdtl = MyDevice(dev_eui = dev.dev_eui,
                            type_id = dev.type_id,
                            type_nm = dev.type_nm)
                    dtls.append(devdtl)
    return dtls


@router.get("/myfulldevices", response_model=list[FullDevice], tags=['MyDevice API'])
async def get_all_mydevices(current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Getting all mydevices")
    query = mydevice_table.select().where(
            mydevice_table.c.user_id == current_user.id).order_by(mydevice_table.c.id)
    #logger.debug(query)
    devs = await database.fetch_all(query)

    dtls = []
    if devs:
        for dtl_data in devs:
            dev = await get_fulldevice_with_deveui(dtl_data.dev_eui, current_user)
            if dev:
                dtls.append(dev)
    return dtls


@router.post("/favorites/{dev_eui}", 
        response_model=Device, 
        description="Add to mydevices", 
        tags=['MyDevice API'])
async def register_mydevice(dev_eui: str, 
        current_user: Annotated[User, Depends(get_current_user)]):

    logger.info(f"Add device to mydevices {dev_eui}")

    device = await get_fulldevice_with_deveui(dev_eui, current_user)
    if not device:
        raise HTTPException(status_code=400, detail="Device not found")

    #check if device domain
    if device.domain != 'Public':
        if device.domain == 'Private':
            if device.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You do not own this device.")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device is a private device.")

    mydev = await find_mydevice_by_dev_eui(dev_eui)
    if mydev:
        raise HTTPException(status_code=400, detail="Device is already in your favorites...")

    newdate = datetime.now()
    query = mydevice_table.insert().values(
            device_id=device.id,
            user_id=current_user.id,
            type_id=device.type_id,
            type_nm=device.type_nm,
            dev_eui=device.dev_eui,
            description=device.description,
            created=newdate,
            updated=newdate
        )
    #logger.debug(query)
    last_record_id = await database.execute(query)
    return device


@router.delete("/unfavorite/{dev_eui}", 
        response_model=MyDevice, 
        description="Delet from mydevices", tags=['MyDevice API'])
async def unregister_mydevice(dev_eui: str, 
        current_user: Annotated[User, Depends(get_current_user)]):

    logger.info("Delete device from mydevice")

    mydev = await find_mydevice_by_dev_eui(dev_eui)
    if not mydev:
        raise HTTPException(status_code=404, detail="Device is not in your favorites")

    query = mydevice_table.delete().where(mydevice_table.c.id == mydev.id)
    #logger.debug(query)
    await database.execute(query)
    return mydev



