import logging
from typing import Annotated
from datetime import datetime, timezone
from fastapi import (
        APIRouter, 
        BackgroundTasks, 
        HTTPException, 
        Request, 
        status, 
        Depends, 
        Response, 
        Header
)
from packetthings import tasks
from packetthings.database import database, measurement_table
from packetthings.models.measurement import MeasurementIn, Measurement, MeasurementUpdate, MeasurementFull
from packetthings.security import (
    authenticate_user,
    get_user,
)
from packetthings.models.user import User
from packetthings.security import get_current_user
from packetthings.routers.unit import find_unit_by_id, find_unit_by_name
from packetthings.routers.role import find_role_by_id


logger = logging.getLogger(__name__)
router = APIRouter()


async def find_measurement_by_name(name: str):
    logger.info(f"Finding measurement with name: {name}")
    query = measurement_table.select().where(measurement_table.c.name == name)
    #logger.debug(query)
    return await database.fetch_one(query)


async def find_measurement_by_id(measurement_id: int):
    logger.info(f"Finding measurement with id: {measurement_id}")
    query = measurement_table.select().where(measurement_table.c.id == measurement_id)
    #logger.debug(query)
    return await database.fetch_one(query)


@router.post("/measurement", response_model=Measurement, status_code=201, tags=['Measurement API'])
async def add_measurement(measurement: MeasurementIn, 
        current_user: Annotated[User, Depends(get_current_user)]):

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can add Measurements")
    
    logger.debug("Adding new measurement.")

    measurement_name = measurement.name.strip()
    if measurement_name=="":
        raise HTTPException(status_code=400, detail="Measurement name cannot be blank")

    if await find_measurement_by_name(measurement.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A measurement with that name already exists",
        )
    if not await find_unit_by_id(measurement.unit_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A unit with that ID was not found",
        )

    newdate = datetime.now()
    query = measurement_table.insert().values(
            name=measurement.name,
            unit_id=measurement.unit_id,
            description=measurement.description,
            created=newdate,
            updated=newdate
        )
    #logger.debug(query)
    last_record_id = await database.execute(query)
    data = {**measurement.model_dump()}
    return {**data, "id": last_record_id}


@router.get("/measurement", response_model=list[Measurement], tags=['Measurement API'])
async def get_all_measurements(current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Getting all measurements")
    query = measurement_table.select().where()
    #logger.debug(query)
    return await database.fetch_all(query)


@router.get("/full/measurement", response_model=list[MeasurementFull], tags=['Measurement API'])
async def get_full_measurements(current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Getting all measurements")
    query = measurement_table.select().where()
    #logger.debug(query)

    retjson = []
    ctr = 1

    measurements = await database.fetch_all(query)

    for dtl in measurements:
        unit = await find_unit_by_id(dtl.unit_id)

        if unit:
            newmeasure = MeasurementFull(id=dtl.id,
                    name=dtl.name,
                    description=dtl.description,
                    unit_id=dtl.unit_id,
                    unit_nm=unit.name)
            retjson.append(newmeasure)
    
    return retjson


@router.get("/measurement/{name}", response_model=Measurement, tags=['Measurement API'])
async def get_measurement_with_names(name: str, 
        current_user: Annotated[User, Depends(get_current_user)]):
    return await find_measurement_by_name(name)


@router.get("/measurement_by_id/{measurement_id}", 
        response_model=Measurement, 
        tags=['Measurement API'])
async def get_measurement_with_id(measurement_id: int, 
        current_user: Annotated[User, Depends(get_current_user)]):
    measurement = await find_measurement_by_id(measurement_id)
    if not measurement:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A measurement with that id was not found.",
        )
    return measurement



@router.patch("/measurement", response_model=Measurement, tags=['Measurement API'])
async def update_measurement(measurement: MeasurementUpdate, 
        current_user: Annotated[User, Depends(get_current_user)]):

    logger.info(f"Getting Role")
    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can update Measurements")

    logger.info(f"Getting Measurement")
    if not await find_measurement_by_id(measurement.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A measurement with that ID was not found.",
        )
    measurement2 = await find_measurement_by_name(measurement.name)
    if measurement2.id != measurement.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A measurement with that name already exists.",
        )
 
    logger.info(f"Updating measurement with id: {measurement.id}")
    newdate = datetime.now()
    query = (
        measurement_table.update().where(measurement_table.c.id == measurement.id).values(
            name=measurement.name,
            description=measurement.description,
            unit_id=measurement.unit_id,
            updated=newdate
        )
    )
    #logger.debug(query)
    await database.execute(query)
    return await find_measurement_by_id(measurement.id)


@router.delete("/measurement", response_model=Measurement, tags=['Measurement API'])
async def delete_measurement(measurement: MeasurementUpdate, 
        current_user: Annotated[User, Depends(get_current_user)]):

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can delete Measurements")

    if not await find_measurement_by_id(measurement.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A measurement with that ID was not found.",
        )

    logger.info(f"Deleting measurement with id: {measurement.id}")
    query = (
        measurement_table.delete().where(measurement_table.c.id == measurement.id)
    )
    #logger.debug(query)
    await database.execute(query)
    return measurement


@router.get("/measurementdtl/", tags=['Measurement API'])
async def read_items(user_agent: Annotated[str | None, Header()] = None):
    return {"User-Agent": user_agent}


