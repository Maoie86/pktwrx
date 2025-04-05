from fastapi import FastAPI, HTTPException
from database import dbdatabase, dbengine, dbmetadata
from models import gwdata, tagsdata, GWSUpdate, GetTags, AddTag
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


@app.get("/gws", tags=['Actility API'])
async def get_gws():

    query = (
        select(
            gwdata.c.lrr_id,
            gwdata.c.lrr_uuid,
            gwdata.c.name,
            gwdata.c.lat,
            gwdata.c.lon,
            gwdata.c.monitored,
            func.count(tagsdata.c.lrr_id).label("tags")
        )
        .select_from(gwdata.outerjoin(tagsdata, gwdata.c.lrr_id == tagsdata.c.lrr_id))
        .group_by(gwdata.c.lrr_uuid)
    )
    # print(query)
    gws = await dbdatabase.fetch_all(query)
    if gws is None:
        raise HTTPException(status_code=404, detail="No gateways found")
    return gws


@app.get("/gwsid/{lrr_uuid}", tags=['Actility API'])
async def get_gws_lrruuid(lrr_uuid: str):
    query = select([gwdata]).where(gwdata.c.lrr_uuid == lrr_uuid)
    gws = await dbdatabase.fetch_one(query)
    if gws is None:
        raise HTTPException(status_code=404, detail="No gateways found")
    return gws


@app.patch("/monitor", tags=['Actility API'])
async def monitor_gws_lrr_uuid(gwsupd: GWSUpdate):
    query = select([gwdata]).where(gwdata.c.lrr_uuid == gwsupd.lrr_uuid)
    gws = await dbdatabase.fetch_one(query)
    if gws is None:
        raise HTTPException(status_code=400, detail="No gateways found")
    query = gwdata.update().where(gwdata.c.lrr_uuid == gwsupd.lrr_uuid).values(monitored=True)
    await dbdatabase.execute(query)
    return  {"detail": "Monitored", "lrr_uuid": gwsupd.lrr_uuid}


@app.patch("/unmonitor", tags=['Actility API'])
async def unmonitor_gws_lrr_uuid(gwsupd: GWSUpdate):
    query = select([gwdata]).where(gwdata.c.lrr_uuid == gwsupd.lrr_uuid)
    gws = await dbdatabase.fetch_one(query)
    if gws is None:
        raise HTTPException(status_code=404, detail="No gateways found")
    query = gwdata.update().where(gwdata.c.lrr_uuid == gwsupd.lrr_uuid).values(monitored=False)
    await dbdatabase.execute(query)
    return  {"detail": "Unmonitored", "lrr_uuid": gwsupd.lrr_uuid}


@app.post("/tags", tags=['Actility API'])
async def get_tags_lrr_id(gettags: GetTags):
    query = select([tagsdata]).where(
            tagsdata.c.lrr_id == gettags.lrr_id).order_by(tagsdata.c.tag)
    # tags = []
    tags = await dbdatabase.fetch_all(query)
    if tags is None:
        raise HTTPException(status_code=404, detail="No tags for this gateway was found")
    return tags


@app.post("/addtag", tags=['Actility API'])
async def add_tags(newtag: AddTag):

    lrrid = newtag.lrr_id.strip()
    if lrrid == "":
        raise HTTPException(status_code=400, detail="Blank LRR_ID")

    ntag = newtag.tag.strip()
    if ntag == "":
        raise HTTPException(status_code=400, detail="Blank tag")

    query = select([gwdata]).where(gwdata.c.lrr_id == lrrid)
    gws = await dbdatabase.fetch_all(query)
    if gws is None:
        raise HTTPException(status_code=404, detail="No gateways found")

    query = select([tagsdata]).where(and_(tagsdata.c.lrr_id == lrrid, tagsdata.c.tag == ntag))
    tag = await dbdatabase.fetch_all(query)
    if tag:
        raise HTTPException(status_code=400, detail="Tag already exists")

    query = tagsdata.insert().values(
        lrr_id=lrrid,
        tag=ntag
    )
    await dbdatabase.execute(query)
    return {"detail": "Added", "lrr_id": lrrid, "tag": ntag}


@app.delete("/deltag", tags=['Actility API'])
async def del_tags(deltag: AddTag):

    lrrid = deltag.lrr_id.strip()
    if lrrid == "":
        raise HTTPException(status_code=400, detail="Blank LRR_ID")

    ntag = deltag.tag.strip()
    if ntag == "":
        raise HTTPException(status_code=400, detail="Blank tag")

    query = select([gwdata]).where(gwdata.c.lrr_id == lrrid)
    gws = await dbdatabase.fetch_all(query)
    if gws is None:
        raise HTTPException(status_code=404, detail="No gateways found")

    query = select([tagsdata]).where(and_(tagsdata.c.lrr_id == lrrid, tagsdata.c.tag == ntag))
    tags = await dbdatabase.fetch_one(query)
    if tags is None:
        raise HTTPException(status_code=404, detail="This tag for this gateway was not found")

    # Delete the user
    query = tagsdata.delete().where(and_(tagsdata.c.lrr_id==lrrid, tagsdata.c.tag==ntag))
    await dbdatabase.execute(query)

    return {"detail": "Deleted", "lrr_id": lrrid, "tag": ntag}



