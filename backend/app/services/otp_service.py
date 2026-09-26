import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from app.core.config import settings
from app.core.security import generate_otp, hash_otp, verify_otp_hash
from app.models.otp import OTPCode
from app.core.providers.otp_providers import ConsoleOTPProvider, SendGridOTPProvider, TwilioOTPProvider, OTPProvider

logger = logging.getLogger("stocksense.otp")

def get_otp_provider() -> OTPProvider:
    """
    Factory to return the appropriate OTP provider based on environment settings.
    """
    if settings.DEV_MODE:
        return ConsoleOTPProvider()

    # Production Logic: You would add actual keys from settings.env here
    # return SendGridOTPProvider(api_key=settings.SENDGRID_API_KEY)
    # return TwilioOTPProvider(account_sid=settings.TWILIO_SID, auth_token=settings.TWILIO_TOKEN)
    return ConsoleOTPProvider() # Fallback

class OTPService:
    @staticmethod
    async def create_and_send_otp(
        db: AsyncSession,
        target_identifier: str,
        purpose: str = "REGISTRATION"
    ) -> str:
        """
        Generate cryptographically secure 6-digit OTP, store hashed in database,
        and dispatch via the configured OTP provider.
        """
        now = datetime.now(timezone.utc)

        # Invalidate any active prior OTPs for this target and purpose
        await db.execute(
            update(OTPCode)
            .where(
                and_(
                    OTPCode.target_identifier == target_identifier,
                    OTPCode.purpose == purpose,
                    OTPCode.is_used == False
                )
            )
            .values(is_used=True)
        )

        raw_otp = generate_otp(6)
        hashed_code = hash_otp(raw_otp)
        expires_at = now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

        otp_record = OTPCode(
            target_identifier=target_identifier,
            code_hash=hashed_code,
            purpose=purpose,
            attempts=0,
            max_attempts=settings.OTP_MAX_ATTEMPTS,
            expires_at=expires_at,
            is_used=False
        )
        db.add(otp_record)
        await db.commit()

        # Dispatch using the provider pattern
        provider = get_otp_provider()
        channel = 'email' if '@' in target_identifier else 'sms'

        success = await provider.send_otp(target_identifier, raw_otp, channel)

        if not success:
            logger.error(f"Failed to dispatch OTP to {target_identifier} via {channel}")

        logger.info(f"Generated OTP for {target_identifier} ({purpose})")

        return raw_otp

    @staticmethod
    async def verify_otp(
        db: AsyncSession,
        target_identifier: str,
        otp_code: str,
        purpose: str
    ) -> bool:
        """
        Verify candidate OTP against stored hash, enforcing expiration and attempt limits.
        """
        stmt = select(OTPCode).where(
            and_(
                OTPCode.target_identifier == target_identifier,
                OTPCode.purpose == purpose,
                OTPCode.is_used == False
            )
        ).order_by(OTPCode.created_at.desc())

        result = await db.execute(stmt)
        otp_record = result.scalars().first()

        if not otp_record:
            return False

        expires_at = otp_record.expires_at
        if expires_at.tzinfo is not None:
            now = datetime.now(timezone.utc)
        else:
            now = datetime.utcnow()

        # Check expiration
        if expires_at < now:
            otp_record.is_used = True
            await db.commit()
            return False

        # Check attempt count
        if otp_record.attempts >= otp_record.max_attempts:
            otp_record.is_used = True
            await db.commit()
            return False

        otp_record.attempts += 1

        if verify_otp_hash(otp_code, otp_record.code_hash):
            otp_record.is_used = True
            await db.commit()
            return True

        await db.commit()
        return False
