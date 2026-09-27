from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token, decode_token
from app.models.user import User, Organization, Role, UserRole, RefreshToken
from app.services.otp_service import OTPService
from app.services.audit_service import AuditService


class AuthService:
    @staticmethod
    async def get_or_create_default_org(db: AsyncSession) -> Organization:
        """Fetch default organization or create if it doesn't exist."""
        stmt = select(Organization).where(Organization.slug == "default")
        result = await db.execute(stmt)
        org = result.scalars().first()
        if not org:
            org = Organization(
                name="StockSense Enterprises",
                slug="default",
                is_active=True
            )
            db.add(org)
            await db.commit()
            await db.refresh(org)
        return org

    @staticmethod
    async def register_user(
        db: AsyncSession,
        full_name: str,
        email: str,
        mobile: str,
        password: str
    ) -> Tuple[User, str]:
        """Validate uniqueness, hash password, create unverified user, and send OTP."""
        email_clean = email.lower().strip()
        mobile_clean = "".join(filter(str.isdigit, mobile))

        # Check duplicate email
        stmt = select(User).where(User.email == email_clean)
        existing_email = (await db.execute(stmt)).scalars().first()
        if existing_email:
            raise ValueError("An account with this email address already exists")

        # Check duplicate mobile
        stmt = select(User).where(User.mobile == mobile_clean)
        existing_mobile = (await db.execute(stmt)).scalars().first()
        if existing_mobile:
            raise ValueError("An account with this mobile number already exists")

        org = await AuthService.get_or_create_default_org(db)
        hashed_pw = get_password_hash(password)

        user = User(
            organization_id=org.id,
            email=email_clean,
            mobile=mobile_clean,
            hashed_password=hashed_pw,
            full_name=full_name.strip(),
            is_active=True,
            is_verified=False
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Dispatch OTP to email
        otp = await OTPService.create_and_send_otp(db, email_clean, purpose="REGISTRATION")
        return user, otp

    @staticmethod
    async def verify_registration(
        db: AsyncSession,
        target_identifier: str,
        otp_code: str
    ) -> User:
        """Verify registration OTP and activate user account."""
        target_clean = target_identifier.lower().strip()
        is_valid = await OTPService.verify_otp(db, target_clean, otp_code, purpose="REGISTRATION")
        if not is_valid:
            raise ValueError("Invalid or expired OTP code")

        stmt = select(User).where(or_(User.email == target_clean, User.mobile == target_clean))
        user = (await db.execute(stmt)).scalars().first()
        if not user:
            raise ValueError("User not found")

        user.is_verified = True

        # Assign role: if first user make ADMIN, else INVENTORY_MANAGER
        count_stmt = select(User).where(User.is_verified == True)
        verified_count = len((await db.execute(count_stmt)).scalars().all())

        role_name = "ADMIN" if verified_count <= 1 else "INVENTORY_MANAGER"
        role_stmt = select(Role).where(Role.name == role_name)
        role = (await db.execute(role_stmt)).scalars().first()
        if not role:
            role = Role(name=role_name, description=f"Default {role_name} Role")
            db.add(role)
            await db.commit()
            await db.refresh(role)

        # Check if user already has role
        ur_stmt = select(UserRole).where(and_(UserRole.user_id == user.id, UserRole.role_id == role.id))
        existing_ur = (await db.execute(ur_stmt)).scalars().first()
        if not existing_ur:
            db.add(UserRole(user_id=user.id, role_id=role.id))

        await db.commit()
        await db.refresh(user)

        await AuditService.log_action(
            db=db,
            action="USER_VERIFIED",
            entity="USER",
            entity_id=user.id,
            user_id=user.id,
            after_state={"email": user.email, "role": role_name}
        )

        return user

    @staticmethod
    async def authenticate_and_send_login_otp(
        db: AsyncSession,
        username: str,
        password: str
    ) -> Tuple[User, str]:
        """Validate credentials and dispatch 2FA Login OTP."""
        clean_user = username.lower().strip()
        stmt = select(User).where(or_(User.email == clean_user, User.mobile == clean_user))
        user = (await db.execute(stmt)).scalars().first()

        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid email/mobile or password")

        if not user.is_active:
            raise ValueError("Account is deactivated. Please contact support.")

        if not user.is_verified:
            # Re-send verification OTP
            await OTPService.create_and_send_otp(db, user.email, purpose="REGISTRATION")
            raise ValueError("Account is not yet verified. A new verification OTP has been sent.")

        # Dispatch Login 2FA OTP
        otp = await OTPService.create_and_send_otp(db, user.email, purpose="LOGIN")
        return user, otp

    @staticmethod
    async def complete_login_with_otp(
        db: AsyncSession,
        username: str,
        otp_code: str
    ) -> Tuple[User, str, str]:
        """Verify login OTP and generate JWT access + refresh tokens."""
        clean_user = username.lower().strip()
        stmt = select(User).where(or_(User.email == clean_user, User.mobile == clean_user))
        user = (await db.execute(stmt)).scalars().first()

        if not user:
            raise ValueError("User not found")

        is_valid = await OTPService.verify_otp(db, user.email, otp_code, purpose="LOGIN")
        if not is_valid:
            raise ValueError("Invalid or expired login OTP")

        # Get user roles
        ur_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
        roles = (await db.execute(ur_stmt)).scalars().all()

        token_payload = {
            "sub": user.id,
            "email": user.email,
            "org_id": user.organization_id,
            "roles": list(roles)
        }

        access_token = create_access_token(token_payload)
        refresh_token = create_refresh_token({"sub": user.id})

        # Save refresh token in DB
        db.add(RefreshToken(user_id=user.id, token=refresh_token))
        await db.commit()

        return user, access_token, refresh_token

    @staticmethod
    async def rotate_refresh_token(
        db: AsyncSession,
        raw_refresh_token: str
    ) -> Tuple[str, str, User]:
        """Rotate refresh token and issue new token pair."""
        payload = decode_token(raw_refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise ValueError("Invalid refresh token")

        user_id = payload.get("sub")
        stmt = select(RefreshToken).where(
            and_(
                RefreshToken.token == raw_refresh_token,
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False
            )
        )
        token_record = (await db.execute(stmt)).scalars().first()
        if not token_record:
            raise ValueError("Refresh token is revoked or invalid")

        # Revoke old token
        token_record.revoked = True

        # Fetch user & roles
        user = (await db.execute(select(User).where(User.id == user_id))).scalars().first()
        if not user or not user.is_active:
            raise ValueError("User inactive or not found")

        ur_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
        roles = (await db.execute(ur_stmt)).scalars().all()

        new_access = create_access_token({
            "sub": user.id,
            "email": user.email,
            "org_id": user.organization_id,
            "roles": list(roles)
        })
        new_refresh = create_refresh_token({"sub": user.id})

        db.add(RefreshToken(user_id=user.id, token=new_refresh))
        await db.commit()

        return new_access, new_refresh, user
