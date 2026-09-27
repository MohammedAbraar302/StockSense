from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from app.core.database import Base
from app.models.base import generate_uuid, TimestampMixin


class OTPCode(Base, TimestampMixin):
    __tablename__ = "otp_codes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    target_identifier = Column(String(255), nullable=False, index=True)  # email or phone
    code_hash = Column(String(255), nullable=False)
    purpose = Column(String(50), nullable=False, index=True)  # REGISTRATION, LOGIN, PASSWORD_RESET
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=5, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
