import logging
import requests
import os
import re
import dns.resolver
import inspect

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette.responses import RedirectResponse
from typing import Annotated
from authlib.integrations.starlette_client import OAuth, OAuthError
from jose import jwt
from fastapi_sso.sso.facebook import FacebookSSO
from pydantic import BaseModel

from starlette.config import Config

from requests_oauthlib import OAuth2Session
from requests_oauthlib.compliance_fixes import facebook_compliance_fix

from packetthings import tasks
from packetthings.config import config
from packetthings.database import(
        database, 
        user_table, 
        location_table, 
        role_table, 
        device_table,
        mydevice_table
)
from packetthings.models.device import LatLong
from packetthings.models.user import (FullUser, 
    ListUser, 
    UpdateUser, 
    User, 
    UserIn, 
    UserLogin, 
    ForgetPasswordRequest, 
    ResetPasswordRequest, 
    AssignTempPassword,
    SuccessMessage
)
from packetthings.security import (
    authenticate_user,
    create_access_token,
    create_confirmation_token,
    create_forgot_password_token,
    get_password_hash,
    get_subject_for_token_type,
    get_user,
    get_current_user,
)
from packetthings.models.location import LocationIn, Location, LocationUpdate


class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None


logger = logging.getLogger(__name__)
router = APIRouter()

GOOGLE_CLIENT_ID = config.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = config.GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI = "https://supabase-dev.packetworx.org:8443/google/auth"
FACEBOOK_CLIENT_ID = config.FACEBOOK_CLIENT_ID
FACEBOOK_CLIENT_SECRET = config.FACEBOOK_CLIENT_SECRET
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

authorization_base_url = 'https://www.facebook.com/dialog/oauth'
token_url = 'https://graph.facebook.com/oauth/access_token'
redirect_uri = 'https://supabase-dev.packetworx.org:8443/facebook/callback'     
state = ""

facebook = OAuth2Session(FACEBOOK_CLIENT_ID, redirect_uri=redirect_uri)
facebook = facebook_compliance_fix(facebook)


def is_valid_domain(email):
    domain = email.split('@')[1]
    try:
        records = dns.resolver.resolve(domain, 'MX')
        return len(records) > 0
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.Timeout):
        return False


def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(pattern, email) is not None


# Example usage
# email = "example@example.com"
# print(is_valid_email(email))  # True or False


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


async def find_user_by_id(user_id: int):
    logger.info(f"Finding user with id: {user_id}")
    query = user_table.select().where(user_table.c.id == user_id)
    #logger.debug(query)
    return await database.fetch_one(query)


async def find_users_by_role_id(role_id: str):
    logger.info(f"Finding user with role : {role_id}")
    query = user_table.select().where(user_table.c.role_id == role_id)
    #logger.debug(query)
    return await database.fetch_all(query)


async def find_users_by_email(email: str):
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user name...",
        )

    if email == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address...",
        )

    if not is_valid_email(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address...",
        )
 
    logger.info(f"Finding user with email: {email}")
    query = user_table.select().where(user_table.c.email == email)
    #logger.debug(query)
    return await database.fetch_one(query)


@router.post("/register", 
        status_code=201, 
        tags=['User API'], 
        summary="Register a new user", 
        description="This endpoint creates a new user.  The user will still need to be verified")
async def register(user: UserIn, background_tasks: BackgroundTasks, request: Request):
    """
    This endpoint creates a new user.  The user will still need to be verified.
    """

    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address...",
        )

    if not user.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user name...",
        )

    if user.email == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address...",
        )

    if not is_valid_email(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address...",
        )

    if await get_user(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that email already exists",
        )

    if not user.password or  user.password == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password.",
        )

    hashed_password = get_password_hash(user.password)

    newdate = datetime.now()
    query = user_table.insert().values(
                email=user.email, 
                name=user.name, 
                source="packetworx",
                status="active",
                role_id=11,
                confirmed=False,
                password=hashed_password,
                created=newdate,
                updated=newdate
            )   

    #logger.debug(query)
    await database.execute(query)
    logger.info("Submitting background task to send email")
    token1=create_confirmation_token(user.email)
    #logger.debug(token1)

    # logger.debug(str(request))
    # confirmation_url1 = request.url_for("confirm_email", email=token1)

    background_tasks.add_task(
        tasks.send_user_registration_email,
        user.email,
        confirmation_url=token1,
    )
    return {"detail": "User created. Please confirm your email.", "toker": token1}


