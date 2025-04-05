import logging
import sqlalchemy
import json
import google.generativeai as genai
from typing import Annotated

from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query

# from packetthings.database import packet_table
from packetthings.dbscylla import get_session
from packetthings.models.rawjson import RawJson
from packetthings.models.user import User, SuccessMessage

from packetthings.security import (
        get_current_user,
        create_deviceregister_token,
        get_subject_for_token_type)


router = APIRouter()
session = get_session()

#        response_model=list[RawJson], 

@router.get("/rawjson/{device_name}/{yymmdd}", 
        tags=['RawJson API'])
async def get_rawjson(device_name: str, 
        yymmdd: str):

    sql_tx = "SELECT * FROM rawjson_data WHERE device_name = "
    sql_tx = sql_tx + " '" + device_name + "' "
    sql_tx = sql_tx + "AND yymmdd = " + yymmdd + " "
    rows = session.execute(sql_tx)
    retjson = []
    if rows.current_rows:
        retjson = rows.current_rows
    return retjson



genai.configure(api_key="AIzaSyBvWrfe3rEfPd_ya5YTrSu97fW5ZbGAl9c")
# model = genai.GenerativeModel("gemini-1.5-flash")
model = genai.GenerativeModel("gemini-2.0-flash")

@router.post("/chat/", 
        tags=['Gemini Chatbot'])
async def chat(input_text: str,  current_user: Annotated[User, Depends(get_current_user)]):
    response = model.generate_content(input_text)
    print(response.usage_metadata)
    return {"response": response.text, 
            "ptc": response.usage_metadata.prompt_token_count,
            "ctc": response.usage_metadata.candidates_token_count,
            "ttc": response.usage_metadata.total_token_count,
            }



