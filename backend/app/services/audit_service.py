import json
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog, Notification


class AuditService:
    @staticmethod
    async def log_action(
        db: AsyncSession,
        action: str,
        entity: str,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        before_state: Optional[Any] = None,
        after_state: Optional[Any] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Record an immutable audit log entry."""
        before_json = json.dumps(before_state, default=str) if before_state is not None else None
        after_json = json.dumps(after_state, default=str) if after_state is not None else None

        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            before_state=before_json,
            after_state=after_json,
            ip_address=ip_address
        )
        db.add(log_entry)
        await db.commit()
        return log_entry

    @staticmethod
    async def notify(
        db: AsyncSession,
        notification_type: str,
        title: str,
        message: str,
        user_id: Optional[str] = None,
        link: Optional[str] = None
    ) -> Notification:
        """Create a persistent system notification."""
        notif = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
            is_read=False
        )
        db.add(notif)
        await db.commit()
        return notif