@router.post("/login", tags=['User API'])
async def login(user: UserLogin):
    curframe = inspect.currentframe()
    calframe = inspect.getouterframes(curframe, 2)
    logger.info("User is logging in " + calframe[1][3])
    
    if not is_valid_email(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address...",
        )
    
    user = await authenticate_user(user.email, user.password)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.status != 'active':
        raise HTTPException(status_code=404, detail="User has been deactivated.")

    if user.confirmed == False:
        raise HTTPException(status_code=404, detail="User has not been confirmed.")

    access_token = create_access_token(user.email)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/token", response_model=Token, tags=['User API'])
async def login_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if user.status != 'active':
        raise HTTPException(status_code=404, detail="User has been deactivated.")

    access_token = create_access_token(user.email)
    return {"access_token": access_token, "token_type": "bearer"}



@router.get("/confirm/{token}", tags=['User API'])
async def confirm_email(token: str):

    newdate = datetime.now()
    email = get_subject_for_token_type(token, "confirmation")

    user = await find_users_by_email(email)
    if not user:
        raise HTTPException(status_code=400, detail="Email not found.")

    if user.status != 'active':
        raise HTTPException(status_code=400, detail="User has been deactivated.")

    # if user.confirmed != False:
    #    raise HTTPException(status_code=400, detail="User has already been confirmed.")

    query = (
        user_table.update().where(user_table.c.email == email).values(confirmed=True, 
            updated=newdate)
    )
    #logger.debug(query)
    await database.execute(query)
 
    # add default location for this user
    newdate = datetime.now()
    if user:
        query = location_table.insert().values(
                name="My House",
                user_id=user.id,
                description="My House",
                created=newdate,
                updated=newdate
            )
        #logger.debug(query)
        last_record_id = await database.execute(query)

        if last_record_id:
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

    return {"detail": "User confirmed"}


@router.post("/forgotpassword", status_code=201, tags=['User API'])
async def forgotpassword(user:  ForgetPasswordRequest, 
        background_tasks: BackgroundTasks, 
        request: Request):

    user2 = await get_user(user.email)
    if not user2:
        raise HTTPException(status_code=400, detail="Email not found.")

    if user2.status != 'active':
        raise HTTPException(status_code=400, detail="User has been deactivated.")

    logger.info("Creating Reset Password Token")

    token1=create_forgot_password_token(user.email)
    #logger.debug(token1)

    logger.info("Submitting background task to send email")
    background_tasks.add_task(
        tasks.send_forgot_password_email,
        user.email,
        confirmation_url=token1,
    )
    # return {"detail": "Email sent. Please check your email.", "toker": token1}
    return {"detail": "Email sent. Please check your email."}


@router.post("/resetpassword", status_code=201, tags=['User API'])
async def forgotpassword(user: ResetPasswordRequest, request: Request):

    try:
        logger.info("Resetting Password")

        email = get_subject_for_token_type(user.secret_token, "resetpassword")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Password Reset Payload or Reset Link Expired",
            )

        if not user.new_password or  user.new_password == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid password.",
            )


        if user.new_password != user.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password and confirm password are not same.",
            )

        hashed_password = get_password_hash(user.new_password)
        newdate = datetime.now()
        query = (
            user_table.update().where(user_table.c.email == email).values(
                password=hashed_password,
                updated=newdate
            )       
        )

        #logger.debug(query)
        await database.execute(query)
        #logger.debug("Password has been updated.")
        return {'success': True, 'status_code': status.HTTP_200_OK, 'message': 'Password Reset Successfull!'}

    except Exception as e:
        raise HHTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail="Some thing unexpected happened!")


@router.get("/google/login", tags=['Google SSO'])
async def login_google():
    return {
        "url": f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope=openid%20profile%20email&access_type=offline"
    }


