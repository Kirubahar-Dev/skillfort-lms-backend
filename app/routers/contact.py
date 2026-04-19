from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models import ContactMessage
from app.schemas.interview import ContactRequest
from app.utils.database import get_db

router = APIRouter(tags=["contact"])


@router.post("/api/contact")
def submit_contact(payload: ContactRequest, db: Session = Depends(get_db)):
    msg = ContactMessage(**payload.model_dump())
    db.add(msg)
    db.commit()
    return {"message": "Contact request received", "email": payload.email}
