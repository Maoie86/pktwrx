import logging
import os
import json
import yaml
import time
import uuid

from typing import Annotated
from datetime import datetime, timezone
from sqlalchemy import and_, or_

from fastapi import (
        APIRouter, 
        BackgroundTasks, 
        HTTPException, 
        Request, 
        status, 
        Depends, 
        Response, 
        Header, 
        UploadFile, 
        File
)

from fastapi.responses import FileResponse
from packetthings import tasks
from packetthings.database import database, location_table, device_table
from packetthings.models.location import (
        LocationIn, 
        Location, 
        LocationUpdate
        )
# from packetthings.routers.device import find_device_by_location_id
from packetthings.security import (
    authenticate_user,
    get_user
)

from packetthings.models.user import User
from packetthings.security import get_current_user
from packetthings.routers.role import find_role_by_id

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads2")
timestr = time.strftime("%Y%m%d-%H%M%S")

logger = logging.getLogger(__name__)
router = APIRouter()


async def find_location_by_name(name: str, user_id: int):
    logger.info(f"Finding location with name: {name}")
    query = location_table.select().where(
            and_(location_table.c.name==name,
                location_table.c.user_id==user_id))
    # logger.debug(query)
    return await database.fetch_one(query)


async def find_location_by_id(location_id: int):
    logger.info(f"Finding location with id: {location_id}")
    query = location_table.select().where(location_table.c.id==location_id)
    # logger.debug(query)
    return await database.fetch_one(query)


async def find_locations_by_group_id(location_id: int):
    logger.info(f"Finding location group with id: {location_id}")
    query = location_table.select().where(location_table.c.location_id==location_id)
    # logger.debug(query)
    return await database.fetch_all(query)


async def find_device_by_location_id(location_id):
    logger.info(f"Finding location with id: {location_id}")
    query = device_table.select().where(device_table.c.location_id == location_id)
    # logger.debug(query)
    devices = await database.fetch_all(query)
    return devices


@router.post("/location", response_model=Location, status_code=201, tags=['Location API'])
async def add_location(location: LocationIn, 
        current_user: Annotated[User, Depends(get_current_user)]):


    logger.debug("Adding new location.")
    if location.name.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location name must not be blank",
        )

    # logger.debug(location)
    loc2 = await find_location_by_name(location.name, current_user.id)
    if loc2:
        #logger.debug(loc2)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A Location with that name already exists",
        )
    else:
        logger.debug("Not found")
        
    if location.location_id != 0:
        # top level, group
        loc3 = await find_location_by_id(location.location_id)
        if loc3:
            # check if same user and if level is 0
            if loc3.location_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid location level. Onyl 2 levels allowed. ",
                )

            if loc3.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Location(Group) does not belong to you. ",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A location with that ID was not found",
            )

    logger.debug("Adding new location.")

    newdate = datetime.now()
    if location.location_id != 0:
        query = location_table.insert().values(
                name=location.name,
                user_id=current_user.id,
                location_id=location.location_id,
                description=location.description,
                created=newdate,
                updated=newdate
            )
    else:
        query = location_table.insert().values(
                name=location.name,
                user_id=current_user.id,
                description=location.description,
                created=newdate,
                updated=newdate
            )
 
    # logger.debug(query)
    last_record_id = await database.execute(query)
    data = {**location.model_dump()}
    return {**data, "id": last_record_id}


@router.get("/location", response_model=list[Location], tags=['Location API'])
async def get_all_locations(current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Getting all locations")
    query = location_table.select().where(location_table.c.user_id==current_user.id)
    # logger.debug(query)
    return await database.fetch_all(query)



@router.get("/group", response_model=list[Location], tags=['Location API'])
async def get_all_groups(current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Getting all location groups")
    query = location_table.select().where(
        and_(location_table.c.location_id==None,
            location_table.c.user_id==current_user.id
        ) 
    )
    
    # logger.debug(query)
    return await database.fetch_all(query)


@router.get("/get_children/{location_id}", response_model=list[Location], tags=['Location API'])
async def get_location_children(location_id: int, 
        current_user: Annotated[User, Depends(get_current_user)]):
    logger.info(f"Getting all locations for group id: {location_id}")
    if location_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Child locations cannot have null parent ID",
        )

    query = (
            location_table.select().where(
                (location_table.c.location_id == location_id) 
                and (location_table.c.user_id==current_user.id))
            )
    #logger.debug(query)
    return await database.fetch_all(query)



@router.get("/location/{name}", response_model=Location, tags=['Location API'])
async def get_location_with_names(name: str, 
        current_user: Annotated[User, Depends(get_current_user)]):
    return await find_location_by_name(name, current_user.id)


@router.get("/location_by_id/{location_id}", response_model=Location, tags=['Location API'])
async def get_location_by_id(location_id: int, 
        current_user: Annotated[User, Depends(get_current_user)]):
    location = await find_location_by_id(location_id)
    if not location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location with that id was not found.",
        )
    return location


