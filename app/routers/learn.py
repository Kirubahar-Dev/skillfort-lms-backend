import io
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.models.entities import (
    Certificate, CourseLesson, Enrollment, LessonProgress, User, Course
)
from app.utils.database import get_db
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/learn", tags=["learn"])


# ── Mark lesson complete ──────────────────────────────────────────────────────
@router.post("/lessons/{lesson_id}/complete")
def complete_lesson(lesson_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Verify enrolled
    enroll = db.query(Enrollment).filter(
        Enrollment.user_id == user.id,
        Enrollment.course_id == lesson.course_id
    ).first()
    if not enroll:
        raise HTTPException(status_code=403, detail="Not enrolled in this course")

    # Upsert lesson progress
    prog = db.query(LessonProgress).filter(
        LessonProgress.student_id == user.id,
        LessonProgress.lesson_id == lesson_id
    ).first()
    if not prog:
        prog = LessonProgress(
            student_id=user.id,
            lesson_id=lesson_id,
            course_id=lesson.course_id,
            completed=True,
            completed_at=datetime.now(timezone.utc)
        )
        db.add(prog)
    elif not prog.completed:
        prog.completed = True
        prog.completed_at = datetime.now(timezone.utc)

    # Recalculate course progress %
    total = db.query(CourseLesson).filter(CourseLesson.course_id == lesson.course_id).count()
    done = db.query(LessonProgress).filter(
        LessonProgress.student_id == user.id,
        LessonProgress.course_id == lesson.course_id,
        LessonProgress.completed == True
    ).count()
    pct = int((done / max(1, total)) * 100)
    enroll.progress_percent = pct
    db.commit()

    # Auto-issue certificate when 100%
    if pct == 100:
        _ensure_certificate(db, user, lesson.course_id)

    return {"lesson_id": lesson_id, "completed": True, "progress_percent": pct}


# ── Get course progress (lesson list with completion) ─────────────────────────
@router.get("/courses/{course_id}/progress")
def course_progress(course_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    enroll = db.query(Enrollment).filter(
        Enrollment.user_id == user.id,
        Enrollment.course_id == course_id
    ).first()
    if not enroll:
        raise HTTPException(status_code=403, detail="Not enrolled")

    lessons = db.query(CourseLesson).filter(
        CourseLesson.course_id == course_id
    ).order_by(CourseLesson.order_index).all()

    completed_ids = {
        p.lesson_id for p in db.query(LessonProgress).filter(
            LessonProgress.student_id == user.id,
            LessonProgress.course_id == course_id,
            LessonProgress.completed == True
        ).all()
    }

    result = []
    for i, l in enumerate(lessons):
        is_done = l.id in completed_ids
        # First lesson always unlocked; others unlock only if previous done
        is_unlocked = (i == 0) or (lessons[i - 1].id in completed_ids)
        result.append({
            "id": l.id,
            "section_title": l.section_title,
            "lesson_title": l.lesson_title,
            "duration_minutes": l.duration_minutes,
            "video_url": l.video_url,
            "order_index": l.order_index,
            "is_preview": l.is_preview,
            "completed": is_done,
            "unlocked": is_unlocked,
        })

    return {
        "course_id": course_id,
        "progress_percent": enroll.progress_percent,
        "lessons": result,
        "total": len(lessons),
        "completed_count": len(completed_ids),
    }


# ── Admin: update lesson video URL ────────────────────────────────────────────
@router.patch("/admin/lessons/{lesson_id}/video")
def update_lesson_video(lesson_id: int, video_url: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in ("admin", "instructor"):
        raise HTTPException(status_code=403, detail="Forbidden")
    lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    lesson.video_url = video_url
    db.commit()
    return {"lesson_id": lesson_id, "video_url": video_url}


# ── Admin: upload video file for a lesson ────────────────────────────────────
@router.post("/admin/lessons/{lesson_id}/upload-video")
async def upload_lesson_video(
    lesson_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if user.role not in ("admin", "instructor"):
        raise HTTPException(status_code=403, detail="Forbidden")
    lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Validate file type
    allowed = {"video/mp4", "video/webm", "video/ogg", "video/quicktime", "video/x-msvideo"}
    content_type = file.content_type or "video/mp4"
    if content_type not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported video type: {content_type}. Use mp4, webm, ogg, mov, or avi.")

    # 500MB limit
    MAX_SIZE = 500 * 1024 * 1024
    file_bytes = await file.read()
    if len(file_bytes) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 500MB.")

    try:
        from app.services.storage_service import upload_video
        url = upload_video(file_bytes, file.filename or "video.mp4", content_type)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    lesson.video_url = url
    db.commit()
    return {"lesson_id": lesson_id, "video_url": url, "filename": file.filename}


# ── Admin: get all students progress for a course ─────────────────────────────
@router.get("/admin/courses/{course_id}/student-progress")
def admin_course_progress(course_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in ("admin", "instructor"):
        raise HTTPException(status_code=403, detail="Forbidden")

    enrollments = db.query(Enrollment).filter(Enrollment.course_id == course_id).all()
    lessons = db.query(CourseLesson).filter(CourseLesson.course_id == course_id).order_by(CourseLesson.order_index).all()
    total_lessons = len(lessons)

    result = []
    for enroll in enrollments:
        student = db.query(User).filter(User.id == enroll.user_id).first()
        completed = db.query(LessonProgress).filter(
            LessonProgress.student_id == enroll.user_id,
            LessonProgress.course_id == course_id,
            LessonProgress.completed == True
        ).count()
        result.append({
            "student_id": enroll.user_id,
            "student_name": student.full_name if student else "Unknown",
            "student_email": student.email if student else "",
            "progress_percent": enroll.progress_percent,
            "lessons_completed": completed,
            "total_lessons": total_lessons,
            "enrolled_at": enroll.created_at.isoformat() if enroll.created_at else None,
        })

    return {"course_id": course_id, "students": result}


# ── Certificate: generate PDF ─────────────────────────────────────────────────
@router.get("/certificate/{course_id}")
def get_certificate(course_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    enroll = db.query(Enrollment).filter(
        Enrollment.user_id == user.id,
        Enrollment.course_id == course_id
    ).first()
    if not enroll or enroll.progress_percent < 100:
        raise HTTPException(status_code=403, detail="Complete all lessons to get certificate")

    cert = _ensure_certificate(db, user, course_id)
    course = db.query(Course).filter(Course.id == course_id).first()

    pdf_bytes = _build_certificate_pdf(
        student_name=user.full_name,
        course_title=course.title if course else "Course",
        certificate_no=cert.certificate_no,
        issued_date=cert.created_at,
    )
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="certificate_{cert.certificate_no}.pdf"'}
    )


# ── Certificate JSON (for frontend rendering) ─────────────────────────────────
@router.get("/certificate/{course_id}/info")
def get_certificate_info(course_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    enroll = db.query(Enrollment).filter(
        Enrollment.user_id == user.id,
        Enrollment.course_id == course_id
    ).first()
    if not enroll:
        raise HTTPException(status_code=404, detail="Not enrolled")

    course = db.query(Course).filter(Course.id == course_id).first()
    eligible = enroll.progress_percent >= 100
    cert = None
    if eligible:
        cert = _ensure_certificate(db, user, course_id)

    return {
        "eligible": eligible,
        "progress_percent": enroll.progress_percent,
        "course_title": course.title if course else "",
        "course_category": course.category if course else "",
        "student_name": user.full_name,
        "certificate_no": cert.certificate_no if cert else None,
        "issued_date": cert.created_at.isoformat() if cert and cert.created_at else None,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────
def _ensure_certificate(db: Session, user: User, course_id: int) -> Certificate:
    cert = db.query(Certificate).filter(
        Certificate.user_id == user.id,
        Certificate.course_id == course_id
    ).first()
    if not cert:
        cert_no = f"SF-{course_id:03d}-{user.id:05d}-{uuid.uuid4().hex[:6].upper()}"
        cert = Certificate(
            user_id=user.id,
            course_id=course_id,
            certificate_no=cert_no,
            file_path=f"/certificates/{cert_no}.pdf"
        )
        db.add(cert)
        db.commit()
        db.refresh(cert)
    return cert


def _build_certificate_pdf(student_name: str, course_title: str, certificate_no: str, issued_date) -> bytes:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph
    from reportlab.lib.enums import TA_CENTER

    width, height = landscape(A4)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(A4))

    # Background
    c.setFillColor(colors.HexColor("#0f172a"))
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # Gold border
    c.setStrokeColor(colors.HexColor("#f59e0b"))
    c.setLineWidth(4)
    c.rect(15*mm, 15*mm, width - 30*mm, height - 30*mm, fill=0, stroke=1)
    c.setLineWidth(1.5)
    c.rect(18*mm, 18*mm, width - 36*mm, height - 36*mm, fill=0, stroke=1)

    # Logo text / brand
    c.setFont("Helvetica-Bold", 28)
    c.setFillColor(colors.HexColor("#f59e0b"))
    c.drawCentredString(width / 2, height - 50*mm, "SKILLFORT INSTITUTE")

    c.setFont("Helvetica", 12)
    c.setFillColor(colors.HexColor("#94a3b8"))
    c.drawCentredString(width / 2, height - 60*mm, "Professional Development & Placement Training")

    # Divider
    c.setStrokeColor(colors.HexColor("#f59e0b"))
    c.setLineWidth(1)
    c.line(60*mm, height - 65*mm, width - 60*mm, height - 65*mm)

    # Certificate of Completion
    c.setFont("Helvetica", 14)
    c.setFillColor(colors.HexColor("#cbd5e1"))
    c.drawCentredString(width / 2, height - 80*mm, "CERTIFICATE OF COMPLETION")

    # Student name
    c.setFont("Helvetica-Bold", 36)
    c.setFillColor(colors.white)
    c.drawCentredString(width / 2, height - 105*mm, student_name)

    c.setFont("Helvetica", 13)
    c.setFillColor(colors.HexColor("#94a3b8"))
    c.drawCentredString(width / 2, height - 118*mm, "has successfully completed the course")

    # Course title
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(colors.HexColor("#f59e0b"))
    c.drawCentredString(width / 2, height - 138*mm, course_title)

    # Bottom details
    date_str = issued_date.strftime("%d %B %Y") if issued_date else datetime.now().strftime("%d %B %Y")

    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#94a3b8"))
    c.drawString(30*mm, 35*mm, f"Certificate No: {certificate_no}")
    c.drawString(30*mm, 28*mm, f"Issue Date: {date_str}")

    # Signature line
    c.setStrokeColor(colors.HexColor("#f59e0b"))
    c.line(width - 90*mm, 38*mm, width - 30*mm, 38*mm)
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor("#94a3b8"))
    c.drawCentredString(width - 60*mm, 32*mm, "Authorized Signatory")
    c.drawCentredString(width - 60*mm, 26*mm, "Skillfort Institute")

    c.save()
    return buf.getvalue()
