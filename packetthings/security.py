import datetime
import logging
from dateutil.relativedelta import relativedelta

from packetthings.config import config
from packetthings.database import database, user_table

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from typing import Annotated, Literal
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

SECRET_KEY = config.SECRET_KEY
ALGORITHM = config.ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"])


def create_unauthorized_exception(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def access_token_expire_minutes() -> int:
    return 300

def confirm_token_expire_minutes() -> int:
    return 120


def create_access_token(email: str):
    logger.debug("Creating access token", extra={"email": email})
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=access_token_expire_minutes()
    )
    jwt_data = {"sub": email, "exp": expire, "type": "access"}
    encoded_jwt = jwt.encode(jwt_data, key=SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_confirmation_token(email: str):
    logger.debug("Creating access token", extra={"email": email})
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=confirm_token_expire_minutes()
    )
    jwt_data = {"sub": email, "exp": expire, "type": "confirmation"}
    encoded_jwt = jwt.encode(jwt_data, key=SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_forgot_password_token(email: str):
    logger.debug("Creating reset password token", extra={"email": email})
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=confirm_token_expire_minutes()
    )
    jwt_data = {"sub": email, "exp": expire, "type": "resetpassword"}
    encoded_jwt = jwt.encode(jwt_data, key=SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_deviceregister_token(dev_eui: str):
    logger.debug("Creating device token", extra={"email": dev_eui})
    # expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=18000)
    expire = datetime.datetime.now(datetime.timezone.utc) + relativedelta(years=10)
    jwt_data = {"sub": dev_eui, "exp":expire, "type": "devicetoken"}
    encoded_jwt = jwt.encode(jwt_data, key=SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_subject_for_token_type(
    token: str, 
    type: Literal["access", 
        "confirmation", 
        "resetpassword", 
        "devicetoken"]
) -> str:

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError as e:
        raise create_unauthorized_exception("Token has expired") from e
    except JWTError as e:
        raise create_unauthorized_exception("Invalid token") from e

    email = payload.get("sub")
    if email is None:
        raise create_unauthorized_exception("Token is missing 'sub' field")

    token_type = payload.get("type")
    if token_type is None or token_type != type:
        raise create_unauthorized_exception(
            f"Token has incorrect type, expected '{type}'"
        )
    return email


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


async def get_user(email: str):
    #logger.debug("Fetching user from the database", extra={"email": email})
    query = user_table.select().where(user_table.c.email == email)
    # logger.debug(query)
    result = await database.fetch_one(query)
    if result:
        return result


async def authenticate_user(email: str, password: str):
    logger.debug("Authenticating user", extra={"email": email})
    user = await get_user(email)
    if not user:
        raise create_unauthorized_exception("Invalid email or password")
    if not verify_password(password, user.password):
        raise create_unauthorized_exception("Invalid email or password")
    if not user.confirmed:
        raise create_unauthorized_exception("User has not confirmed email")
    if user.status != 'active':
        raise create_unauthorized_exception("User has been deactivated")
    return user


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    #logger.debug("Getting current user.")
    email = get_subject_for_token_type(token, "access")
    user = await get_user(email=email)
    if user is None:
        raise create_unauthorized_exception("Could not find user for this token")
    # logger.debug(user)
    return user


