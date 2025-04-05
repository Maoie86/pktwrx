import logging
import json
import os
import yaml
import datetime
import time
import uuid

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status, Depends, UploadFile, File
from fastapi.responses import FileResponse
from packetthings import tasks
from packetthings.database import database, type_table, typedetail_table
from packetthings.models.type import TypeIn, Type, TypeUpdate, FullType, TypeDetails
from packetthings.security import (
    authenticate_user,
    get_user,
)
from packetthings.models.user import User
from packetthings.security import get_current_user
from packetthings.routers.role import find_role_by_id
from packetthings.routers.measurement import find_measurement_by_id

logger = logging.getLogger(__name__)
router = APIRouter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
timestr = time.strftime("%Y%m%d-%H%M%S")


async def find_typedetail_by_type_id(type_id: int):
    logger.info(f"Finding typedetails with type id: {type_id}")
    query = typedetail_table.select().where(typedetail_table.c.type_id == type_id)
    #logger.debug(query)
    return await database.fetch_all(query)


async def find_type_by_name(name: str):
    logger.info(f"Finding type with name: {name}")
    query = type_table.select().where(type_table.c.name == name)
    #logger.debug(query)
    return await database.fetch_one(query)


async def find_type_by_id(type_id: int):
    logger.info(f"Finding type with id: {type_id}")
    query = type_table.select().where(type_table.c.id == type_id)
    #logger.debug(query)
    return await database.fetch_one(query)


@router.post("/type", response_model=Type, status_code=201, tags=['Type API'])
async def add_type(type: TypeIn, current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Adding new type.")

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can add device types")
 
    type_name = type.name.strip()
    if type_name=="":
        raise HTTPException(status_code=400, detail="Type name cannot be blank")


    if await find_type_by_name(type.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that name already exists",
        )

    query = type_table.insert().values(
            name=type.name,
            inactivity=type.inactivity,
            description=type.description,
            created=datetime.datetime.now(),
            updated=datetime.datetime.now()
        )
    #logger.debug(query)
    last_record_id = await database.execute(query)
    data = {**type.model_dump()}
    return {**data, "id": last_record_id}


@router.get("/type", response_model=list[Type], tags=['Type API'])
async def get_all_types(current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Getting all types")
    query = type_table.select().where()
    #logger.debug(query)
    return await database.fetch_all(query)


@router.get("/fulltype", response_model=list[FullType], tags=['Type API'])
async def get_all_fulltype(current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Getting all types")

    query = type_table.select().where()
    #logger.debug(query)

    ret = [] 
    retdtls = []
    types = await database.fetch_all(query)
    if types:
        for ntype in types:
            typedtls = await find_typedetail_by_type_id(ntype.id)
            if typedtls:
                retdtls = []
                for dtl in typedtls:
                    measure = ""
                    measurement = await find_measurement_by_id(dtl.measurement_id)
                    if measurement:
                        measure = measurement.name

                    ndtl =  TypeDetails(id=dtl.id,
                            name=dtl.name,
                            description=dtl.description,
                            measurement_id=dtl.measurement_id,
                            measurement_nm=measure)
                    retdtls.append(ndtl)
            fulltype = FullType(name=ntype.name,
                id=ntype.id,
                description=ntype.description,
                inactivity=ntype.inactivity,
                typedtls=retdtls)

            ret.append(fulltype)

    return ret



@router.patch("/type", response_model=Type, tags=['Type API'])
async def update_type(type: TypeUpdate, current_user: Annotated[User, Depends(get_current_user)]):

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can update device types")

    if not await find_type_by_id(type.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that name was not found.",
        )
    type2 = await find_type_by_name(type.name)
    if type2.id != type.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that name already exists.",
        )
 
    logger.info("Updating type with id: {type.id}")
    query = (
        type_table.update().where(type_table.c.id == type.id).values(
            name=type.name,
            inactivity=type.inactivity,
            description=type.description,
            updated=datetime.datetime.now()
        )
    )
    #logger.debug(query)
    await database.execute(query)
    return await find_type_by_id(type.id)


@router.post("/type/upload/{type_id}", tags=['Type API'])
async def upload_file(type_id: int, 
        current_user: Annotated[User, Depends(get_current_user)], 
        file: UploadFile = File(...)):

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can upload device types images")

    if not await find_type_by_id(type_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that ID was not found.",
        )
     
    file.filename = f"{uuid.uuid1()}.jpg"
    contents = await file.read()

    #save the file
    SAVE_FILE_PATH = os.path.join(UPLOAD_DIR, file.filename)
    with open(SAVE_FILE_PATH, "wb") as f:
        f.write(contents)

    #update type with id
    logger.info("Updating type with id: {type.id}")
    query = (
        type_table.update().where(type_table.c.id == type_id).values(
            image=file.filename,
            updated=datetime.datetime.now()
        )
    )
    #logger.debug(query)
    await database.execute(query)
    return await find_type_by_id(type_id)


@router.get("/type/download/", tags=['Type API'])
async def download_file(new_filename, current_user: Annotated[User, Depends(get_current_user)]):
    SAVE_FILE_PATH = os.path.join(UPLOAD_DIR, new_filename)
    return FileResponse(
            path=SAVE_FILE_PATH,
            media_type="application/octet-stream",
            filename=new_filename,)


@router.get("/type/{name}", response_model=Type, tags=['Type API'])
async def get_type_with_names(name: str, current_user: Annotated[User, Depends(get_current_user)]):
    type = await find_type_by_name(name)
    if not type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that name was not found.",
        )
    return type

# this does not get called as the request is catured by the previous function
@router.get("/type_by_id/{type_id}", response_model=Type, tags=['Type API'])
async def get_type_with_id(type_id: int, current_user: Annotated[User, Depends(get_current_user)]):
    type = await find_type_by_id(type_id)
    if not type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that id was not found.",
        )
    return type


@router.delete("/type", response_model=Type, tags=['Type API'])
async def delete_type(type: Type, current_user: Annotated[User, Depends(get_current_user)]):

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can delete device types")
    
    if not await find_type_by_id(type.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that ID was not found.",
        )
    if await find_typedetail_by_type_id(type.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Typedetails with that Type ID was found.",
        )

    logger.info("Deleting type with id: {type.id}")
    query = (
        type_table.delete().where(type_table.c.id == type.id)
    )
    #logger.debug(query)
    await database.execute(query)
    return type