@router.get("/google/auth", tags=['Google SSO'])
async def auth_google(code: str):
    token_url = "https://accounts.google.com/o/oauth2/token"
    logger.info("code:  " + code)
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    response = requests.post(token_url, data=data)

    access_token = response.json().get("access_token")
    user_info = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"})
    user_json = user_info.json()

    value = user_json.get('email')
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address not found is response",
        )

    name = user_json.get('name')
    if name is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name cannot be blank",
        )

    if not is_valid_email(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address...",
        )

    if await get_user(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that email already exists",
        )

    user = UserIn(email=user_json['email'], 
        password="1423F4$f!@SeFEdfpPIjbMTaard886986ErERerer",
        name=user_json['name']
    )
    hashed_password = get_password_hash(user.password)
    pktwrx_access_token = create_access_token(value)
    
    query = user_table.insert().values(
                name=user.name,
                email=user_json['email'],
                source="google",
                status="active",
                role_id=10,
                confirmed=True,
                password=hashed_password,
                created=user.created,
                updated=user.updated
            )
    #logger.debug(query)
    await database.execute(query)
    return {"pktworx_token": pktwrx_access_token, "google_access_token": access_token, **user_json}



@router.get("/google/token", tags=['Google SSO'])
async def google_token(token: str = Depends(oauth2_scheme)):
    return jwt.decode(token, GOOGLE_CLIENT_SECRET, algorithms=["HS256"])


facebook_sso = FacebookSSO(
    FACEBOOK_CLIENT_ID,
    FACEBOOK_CLIENT_SECRET,
    "https://supabase-dev.packetworx.org:8443/facebook/callback",
    allow_insecure_http=True
)

@router.get("/facebook/login", tags=['Facebook SSO'])
async def facebook_login():
    # authorization_url = await facebook_sso.get_login_redirect()
    # return authorization_urli
    global state
    authorization_url, state = facebook.authorization_url(authorization_base_url)
    print(state)
    # return await facebook_sso.get_login_redirect()
    return authorization_url 


@router.get("/facebook/callback", tags=['Facebook SSO'])
# async def facebook_callback(request: Request):
async def facebook_callback(code: str):
    try:
        global state
        #logger.debug(code)
        #logger.debug("state: " + state)

        # user = await facebook_sso.verify_and_process(request)
        # return user

        redirect_response = redirect_uri + "?code=" + code + "&state=" + state +  "#_=_"
        #logger.debug(redirect_response)

        facebook.fetch_token(token_url, client_secret=client_secret,
                             authorization_response=redirect_response)

        # Fetch a protected resource, i.e. user profile
        #logger.debug("state: " + state)
        r = facebook.get('https://graph.facebook.com/me?')
        #logger.debug("content:  " + r.content)


        return code
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail="Some thing unexpected happened!")


@router.get("/whoami", response_model=FullUser, status_code=201, tags=['User API'])
async def get_whoami(current_user: Annotated[User, Depends(get_current_user)]):
    curframe = inspect.currentframe()
    calframe = inspect.getouterframes(curframe, 2)
    logger.info("Getting user details whoami from " + calframe[1][3])
    try:
        #logger.debug(current_user)
        if await get_user(current_user.email):
            #logger.info("User with email found")
            query = user_table.select().where(user_table.c.id == current_user.id)
            #logger.debug(query)
            return await database.fetch_one(query)
        else:
            #logger.info("User with email not found")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with that email does not exist",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that email does not exist",
        )


@router.get("/renewtoken", status_code=201, tags=['User API'])
async def get_new_token(current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Getting new bearer token")
    try:
        #logger.debug(current_user)
        access_token = create_access_token(current_user.email)
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token",
        )


@router.post("/adduser", status_code=201, tags=['User API'])
async def add_user(user: UserIn, 
	background_tasks: BackgroundTasks, 
	request: Request,
	current_user: Annotated[User, Depends(get_current_user)]):

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")

    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can add Users")

    if await get_user(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that email already exists",
        )
    hashed_password = get_password_hash(user.password)

    newdate = datetime.now()
    query = user_table.insert().values(
                email=user.email,
                name=user.name,
                source="packetworx",
                confirmed=False,
                status="active",
                role_id=user.role_id,
                password=hashed_password,
                created=newdate,
                updated=newdate
            )

    #logger.debug(query)
    await database.execute(query)
    logger.info("Submitting background task to send email")
    token1=create_confirmation_token(user.email)
    #logger.debug(token1)

    background_tasks.add_task(
        tasks.send_user_registration_email,
        user.email,
        confirmation_url=token1,
    )
    return {"detail": "User created. Please confirm your email.", "toker": token1}



