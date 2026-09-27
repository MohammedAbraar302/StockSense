from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    mobile: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        cleaned = "".join(filter(str.isdigit, v))
        if len(cleaned) < 10:
            raise ValueError("Mobile number must contain at least 10 digits")
        return v


class LoginRequest(BaseModel):
    username: str = Field(..., description="Email address or mobile number")
    password: str = Field(..., min_length=1)


class VerifyOTPRequest(BaseModel):
    target_identifier: str = Field(..., description="Email or mobile number where OTP was sent")
    otp_code: str = Field(..., min_length=6, max_length=6)
    purpose: str = Field("REGISTRATION", description="REGISTRATION, LOGIN, or PASSWORD_RESET")


class ResendOTPRequest(BaseModel):
    target_identifier: str
    purpose: str = "REGISTRATION"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    target_identifier: str


class PasswordResetConfirmRequest(BaseModel):
    target_identifier: str
    otp_code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8)
    confirm_password: str

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class UserRoleResponse(BaseModel):
    id: str
    name: str


class UserResponse(BaseModel):
    id: str
    organization_id: str
    email: str
    mobile: Optional[str] = None
    full_name: str
    is_active: bool
    is_verified: bool
    roles: List[str] = []

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
