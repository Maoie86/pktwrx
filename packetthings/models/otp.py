from pydantic import BaseModel, ConfigDict
import datetime
from enum import Enum

class OTPType(str, Enum):
    verifyemail = "verify"
    forgotpassword = "change"


class OTP(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    otp: str
    email: str


class RequestOTP(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: str
    otp_type: OTPType


class VerifyEmailOTP(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: str
    otp: str
    otp_type: OTPType
    token: str


class ChangePasswordOTP(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: str
    otp: str
    otp_type: OTPType
    token: str
    newpassword: str