@router.patch("/location", response_model=Location, tags=['Location API'])
async def update_location(location: LocationUpdate, 
        current_user: Annotated[User, Depends(get_current_user)]):
    if not await find_location_by_id(location.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A location with that ID was not found.",
        )
    location2 = await find_location_by_name(location.name, current_user.id)
    if location2.id != location.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A location with that name already exists.",
        )
 
    logger.info(f"Updating location with id: {location.id}")
    newdate = datetime.now()
    query = (
        location_table.update().where(location_table.c.id == location.id).values(
            name=location.name,
            description=location.description,
            updated=newdate
        )
    )
    #logger.debug(query)
    await database.execute(query)
    return await find_location_by_id(location.id)


@router.delete("/location", response_model=Location, tags=['Location API'])
async def delete_location(location: Location, 
        current_user: Annotated[User, Depends(get_current_user)]):

    group = await find_location_by_id(location.id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A location with that ID was not found",
        )

    # location2 = await find_location_by_name(location.name, current_user.id)
    if group.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That location does not belong to the current user",
        )

    #devices = find_device_by_location_id(location.id)
    #if devices:
    #    raise HTTPException(
    #        status_code=status.HTTP_400_BAD_REQUEST,
    #        detail="This location has device(s) under it.",
    #    )


    locs = await find_locations_by_group_id(location.id)
    if locs:
        for loc in locs:
            logger.info(f"Updating devices to default gruop and location")
            query = (
                device_table.update().where(device_table.c.location_id == loc.id).values(
                    location_id=1
                )
            )
            #logger.debug(query)
            await database.execute(query)

            logger.info(f"Delete location with id: {loc.id}")
            query = (
                location_table.delete().where(location_table.c.id == loc.id)
            )
            #logger.debug(query)
            await database.execute(query)
    else:
        loc = await find_location_by_id(location.id)
        if loc:
            logger.info(f"Updating devices to default gruop and location")
            query = (
                device_table.update().where(device_table.c.location_id == loc.id).values(
                    location_id=1
                )
            )
            #logger.debug(query)
            await database.execute(query)


    logger.info(f"Delete location with id: {location.id}")
    query = (
        location_table.delete().where(location_table.c.id == location.id)
    )
    #logger.debug(query)
    await database.execute(query)
    return location



@router.post("/location/upload/{location_id}", tags=['Location API'])
async def location_upload_file(location_id: int, 
        current_user: Annotated[User, Depends(get_current_user)], 
        file: UploadFile = File(...)):

    if not await find_location_by_id(location_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A location with that ID was not found.",
        )

    file.filename = f"{uuid.uuid1()}.jpg"
    contents = await file.read()

    #save the file
    SAVE_FILE_PATH = os.path.join(UPLOAD_DIR, file.filename)
    with open(SAVE_FILE_PATH, "wb") as f:
        f.write(contents)


    #update type with id
    logger.info(f"Updating location with id: {location_id}")
    query = (
        location_table.update().where(location_table.c.id == location_id).values(
            image=file.filename,
            updated=datetime.now()
        )
    )
    #logger.debug(query)
    await database.execute(query)
    return await find_location_by_id(location_id)


@router.get("/location/download/", tags=['Location API'])
async def location_download_file(new_filename, 
        current_user: Annotated[User, Depends(get_current_user)]):

    SAVE_FILE_PATH = os.path.join(UPLOAD_DIR, new_filename)
    return FileResponse(
            path=SAVE_FILE_PATH,
            media_type="application/octet-stream",
            filename=new_filename,)



