import logging
import random
import string
import uuid

from enum import Enum
from typing import Annotated
from datetime import datetime, timezone

import sqlalchemy
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, status

from packetthings import tasks
from packetthings.dbscylla import get_session
from packetthings.database import database, user_table, location_table
from packetthings.models.otp import OTP, RequestOTP, OTPType, ChangePasswordOTP, VerifyEmailOTP
from packetthings.models.user import User
from packetthings.security import (
    create_access_token,
    create_confirmation_token,
    create_forgot_password_token,
    get_user,
    get_current_user,
    get_password_hash,
)
from packetthings.models.location import LocationIn, Location, LocationUpdate


router = APIRouter()

logger = logging.getLogger(__name__)
session = get_session()


def generate_otp():
    length = 6
    return ''.join(random.choices(string.digits, k=length))



@router.post("/get_otp", tags=['OTP API'])
async def get_otp(req_otp: RequestOTP, background_tasks: BackgroundTasks):

    logger.info(f"Geneating OTP for email {req_otp.email}")
    if req_otp.email:
        logger.info(f"Geneating OTP for email {req_otp.email}")
        user = await get_user(req_otp.email)
        if user:

            otp = generate_otp()
            if req_otp.otp_type == OTPType.verifyemail:
                token = create_confirmation_token(user.email)
            else:
                if req_otp.otp_type == OTPType.forgotpassword:
                    token = create_forgot_password_token(user.email)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid token type.",
                    )

            sql = "INSERT INTO otp_data(otp, email, session, type)"
            sql = sql + " values('" + otp + "', '" + user.email + "', '" + token + "', '" + req_otp.otp_type + "') USING TTL 300 "
            session.execute(sql)

            background_tasks.add_task(
                tasks.send_otp_email,
                user.email,
                otp=otp,
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with that email does not exist.",
            )
    
    return {'detail': 'Sent', 'token': token}



@router.post("/forgotpassword_otp", tags=['OTP API'])
async def forgotpassword_otp(req_otp: ChangePasswordOTP):

    logger.info(f"Forgot password OTP for email {req_otp.email}")

    user = await get_user(req_otp.email)
    if user:
        sql_tx = "SELECT * FROM otp_data WHERE otp = '" + req_otp.otp + "' "
        sql_tx = sql_tx + "AND email = '" + user.email + "' "
        sql_tx = sql_tx + "AND type = '" + OTPType.forgotpassword + "'; "
        logger.info(sql_tx)
        rows = session.execute(sql_tx)

        if len(rows.current_rows) > 0:
            if rows.current_rows[0]['session'] == req_otp.token:
                # extra checking, token should be the same in
                hashed_password = get_password_hash(req_otp.newpassword)
                updated = user.updated
                query = (
                    user_table.update().where(user_table.c.email == user.email).values(
                        password=hashed_password,
                        updated=updated
                    )
                )

                logger.debug(query)
                await database.execute(query)
                logger.debug("Password has been reset.")
                return {'success': True,
                        'status_code': status.HTTP_200_OK,
                        'message': 'Password Reset Successfull!'}
            else:
                logger.info("Wrong OTP or Expired OTP...")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token.",
                )
        else: 
            logger.info("Wrong OTP or Expired OTP...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that email does not exist.",
        )

    return "Unknow Error"



@router.post("/verifyemail_otp", tags=['OTP API'])
async def verifyemail_otp(req_otp: VerifyEmailOTP):

    logger.info(f"Email Verification  OTP for email {req_otp.email}")

    user = await get_user(req_otp.email)
    if user:
        sql_tx = "SELECT * FROM otp_data WHERE otp = '" + req_otp.otp + "' "
        sql_tx = sql_tx + "AND email = '" + user.email + "' "
        sql_tx = sql_tx + "AND type = '" + OTPType.verifyemail + "'; "
        logger.info(sql_tx)
        rows = session.execute(sql_tx)

        if len(rows.current_rows) > 0:
            if rows.current_rows[0]['session'] == req_otp.token:
                # extra checking, token should be the same in
                updated = user.updated
                query = (
                    user_table.update().where(user_table.c.email == user.email).values(confirmed=True)
                    )
                logger.debug(query)
                await database.execute(query)
                logger.debug("Email has been verified.")

                newdate = datetime.now()

                query = location_table.insert().values(
                        name="My House",
                        user_id=user.id,
                        description="My House",
                        created=newdate,
                        updated=newdate
                )
                logger.debug(query)
                last_record_id = await database.execute(query)

                query = location_table.insert().values(
                        name="Living Room",
                        user_id=user.id,
                        location_id=last_record_id,
                        description="Living Room",
                        created=newdate,
                        updated=newdate
                    )
                last_id = await database.execute(query)

                query = location_table.insert().values(
                        name="Kitchen",
                        user_id=user.id,
                        location_id=last_record_id,
                        description="Kitchen",
                        created=newdate,
                        updated=newdate
                    )
                last_id = await database.execute(query)

                query = location_table.insert().values(
                        name="Dining Hall",
                        user_id=user.id,
                        location_id=last_record_id,
                        description="Dining Hall",
                        created=newdate,
                        updated=newdate
                    )
                last_id = await database.execute(query)

                query = location_table.insert().values(
                        name="Bed Room",
                        user_id=user.id,
                        location_id=last_record_id,
                        description="Bed Room",
                        created=newdate,
                        updated=newdate
                    )
                last_id = await database.execute(query)

                query = location_table.insert().values(
                        name="Parking",
                        user_id=user.id,
                        location_id=last_record_id,
                        description="Parking",
                        created=newdate,
                        updated=newdate
                    )
                last_id = await database.execute(query)

                query = location_table.insert().values(
                        name="Basement",
                        user_id=user.id,
                        location_id=last_record_id,
                        description="Basement",
                        created=newdate,
                        updated=newdate
                    )
                last_id = await database.execute(query)

                return {'success': True,
                        'status_code': status.HTTP_200_OK,
                        'message': 'Email Verification Successfull!'}
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token.",
                )
        else:
            logger.info("Wrong OTP or Expired OTP...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that email does not exist.",
        )

    return "Unknow Error"


