import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status, Depends
from packetthings import tasks
from packetthings.database import database, role_table
from packetthings.models.role import RoleIn, Role, RoleUpdate
from packetthings.security import (
    authenticate_user,
    get_user,
)
from packetthings.models.user import User
from packetthings.routers.user import find_users_by_role_id
from packetthings.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


async def find_role_by_name(name: str):
    logger.info(f"Finding role with name: {name}")
    query = role_table.select().where(role_table.c.name == name)
    #logger.debug(query)
    return await database.fetch_one(query)


async def find_role_by_id(role_id: int):
    logger.info(f"Finding role with id: {role_id}")
    query = role_table.select().where(role_table.c.id == role_id)
    #logger.debug(query)
    return await database.fetch_one(query)


#@router.post("/roles", response_model=list[Role], status_code=201, tags=['Role API'])
#async def add_roles(role: list[RoleIn], current_user: Annotated[User, Depends(get_current_user)]):
#
#    logger.debug("Adding new role by batch.")
#
#    urole = await find_role_by_id(current_user.role_id)
#    if not urole:
#        raise HTTPException(status_code=404, detail="Current user has undefined role")
#
#    if urole.name != 'Admin':
#        raise HTTPException(status_code=400, detail="Only Admins can add roles")
#
#    if await find_role_by_name(role.name):
#        raise HTTPException(
#            status_code=status.HTTP_400_BAD_REQUEST,
#            detail="A role with that name already exists",
#        )
#    newdate = datetime.now()
#    query = role_table.insert().values(
#            name=role.name,
#            status='Active',
#            description=role.description,
#            created=newdate,
#            updated=newdate
#        )
#
#    logger.debug(query)
#    last_record_id = await database.execute(query)
#    data = {**role.model_dump()}
#    return {**data, "id": last_record_id}


@router.post("/role", response_model=Role, status_code=201, tags=['Role API'])
async def add_role(role: RoleIn, current_user: Annotated[User, Depends(get_current_user)]):
    logger.debug("Adding new role.")

    urole = await find_role_by_id(current_user.role_id)
    if not urole:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    if urole.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can add roles")

    if not role.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role name cannot be blank",
        )

    if await find_role_by_name(role.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A role with that name already exists",
        )

    newdate = datetime.now()
    query = role_table.insert().values(
            name=role.name,
            status='Active',
            description=role.description,
            created=newdate,
            updated=newdate
        )

    #logger.debug(query)
    last_record_id = await database.execute(query)
    data = {**role.model_dump()}
    return {**data, "id": last_record_id}


@router.get("/role", response_model=list[Role], tags=['Role API'])
async def get_all_roles(current_user: Annotated[User, Depends(get_current_user)]):

    urole = await find_role_by_id(current_user.role_id)
    if not urole:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    if urole.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can update roles")

    logger.info("Getting all roles")
    query = role_table.select().where()
    #logger.debug(query)
    return await database.fetch_all(query)


@router.get("/role/{name}", response_model=Role, tags=['Role API'])
async def get_role_with_names(name: str, current_user: Annotated[User, Depends(get_current_user)]):

    urole = await find_role_by_id(current_user.role_id)
    if not urole:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    if urole.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can update roles")

    return await find_role_by_name(name)


@router.patch("/role", response_model=Role, tags=['Role API'])
async def update_role(role: RoleUpdate, current_user: Annotated[User, Depends(get_current_user)]):

    urole = await find_role_by_id(current_user.role_id)
    if not urole:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    if urole.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can update roles")

    if not await find_role_by_id(role.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A role with that ID was not founbd.",
        )
    role2 = await find_role_by_name(role.name)
    if role2.id != role.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A role with that name already exists.",
        )
    logger.info("Updating role with id: {role.id}")
    newdate = datetime.now()
    query = (
        role_table.update().where(role_table.c.id == role.id).values(
            name=role.name, 
            description=role.description, 
            status=role.status,
            updated=newdate
        )
    )
    #logger.debug(query)
    await database.execute(query)
    return await find_role_by_id(role.id)
    

@router.delete("/role", response_model=Role, tags=['Role API'])
async def delete_role(role: Role, current_user: Annotated[User, Depends(get_current_user)]):

    urole = await find_role_by_id(current_user.role_id)
    if not urole:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    if urole.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can deletee roles")

    if not await find_role_by_id(role.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A role with that ID was not founbd.",
        )
    if await find_users_by_role_id(role.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Users with that role ID was founbd.",
        )
 
    logger.info("Deleting role with id: {role.id}")
    query = (
        role_table.delete().where(role_table.c.id == role.id)
    )
    #logger.debug(query)
    await database.execute(query)
    return role


@router.get("/role_by_id/{role_id}", response_model=Role, tags=['Role API'])
async def get_role_by_id(role_id: int, current_user: Annotated[User, Depends(get_current_user)]):
    role = await find_role_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role with that id was not found.",
        )
    return role



