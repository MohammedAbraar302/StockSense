from abc import ABC, abstractmethod
import logging

logger = logging.getLogger("stocksense")

class OTPProvider(ABC):
    """Abstract base class for OTP delivery providers."""

    @abstractmethod
    async def send_otp(self, destination: str, otp: str, channel: str) -> bool:
        """
        Send OTP to a destination.
        :param destination: Email or Phone number
        :param otp: The generated OTP code
        :param channel: 'email' or 'sms'
        """
        pass

class ConsoleOTPProvider(OTPProvider):
    """Development provider that prints OTP to the server console."""

    async def send_otp(self, destination: str, otp: str, channel: str) -> bool:
        logger.info(f" [OTP-DEV] Sending {channel.upper()} to {destination}: {otp}")
        return True

class SendGridOTPProvider(OTPProvider):
    """Production provider using SendGrid for email."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def send_otp(self, destination: str, otp: str, channel: str) -> bool:
        if channel != 'email':
            logger.error("SendGrid only supports email channel")
            return False

        try:
            # In a real production environment, we'd use the sendgrid library:
            # from sendgrid import SendGridAPIClient
            # from sendgrid.helpers.mail import Mail
            # ... implement sending logic ...
            logger.info(f" [OTP-PROD] SendGrid would send OTP {otp} to {destination}")
            return True
        except Exception as e:
            logger.error(f"SendGrid failure: {e}")
            return False

class TwilioOTPProvider(OTPProvider):
    """Production provider using Twilio for SMS."""

    def __init__(self, account_sid: str, auth_token: str):
        self.account_sid = account_sid
        self.auth_token = auth_token

    async def send_otp(self, destination: str, otp: str, channel: str) -> bool:
        if channel != 'sms':
            logger.error("Twilio only supports sms channel")
            return False

        try:
            # Real implementation would use twilio-python library
            logger.info(f" [OTP-PROD] Twilio would send SMS OTP {otp} to {destination}")
            return True
        except Exception as e:
            logger.error(f"Twilio failure: {e}")
            return False
