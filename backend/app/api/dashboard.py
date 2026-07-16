from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.dashboard_service import get_dashboard_data

router = APIRouter()


@router.get("/")
def dashboard(days: int = Query(14, ge=1, le=365), months: int = Query(6, ge=1, le=36), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_dashboard_data(db, current_user, days, months)
