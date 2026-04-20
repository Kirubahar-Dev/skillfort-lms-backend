import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models import Certificate, Course, EmailLog, Enrollment, Order
from app.schemas.commerce import ConfirmOrderRequest, CreateOrderRequest, SendMailRequest
from app.services.certificate_service import CertificateService
from app.services.mail_service import MailService
from app.services.payment_service import RazorpayService
from app.utils.config import get_settings
from app.utils.database import get_db
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/orders", tags=["commerce"])
settings = get_settings()


@router.post("/create")
def create_order(payload: CreateOrderRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    course = db.query(Course).filter(Course.id == payload.course_id, Course.status == "published").first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    order_no = f"SF-{uuid.uuid4().hex[:10].upper()}"
    rp = RazorpayService()
    gateway_order = rp.create_order(amount=payload.amount, receipt=order_no)

    order = Order(
        order_id=order_no,
        razorpay_order_id=gateway_order.get("id"),
        user_id=user.id,
        course_id=payload.course_id,
        amount=payload.amount,
        status="created",
    )
    db.add(order)
    db.commit()

    return {
        "order_id": order_no,
        "razorpay_order_id": gateway_order.get("id"),
        "amount": payload.amount,
        "key_id": settings.razorpay_key_id,
        "currency": "INR",
    }


@router.post("/confirm")
async def confirm_order(payload: ConfirmOrderRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    order = db.query(Order).filter(Order.order_id == payload.order_id, Order.user_id == user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    rp = RazorpayService()
    rp.verify_signature(order.razorpay_order_id or "", payload.razorpay_payment_id, payload.razorpay_signature)

    order.razorpay_payment_id = payload.razorpay_payment_id
    order.status = "paid"

    course = db.query(Course).filter(Course.id == order.course_id).first()
    enrollment = db.query(Enrollment).filter(Enrollment.user_id == user.id, Enrollment.course_id == order.course_id).first()
    if not enrollment:
        db.add(
            Enrollment(
                user_id=user.id,
                course_id=order.course_id,
                progress_percent=0,
                completed=False,
                last_lesson="Lesson 1",
            )
        )

    cert_no = f"CERT-{uuid.uuid4().hex[:8].upper()}"
    cert_path = CertificateService(settings.file_storage_dir).generate(
        certificate_no=cert_no,
        student_name=user.full_name,
        course_name=course.title if course else "Skillfort Course",
    )

    cert = Certificate(user_id=user.id, course_id=order.course_id, certificate_no=cert_no, file_path=cert_path)
    db.add(cert)

    mailer = MailService()
    subject = f"Enrolled: {course.title if course else 'Course'} ✅"
    mail_result = await mailer.send_enrollment_confirmation(
        user.email, user.full_name,
        course.title if course else "Skillfort Course",
        order.order_id
    )
    db.add(EmailLog(recipient=user.email, subject=subject, status=mail_result.get("status", "unknown"), error=mail_result.get("reason")))

    db.commit()

    return {
        "message": "Order confirmed",
        "order_id": order.order_id,
        "status": order.status,
        "certificate": cert.file_path,
        "mail": mail_result,
    }


@router.get("/my")
def my_orders(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(Order).filter(Order.user_id == user.id).order_by(Order.created_at.desc()).all()
    return {
        "items": [
            {
                "order_id": r.order_id,
                "course_id": r.course_id,
                "amount": r.amount,
                "status": r.status,
                "created_at": r.created_at,
            }
            for r in rows
        ]
    }


@router.get("/certificates/my")
def my_certificates(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(Certificate).filter(Certificate.user_id == user.id).order_by(Certificate.created_at.desc()).all()
    return {"items": [{"certificate_no": r.certificate_no, "course_id": r.course_id, "file_path": r.file_path} for r in rows]}


@router.get("/certificates/{certificate_no}")
def certificate_file(certificate_no: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    cert = db.query(Certificate).filter(Certificate.certificate_no == certificate_no, Certificate.user_id == user.id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    path = Path(cert.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Certificate file missing")
    return {"file_path": str(path)}


@router.post("/mail/test")
async def send_test_mail(payload: SendMailRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    mailer = MailService()
    result = await mailer.send(payload.recipient, payload.subject, payload.body)
    db.add(EmailLog(recipient=payload.recipient, subject=payload.subject, status=result.get("status", "unknown"), error=result.get("reason")))
    db.commit()
    return result
