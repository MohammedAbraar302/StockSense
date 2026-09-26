from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import get_password_hash
from app.api.deps import get_current_user, require_roles
from app.models.user import User, Role, UserRole
from app.models.audit import AuditLog, Notification
from app.schemas.audit import AuditLogResponse, NotificationResponse, StaffCreate, StaffResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Audit & Staff"])


@router.get("/logs", response_model=List[AuditLogResponse])
async def list_audit_logs(
    entity: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_roles(["ADMIN", "INVENTORY_MANAGER"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve immutable audit log history tracking who changed what, when, and before/after values.
    """
    query = select(AuditLog).options(selectinload(AuditLog.user))
    if entity:
        query = query.where(AuditLog.entity == entity)
    if action:
        query = query.where(AuditLog.action == action)

    query = query.order_by(AuditLog.created_at.desc()).limit(limit)
    rows = (await db.execute(query)).scalars().all()

    return [
        AuditLogResponse(
            id=log.id,
            user_name=log.user.full_name if log.user else "System",
            action=log.action,
            entity=log.entity,
            entity_id=log.entity_id,
            before_state=log.before_state,
            after_state=log.after_state,
            ip_address=log.ip_address,
            created_at=log.created_at
        )
        for log in rows
    ]


@router.get("/notifications", response_model=List[NotificationResponse])
async def list_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Fetch notifications for the current user."""
    stmt = (
        select(Notification)
        .where(
            (Notification.user_id == current_user.id) | (Notification.user_id == None)
        )
        .order_by(Notification.created_at.desc())
        .limit(30)
    )
    return list((await db.execute(stmt)).scalars().all())


@router.put("/notifications/{notif_id}/read")
async def mark_notification_read(
    notif_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a notification as read."""
    notif = (await db.execute(select(Notification).where(Notification.id == notif_id))).scalars().first()
    if notif:
        notif.is_read = True
        await db.commit()
    return {"success": True}


@router.get("/staff", response_model=List[StaffResponse])
async def list_staff_members(
    current_user: User = Depends(require_roles(["ADMIN", "INVENTORY_MANAGER"])),
    db: AsyncSession = Depends(get_db)
):
    """List staff members and their active roles."""
    stmt = (
        select(User)
        .options(selectinload(User.roles).selectinload(UserRole.role))
        .where(User.organization_id == current_user.organization_id)
        .order_by(User.full_name.asc())
    )
    users = (await db.execute(stmt)).scalars().all()

    results = []
    for u in users:
        role_name = u.roles[0].role.name if u.roles and u.roles[0].role else "WAREHOUSE_STAFF"
        results.append(StaffResponse(
            id=u.id,
            full_name=u.full_name,
            email=u.email,
            mobile=u.mobile,
            role=role_name,
            is_active=u.is_active,
            created_at=u.created_at
        ))
    return results


@router.post("/staff", response_model=StaffResponse)
async def create_staff_member(
    req: StaffCreate,
    current_user: User = Depends(require_roles(["ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """Create a staff user and assign role."""
    clean_email = req.email.lower().strip()
    clean_mobile = "".join(filter(str.isdigit, req.mobile))

    # Check duplicates
    if (await db.execute(select(User).where(User.email == clean_email))).scalars().first():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    hashed_pw = get_password_hash(req.password)
    user = User(
        organization_id=current_user.organization_id,
        email=clean_email,
        mobile=clean_mobile,
        hashed_password=hashed_pw,
        full_name=req.full_name.strip(),
        is_active=True,
        is_verified=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    role_record = (await db.execute(select(Role).where(Role.name == req.role_name))).scalars().first()
    if not role_record:
        role_record = Role(name=req.role_name, description=f"{req.role_name} Role")
        db.add(role_record)
        await db.commit()
        await db.refresh(role_record)

    db.add(UserRole(user_id=user.id, role_id=role_record.id))
    await db.commit()

    await AuditService.log_action(
        db=db,
        action="USER_CREATED",
        entity="USER",
        entity_id=user.id,
        user_id=current_user.id,
        after_state={"email": user.email, "role": req.role_name}
    )

    return StaffResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        mobile=user.mobile,
        role=req.role_name,
        is_active=user.is_active,
        created_at=user.created_at
    )
