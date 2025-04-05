import logging
import json
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status, Depends
from packetthings import tasks
from packetthings.database import database, unit_table
from packetthings.models.unit import UnitIn, Unit, UnitUpdate, UnitList, UnitError, UnitDict
from packetthings.security import (
    authenticate_user,
    get_user,
)
from packetthings.models.user import User
from packetthings.security import get_current_user
from packetthings.routers.role import find_role_by_id

logger = logging.getLogger(__name__)
router = APIRouter()


async def find_unit_by_name(name: str):
    logger.info(f"Finding unit with name: {name}")
    query = unit_table.select().where(unit_table.c.name == name)
    #logger.debug(query)
    return await database.fetch_one(query)


async def find_unit_by_id(unit_id: int):
    logger.info(f"Finding unit with id: {unit_id}")
    query = unit_table.select().where(unit_table.c.id == unit_id)
    #logger.debug(query)
    return await database.fetch_one(query)


@router.post("/unit", response_model=Unit, status_code=201, tags=['Unit API'])
async def add_unit(unit: UnitIn, current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Adding new unit of measure.")

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can add units")

    unit_name = unit.name.strip()
    if unit_name=="":
        raise HTTPException(status_code=400, detail="Unit name cannot be blank")

    if await find_unit_by_name(unit.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A unit of measure with that name already exists",
        )
    newdate = datetime.now()
    query = unit_table.insert().values(
            name=unit.name,
            description=unit.description,
            created=newdate,
            updated=newdate
        )
    #logger.debug(query)
    last_record_id = await database.execute(query)
    data = {**unit.model_dump()}
    return {**data, "id": last_record_id}


@router.get("/unit", response_model=list[Unit], tags=['Unit API'])
async def get_all_units(current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Getting all units")
    query = unit_table.select().where()
    #logger.debug(query)
    return await database.fetch_all(query)



@router.get("/unit/{name}", response_model=Unit, tags=['Unit API'])
async def get_unit_with_name(name: str, current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Getting unit with name: {name}")
    unit = await find_unit_by_name(name)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A unit with that id was not found.",
        )
    return unit



@router.get("/unit_by_id/{unit_id}", response_model=Unit, tags=['Unit API'])
async def get_unit_with_id(unit_id: int, current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Getting unit with id: {unit_id}")
    unit = await find_unit_by_id(unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A unit with that id was not found.",
        )
    return unit


@router.patch("/unit", response_model=Unit, tags=['Unit API'])
async def update_unit(unit: UnitUpdate, current_user: Annotated[User, Depends(get_current_user)]):

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can updatye units")
    
    if not await find_unit_by_id(unit.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A unit with that ID was not found.",
        )
    unit2 = await find_unit_by_name(unit.name)
    if unit2:
        if unit2.id != unit.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A unit with that name already exists.",
            )
 
    logger.info("Updating unit with id: {unit.id}")
    newdate = datetime.now()
    query = (
        unit_table.update().where(unit_table.c.id == unit.id).values(
            name=unit.name,
            description=unit.description,
            updated=newdate
        )
    )
    #logger.debug(query)
    await database.execute(query)
    return await find_unit_by_id(unit.id)


@router.delete("/unit", response_model=Unit, tags=['Unit API'])
async def delete_unit(unit: UnitUpdate, current_user: Annotated[User, Depends(get_current_user)]):

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")
    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can delete units")
    if not await find_unit_by_id(unit.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A unit with that ID was not found.",
        )

    # also check devices that use this unit
    logger.info("Deleting unit with id: {unit.id}")
    query = (
        unit_table.delete().where(unit_table.c.id == unit.id)
    )
    #logger.debug(query)
    await database.execute(query)
    return unit


@router.post("/units", status_code=201, tags=['Unit API'])
async def add_unit_json(data: list[UnitIn], 
        current_user: Annotated[User, Depends(get_current_user)]):

    logger.info("Adding list unit of measures.")

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can add units")

    ctr = 0
    for dtl in data:
        ctr = ctr +1
        logger.debug(str(ctr) + " --- " + str(dtl))

    return data


@router.post("/units2", status_code=201, tags=['Unit API'])
async def add_unit_txt(data: UnitDict, 
        current_user: Annotated[User, Depends(get_current_user)]):

    logger.info("Adding list unit of measures.")

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can add units")

    #logger.debug(data)

    return data

@router.post("/webhook", status_code=201, tags=['Unit API'])
async def the_webhook(request: Request):
    raw_body = await request.body()
    body_json = json.loads(json.loads(raw_body.decode('utf-8')))
    rpt = []
    for item in body_json:
        if not await find_unit_by_name(item["name"]):
            uniterr = UnitError(name=item["name"], description="duplicate unit")
            rpt.append(uniterr)
            # logger.debug(rpt)
        # validate
    # if len(rpt) > 0:
    #    raise HTTPException(status_code=400, detail="Errors in the upload file.")
    # logger.debug(rpt)

    return rpt