@router.delete("/user/{email}", response_model=User, tags=['User API'])
async def delete_user(email: str,
        current_user: Annotated[User, Depends(get_current_user)]):

    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")
    if role.name != 'Admin':
        raise HTTPException(status_code=400, detail="Only Admins can delete users")

    user = await find_users_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that email was not found.",
        )

    # check mydevices
    logger.info("Deleting mydevice of this user")
    query = (
        mydevice_table.delete().where(mydevice_table.c.user_id == user.id)
    )
    #logger.debug(query)
    await database.execute(query)

    # check devices
    newdate = datetime.now()
    logger.info("Releasing devices of this user")
    query = (
        device_table.update().where(device_table.c.user_id == user.id).values(
            user_id = 0,
            location_id = 1,
            updated=newdate
        )
    )
    #logger.debug(query)
    await database.execute(query)

    # check locations
    logger.info("Deleting location of this user")
    query = (
        location_table.delete().where(location_table.c.user_id == user.id)
    )
    #logger.debug(query)
    await database.execute(query)


    logger.info("Deleting user with email: " + user.email)
    query = (
        user_table.delete().where(user_table.c.id == user.id)
    )
    #logger.debug(query)
    await database.execute(query)
    return user
        
# response_model=list[FullUser],


@router.get("/users",
        response_model=list[ListUser],
        tags=['User API'],
        description="This API returns all the registered users.")
async def get_all_users(current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Getting all users")
    role = await find_role_by_id(current_user.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Current user has undefined role")

    if role.name != 'Admin':
        query = user_table.select().where(
                    user_table.c.id==current_user.id
                ).order_by(user_table.c.id)
    else:
        query = user_table.select().where().order_by(user_table.c.id)

    #logger.debug(query)
    dtls = await database.fetch_all(query)
    users = []
    if dtls:
        for dtl in dtls:
            if dtl.id > 0:
                role = await find_role_by_id(dtl.role_id)
                role_nm = "Unknown Role"
                if role:
                    role_nm = role.name

                lastuser = ListUser(id = dtl.id,
                        email = dtl.email,
                        password = "******",
                        role_nm = role_nm,
                        name = dtl.name,
                        source = dtl.source,
                        status =  dtl.status,
                        confirmed = dtl.confirmed,
                        role_id = dtl.role_id)
                users.append(lastuser)
    return users


@router.get("/", status_code=201, tags=['User API'])
async def get_home(current_user: Annotated[User, Depends(get_current_user)]):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Bad Request",
    )


@router.post("/", status_code=201, tags=['User API'])
async def post_home(current_user: Annotated[User, Depends(get_current_user)]):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Bad Request",
    )



@router.patch("/user", response_model=User, tags=['User API'])
async def update_user(user: UpdateUser,
        current_user: Annotated[User, Depends(get_current_user)]):

    current_role = await find_role_by_id(current_user.role_id)
    if not current_role:
        raise HTTPException(status_code=404, detail="Current user has undefined role")
    if current_role.name != 'Admin':
        if current_user.id != user.id:
            raise HTTPException(status_code=400, detail="Only Admins can update users")
        if current_user.role_id != user.role_id:
            raise HTTPException(status_code=400, detail="Only Admins can assign roles")

    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address...",
        )

    if user.email == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address...",
        )

    if not is_valid_email(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address...",
        )

    if not user.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user name...",
        )

    role = await find_role_by_id(user.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Invalid user role")

    user2 = await find_user_by_id(user.id)
    if not user2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that id was not found.",
        )

    confirmed = user2.confirmed
    if user.email != user2.email:
        user3 = await find_users_by_email(user.email)
        if user3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with that email already exists.",
            )
        confirmed = false

    logger.info("Updating with id: {user.id")
    newdate = datetime.now()
    query = (
        user_table.update().where(user_table.c.id == user2.id).values(
            name=user.name,
            email=user.email,
            role_id=user.role_id,
            status=user.status,
            confirmed=confirmed,
            updated=newdate
        )
    )

    #logger.debug(query)
    await database.execute(query)
    return user


@router.post("/UserOp", status_code=201, tags=['User API'])
async def post_userop(current_user: Annotated[User, Depends(get_current_user)]):
    raise HTTPException(
        status_code=201,
        detail="Work in Process",
    )



