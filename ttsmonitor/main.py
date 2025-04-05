from fastapi import FastAPI, HTTPException
from database import dbdatabase, dbengine, dbmetadata
from models import gwdata, tagsdata, GWSUpdate
from sqlalchemy import select, and_, delete, update, or_, func, join
from sqlalchemy.orm import aliased


app = FastAPI()

dbmetadata.create_all(dbengine)

@app.on_event("startup")
async def startup():
    await dbdatabase.connect()

@app.on_event("shutdown")
async def shutdown():
    await dbdatabase.disconnect()



@app.get("/gws", tags=['TTS API'])
async def get_gws():

    query = (
        select(
            gwdata.c.id,
            gwdata.c.name,
            gwdata.c.latitude,
            gwdata.c.longitude,
            gwdata.c.monitoring_on,
            func.count(tagsdata.c.gateway_id).label("tags")
        )
        .select_from(gwdata.outerjoin(tagsdata, gwdata.c.id == tagsdata.c.gateway_id))
        .group_by(gwdata.c.id)
    )

    # query = select([gwdata]).where(gwdata.c.id != '')
    gws = await dbdatabase.fetch_all(query)
    if gws is None:
        raise HTTPException(status_code=404, detail="No gateways found")
    return gws



@app.get("/gwsid/{gw_id}", tags=['TTS API'])
async def get_gws_id(gw_id: str):
    query = select(gwdata).where(gwdata.c.id == gw_id)
    gws = await dbdatabase.fetch_one(query)
    if gws is None:
        raise HTTPException(status_code=404, detail="No gateways found")
    return gws


@app.patch("/monitor", tags=['TTS API'])
async def monitor_gws_id(gwsupd: GWSUpdate):
    query = select(gwdata).where(gwdata.c.id == gwsupd.id)
    gws = await dbdatabase.fetch_one(query)
    if gws is None:
        raise HTTPException(status_code=400, detail="No gateways found")

    query = gwdata.update().where(gwdata.c.id == gwsupd.id).values(monitoring_on=True)
    await dbdatabase.execute(query)

    return  {"detail": "Monitored", "id": gwsupd.id}



@app.patch("/unmonitor", tags=['TTS API'])
async def unmonitor_gws_id(gwsupd: GWSUpdate):
    query = select(gwdata).where(gwdata.c.id == gwsupd.id)
    gws = await dbdatabase.fetch_one(query)
    if gws is None:
        raise HTTPException(status_code=400, detail="No gateways found")

    query = gwdata.update().where(gwdata.c.id == gwsupd.id).values(monitoring_on=False)
    await dbdatabase.execute(query)

    return  {"detail": "Unmonitored", "id": gwsupd.id}


@app.post("/tags", tags=['TTS API'])
async def get_tags_id(gwsupd: GWSUpdate):
    query = select(tagsdata).where(
            tagsdata.c.gateway_id == gwsupd.id).order_by(tagsdata.c.tag)
    tags = await dbdatabase.fetch_all(query)
    if tags is None:
        raise HTTPException(status_code=404, detail="No tags for this gateway was found")
    return tags




@app.post("/tags/{gw_id}/{tag}", tags=['TTS API'])
async def add_tags_id(gw_id: str, ntag: str):
    query = select(gwdata).where(gwdata.c.id==gw_id)
    gws = await dbdatabase.fetch_one(query)
    if gws is None:
        raise HTTPException(status_code=404, detail="No gateways found")

    query = tagsdata.insert().values(
        gateway_id=gw_id,
        tag=ntag
    )
    await dbdatabase.execute(query)
    return {"detail": "Added", "id": gw_id, "tag": ntag}





@app.delete("/tags/{gw_id}/{tag}", tags=['TTS API'])
async def del_tags_id(gw_id: str, ntag: str):
    query = select(gwdata).where(gwdata.c.id==gw_id)
    gws = await dbdatabase.fetch_one(query)
    if gws is None:
        raise HTTPException(status_code=404, detail="No gateways found")

    query = select(tagsdata).where(and_(tagsdata.c.gateway_id==gw_id, tagsdata.c.tag==ntag))
    tags = await dbdatabase.fetch_one(query)
    if tags is None:
        raise HTTPException(status_code=404, detail="This tag for this gateway was not found")

    # Delete the user
    query = (
            tagsdata.delete().where(
                and_(tagsdata.c.gateway_id == gw_id, tagsdata.c.tag == ntag))
            )
    await dbdatabase.execute(query)

    return {"detail": "Deleted", "id": gw_id, "tag": ntag}



