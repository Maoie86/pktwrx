from fastapi import FastAPI, HTTPException, Depends, APIRouter, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html

from rawjson import router as rawjson_router

app = FastAPI()

app.include_router(rawjson_router)


