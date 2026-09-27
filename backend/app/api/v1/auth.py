from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    VerifyOTPRequest,
    ResendOTPRequest,
    RefreshTokenRequest,
    UserResponse,
    TokenResponse,
)
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService
from app.services.otp_service import OTPService
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=MessageResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Onboard a new user, validate unique email and mobile, and dispatch a 6-digit verification OTP.
    """
    try:
        user, raw_otp = await AuthService.register_user(
            db=db,
            full_name=req.full_name,
            email=req.email,
            mobile=req.mobile,
            password=req.password
        )
        return MessageResponse(
            message=f"Registration initiated. Verification OTP sent to {user.email}.",
            data={"target_identifier": user.email, "dev_otp": raw_otp}
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


from typing import List
from sqlalchemy import select
from app.models.user import Role, UserRole

async def get_user_role_names(db: AsyncSession, user_id: str) -> List[str]:
    stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user_id)
    return list((await db.execute(stmt)).scalars().all())


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_registration_otp(req: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    """
    Verify registration OTP, activate user account, and issue initial session tokens.
    """
    try:
        user = await AuthService.verify_registration(
            db=db,
            target_identifier=req.target_identifier,
            otp_code=req.otp_code
        )
        # Login verified user
        user, access_token, refresh_token = await AuthService.complete_login_with_otp(
            db=db,
            username=user.email,
            otp_code=req.otp_code
        )
        roles = await get_user_role_names(db, user.id)
        user_resp = UserResponse(
            id=user.id,
            organization_id=user.organization_id,
            email=user.email,
            mobile=user.mobile,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            roles=roles
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=120 * 60,
            user=user_resp
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/resend-otp", response_model=MessageResponse)
async def resend_otp(req: ResendOTPRequest, db: AsyncSession = Depends(get_db)):
    """
    Resend OTP to candidate email or mobile with cooldown enforcement.
    """
    try:
        clean_target = req.target_identifier.lower().strip()
        raw_otp = await OTPService.create_and_send_otp(db, clean_target, purpose=req.purpose)
        return MessageResponse(
            message=f"A new OTP has been dispatched to {clean_target}.",
            data={"dev_otp": raw_otp}
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=MessageResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Step 1 of 2FA Login: validate password and dispatch 2FA OTP code.
    """
    try:
        user, raw_otp = await AuthService.authenticate_and_send_login_otp(
            db=db,
            username=req.username,
            password=req.password
        )
        return MessageResponse(
            message=f"Credentials verified. 2FA Login OTP dispatched to {user.email}.",
            data={"target_identifier": user.email, "dev_otp": raw_otp}
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/login/verify-otp", response_model=TokenResponse)
async def verify_login_otp(req: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    """
    Step 2 of 2FA Login: verify login OTP and issue JWT access and refresh tokens.
    """
    try:
        user, access_token, refresh_token = await AuthService.complete_login_with_otp(
            db=db,
            username=req.target_identifier,
            otp_code=req.otp_code
        )
        roles = await get_user_role_names(db, user.id)
        user_resp = UserResponse(
            id=user.id,
            organization_id=user.organization_id,
            email=user.email,
            mobile=user.mobile,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            roles=roles
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=120 * 60,
            user=user_resp
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """
    Refresh access token with refresh token rotation.
    """
    try:
        access_token, new_refresh_token, user = await AuthService.rotate_refresh_token(
            db=db,
            raw_refresh_token=req.refresh_token
        )
        roles = await get_user_role_names(db, user.id)
        user_resp = UserResponse(
            id=user.id,
            organization_id=user.organization_id,
            email=user.email,
            mobile=user.mobile,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            roles=roles
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=120 * 60,
            user=user_resp
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Return active profile and RBAC roles of authenticated user."""
    roles = await get_user_role_names(db, current_user.id)
    return UserResponse(
        id=current_user.id,
        organization_id=current_user.organization_id,
        email=current_user.email,
        mobile=current_user.mobile,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        roles=roles
    )
