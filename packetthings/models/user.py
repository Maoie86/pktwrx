from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, model_validator, Field


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int | None = None
    email: str
    role_id: int | None = None


class UserLogin(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: str
    password: str


class UserIn(User):
    model_config = ConfigDict(from_attributes=True)
    email: str
    password: str
    name: str
    # created: datetime = Field(default_factory=lambda: datetime.now())
    # updated: datetime = Field(default_factory=lambda: datetime.now())


class FullUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int | None = None
    email: str
    password: str
    name: str
    status: str
    source: str
    confirmed: bool 
    role_id: int | None = None
    created: datetime = Field(default_factory=lambda: datetime.now())
    updated: datetime = Field(default_factory=lambda: datetime.now())


class ListUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int | None = None
    email: str
    password: str
    name: str
    status: str
    source: str
    role_nm: str
    confirmed: bool
    role_id: int | None = None


class UserUpdate(User):
    model_config = ConfigDict(from_attributes=True)
    name: str
    role_id: int


class ForgetPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    secret_token: str
    new_password: str
    confirm_password: str
    # updated: datetime = Field(default_factory=lambda: datetime.now())


class SuccessMessage(BaseModel):
    success: bool
    status_code: int
    message: str


class AssignTempPassword(BaseModel):
    temp_pwd: str


class UpdateUser(BaseModel):
    id: int 
    email: str
    name: str
    status: str
    confirmed: bool
    role_id: int | None = None


