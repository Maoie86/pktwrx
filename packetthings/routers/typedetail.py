import logging
import json
import os
import yaml
import datetime
import time
import uuid

from typing import Annotated

from fastapi import (
        APIRouter, 
        BackgroundTasks, 
        HTTPException, 
        Request, 
        status, 
        Depends, 
        UploadFile, 
        File
)
from fastapi.responses import FileResponse
from packetthings import tasks
from packetthings.database import database, typedetail_table, type_table
from packetthings.models.typedetail import TypeDetailIn, TypeDetail, TypeDetailUpdate
from packetthings.models.type import Type
from packetthings.security import (
    authenticate_user,
    get_user,
)
from packetthings.models.user import User
from packetthings.security import get_current_user
from packetthings.routers.type import find_type_by_id, find_type_by_name
from packetthings.routers.role import find_role_by_id
from packetthings.routers.measurement import find_measurement_by_id

logger = logging.getLogger(__name__)
router = APIRouter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
timestr = time.strftime("%Y%m%d-%H%M%S")


@router.get("/typedetail/{name}", response_model=TypeDetail, tags=['Type API'])
async def find_typedetail_by_name(name: str, 
        current_user: Annotated[User, Depends(get_current_user)]):
    logger.info(f"Finding typedetail with name: {name}")
    query = typedetail_table.select().where(typedetail_table.c.name == name)
    #logger.debug(query)
    return await database.fetch_one(query)


@router.get("/typedetailid/{typedetail_id}", response_model=TypeDetail, tags=['Type API'])
async def find_typedetail_by_id(typedetail_id: int, 
        current_user: Annotated[User, Depends(get_current_user)]):
    logger.info(f"Finding typedetail with id: {typedetail_id}")
    query = typedetail_table.select().where(typedetail_table.c.id == typedetail_id)
    #logger.debug(query)
    return await database.fetch_one(query)


@router.get("/typedetails/{type_id}", response_model=list[TypeDetail], tags=['Type API'])
async def find_typedetail_by_type_id(type_id: int, 
        current_user: Annotated[User, Depends(get_current_user)]):

    logger.info(f"Finding typedetails with type id: {type_id}")
    query = typedetail_table.select().where(
            typedetail_table.c.type_id == type_id).order_by(typedetail_table.c.rank)
    #logger.debug(query)
    return await database.fetch_all(query)


@router.get("/typedetail", response_model=list[TypeDetail], tags=['Type API'])
async def get_all_typedetails(current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Getting all typedetails")
    query = typedetail_table.select().where()
    #logger.debug(query)
    return await database.fetch_all(query)


@router.post("/typedetail", response_model=TypeDetail, status_code=201, tags=['Type API'])
async def add_typedetail(typedetail: TypeDetailIn, 
        current_user: Annotated[User, Depends(get_current_user)]):

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can add Device Type Details")

    if not await find_measurement_by_id(typedetail.measurement_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A measurement with that ID was not found",
        )

    logger.debug("Adding new typedetail.")
    if not await find_type_by_id(typedetail.type_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A type with that ID was not found",
        )

    if await find_typedetail_by_name(typedetail.name, current_user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A typedetail with that name already exists",
        )

    rank = 1
    if typedetail.rank:
        rank = typedetail.rank

    query = typedetail_table.insert().values(
            name=typedetail.name,
            description=typedetail.description,
            type_id=typedetail.type_id,
            rank=rank,
            measurement_id=typedetail.measurement_id,
            created=datetime.datetime.now(),
            updated=datetime.datetime.now()
        )
    #logger.debug(query)
    last_record_id = await database.execute(query)
    data = {**typedetail.model_dump()}
    return {**data, "id": last_record_id}


@router.delete("/typedetail", response_model=TypeDetail, status_code=201, tags=['Type API'])
async def delete_typedetail(typedetail: TypeDetail, 
        current_user: Annotated[User, Depends(get_current_user)]):

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can delete Device Type Details")

    logger.debug("Deleting typedetail.")
    if not await find_typedetail_by_id(typedetail.id, current_user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A typedetail with that ID was not found",
        )
    query = typedetail_table.delete().where(typedetail_table.c.id == typedetail.id)
    #logger.debug(query)
    return typedetail


@router.patch("/typedetail", response_model=TypeDetail, status_code=201, tags=['Type API'])
async def update_typedetail(typedetail: TypeDetailUpdate,
        current_user: Annotated[User, Depends(get_current_user)]):

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can delete Device Type Details")

    if not await find_measurement_by_id(typedetail.measurement_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A measurement with that ID was not found",
        )

    if not await find_typedetail_by_id(typedetail.id, current_user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A typedetail with that ID was not found",
        )

    rank = 1
    if typedetail.rank:
        rank = typedetail.rank

    logger.info("Updating typedetail with id {typedetail.id}")
    query = (
        typedetail_table.update().where(typedetail_table.c.id == typedetail.id).values(
            name=typedetail.name,
            measurement_id=typedetail.measurement_id,
            rank=rank,
            description=typedetail.description,
            updated=datetime.datetime.now()
        )
    )
    #logger.debug(query)
    await database.execute(query)
    return await find_typedetail_by_id(typedetail.id, current_user)


