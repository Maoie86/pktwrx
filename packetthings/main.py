import pathlib
import logging
import os
import psycopg2
import uuid

from psycopg2 import sql
from contextlib import asynccontextmanager

from asgi_correlation_id import CorrelationIdMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, HTTPException, Depends, APIRouter, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html

from packetthings.config import config
from packetthings.dbscylla import get_session
from packetthings.database import database
from packetthings.dbpg import get_db_connection
from packetthings.logging_conf import configure_logging
from packetthings.routers.post import router as post_router
from packetthings.routers.user import router as user_router
from packetthings.routers.packet import router as packet_router
from packetthings.routers.device import router as device_router
from packetthings.routers.role import router as role_router
from packetthings.routers.unit import router as unit_router
from packetthings.routers.type import router as type_router
from packetthings.routers.typedetail import router as typedetail_router
from packetthings.routers.measurement import router as measurement_router
from packetthings.routers.location import router as location_router
from packetthings.routers.mydevice import router as mydevice_router
from packetthings.routers.otp import router as otp_router
from packetthings.routers.notify import router as notify_router
from packetthings.routers.rawjson import router as rawjson_router

from prometheus_fastapi_instrumentator import Instrumentator

logger = logging.getLogger(__name__)

# Define CORS settings
origins = ["*"]  # Allow requests from any origin

# pgconn = None
# pgconn = get_db_connection()
# pgcursor = conn.cursor()

# main_router = APIRouter()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up")
    configure_logging()
    await database.connect()
    yield
    await database.disconnect()
    print("Shutting down")

app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Check if the request has a correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        # If not, generate a new correlation ID
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        # Store the correlation ID in the request state for further use
        request.state.correlation_id = correlation_id
        # Proceed with the request and get the response
        response = await call_next(request)
        # Attach the correlation ID to the response headers
        response.headers["X-Correlation-ID"] = correlation_id
        return response
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(SessionMiddleware, secret_key="Packetworx Packet Things...")

app.add_middleware(HTTPSRedirectMiddleware)

# app.include_router(post_router)
app.include_router(user_router)
app.include_router(packet_router)
app.include_router(device_router)
app.include_router(role_router)
app.include_router(unit_router)
app.include_router(type_router)
app.include_router(typedetail_router)
app.include_router(measurement_router)
app.include_router(location_router)
app.include_router(mydevice_router)
app.include_router(otp_router)
app.include_router(notify_router)
app.include_router(rawjson_router)
# app.include_router(main_router)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

print(BASE_DIR)
print(UPLOAD_DIR)

@app.exception_handler(HTTPException)
async def http_exception_handle_logging(request, exc):
    logger.error(f"HTTPException: {exc.status_code} {exc.detail}")
    return await http_exception_handler(request, exc)


Instrumentator().instrument(app).expose(app, tags=["Prometheus"])


@app.on_event("startup")
async def _startup():
    instrumentator.expose(app)
    # global pgconn
    # pgconn = get_db_connection()
    # print("Database connection established")

#app.mount("/static", StaticFiles(directory="static"), name="static")

## Custom Swagger UI settings
#@app.get("/docs", include_in_schema=False)
#async def custom_swagger_ui_html():
#    return get_swagger_ui_html(
#        openapi_url=app.openapi_url,
#        title=app.title + " - Swagger UI PktWrx",
#        oauth2_redirect_url=app.oauth2_redirect_url,
#        custom_js_url="/static/collapse-tags.js"
#    )


# Event handler to disconnect from the database upon shutdown
#@app.on_event("shutdown")
#async def _shutdown():
#    global pgconn
#    if pgconn:
#        pgconn.close()
#        print("Database connection closed")

# Dependency to get the database cursor
#def get_cursor():
#    global pgconn
#    if pgconn is None:
#        print("Database connection is not established")
#        return {"Error":"conn is none"}
#    cursor = pgconn.cursor()
#    try:
#        yield cursor
#    finally:
#        cursor.close()


#@app.get("/pgdirect", tags=['Device API'])
#async def read_users(cursor: psycopg2.extensions.cursor = Depends(get_cursor)):
#    cursor.execute("SELECT * FROM users;")
#    users = cursor.fetchall()
#    return {"users": users}

