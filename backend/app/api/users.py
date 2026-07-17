from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.document import Document
from app.models.report import ParsedReport
from app.models.user import Role, User
from app.schemas.user import UserAdminUpdate, UserListResponse, UserResponse
from app.utils.audit import log_action

router = APIRouter()


@router.get("", response_model=UserListResponse)
@router.get("/", response_model=UserListResponse, include_in_schema=False)
def list_users(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100), current_user: User = Depends(require_role([Role.Admin])), db: Session = Depends(get_db)):
    query = db.query(User)
    return {"total": query.count(), "page": page, "page_size": page_size, "items": query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()}


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, current_user: User = Depends(require_role([Role.Admin])), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_in: UserAdminUpdate, current_user: User = Depends(require_role([Role.Admin])), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    actions = []
    if user_in.role is not None and user_in.role != user.role:
        actions.append(("User Role Changed", f"User {user.id}: role changed from {user.role.value} to {user_in.role.value}"))
        user.role = user_in.role
    if user_in.is_active is not None and user_in.is_active != user.is_active:
        actions.append(("User Reactivated" if user_in.is_active else "User Deactivated", f"User {user.id} ({user.email})"))
        user.is_active = user_in.is_active
    db.commit()
    db.refresh(user)
    for action, remarks in actions:
        log_action(db, None, action, "Success", f"{remarks} by Admin {current_user.email}")
    return user


@router.delete("/{user_id}")
def delete_user(user_id: int, current_user: User = Depends(require_role([Role.Admin])), db: Session = Depends(get_db)):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Administrators cannot delete their own account")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    email = user.email
    db.query(Document).filter(Document.uploaded_by == user_id).update({Document.uploaded_by: None}, synchronize_session=False)
    db.query(ParsedReport).filter(ParsedReport.reviewed_by == user_id).update({ParsedReport.reviewed_by: None}, synchronize_session=False)
    db.delete(user)
    db.commit()
    log_action(db, None, "User Deleted", "Success", f"Deleted user {user_id} ({email}) by Admin {current_user.email}")
    return {"message": "User deleted successfully"}
