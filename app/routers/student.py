import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    Certificate,
    Course,
    CourseNote,
    Enrollment,
    Notification,
    Order,
    QuizAttempt,
    Review,
    StudentProfile,
    User,
)
from app.utils.config import get_settings
from app.utils.database import get_db
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/student", tags=["student"])
settings = get_settings()


def enrolled_courses_query(db: Session, user_id: int):
    return (
        db.query(Enrollment, Course)
        .join(Course, Course.id == Enrollment.course_id)
        .filter(Enrollment.user_id == user_id)
        .order_by(Enrollment.created_at.desc())
    )


@router.get("/dashboard")
def student_dashboard(db: Session = Depends(get_db), user=Depends(get_current_user)):
    enrollments = db.query(Enrollment).filter(Enrollment.user_id == user.id).all()
    total = len(enrollments)
    completed = len([x for x in enrollments if x.completed or x.progress_percent >= 100])
    in_progress = total - completed
    certs = db.query(Certificate).filter(Certificate.user_id == user.id).count()
    bookmarks = 0

    latest_activity = [
        {
            "course_id": e.course_id,
            "last_lesson": e.last_lesson,
            "progress_percent": e.progress_percent,
        }
        for e in enrollments[:5]
    ]

    return {
        "stats": {
            "total_enrolled_courses": total,
            "completed_courses": completed,
            "in_progress_courses": in_progress,
            "certificates_earned": certs,
        },
        "recent_activity": latest_activity,
        "interview_prep_progress": {
            "bookmarked_questions": bookmarks,
            "mock_scores": [8, 7, 9],
            "planner_completion_percent": 42,
        },
    }


@router.get("/my-courses")
def my_courses(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = enrolled_courses_query(db, user.id).all()
    return {
        "items": [
            {
                "course_id": c.id,
                "slug": c.slug,
                "title": c.title,
                "thumbnail": c.thumbnail,
                "progress_percent": e.progress_percent,
                "completed": e.completed,
                "last_lesson": e.last_lesson,
            }
            for e, c in rows
        ]
    }


@router.get("/learn/{course_slug}")
def learn_course(course_slug: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    course = db.query(Course).filter(Course.slug == course_slug).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    enrollment = db.query(Enrollment).filter(Enrollment.user_id == user.id, Enrollment.course_id == course.id).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="Not enrolled")

    lessons = [
        {
            "id": i + 1,
            "title": f"Lesson {i + 1}",
            "duration_minutes": 20,
            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "completed": i + 1 <= max(1, enrollment.progress_percent // max(1, 100 // max(1, course.lessons_count))),
        }
        for i in range(min(15, max(1, course.lessons_count)))
    ]

    notes = db.query(CourseNote).filter(CourseNote.user_id == user.id, CourseNote.course_id == course.id).order_by(CourseNote.created_at.desc()).all()

    return {
        "course": {
            "id": course.id,
            "slug": course.slug,
            "title": course.title,
            "progress_percent": enrollment.progress_percent,
            "last_lesson": enrollment.last_lesson,
        },
        "lessons": lessons,
        "notes": [{"id": n.id, "lesson_title": n.lesson_title, "note_text": n.note_text, "created_at": n.created_at} for n in notes],
        "quiz": {
            "title": "Quick Check",
            "questions": [
                {"id": 1, "question": "What is REST?", "options": ["Protocol", "Architecture style", "Database", "Language"], "answer": 1},
                {"id": 2, "question": "HTTP status for success?", "options": ["404", "500", "200", "301"], "answer": 2},
            ],
        },
    }


@router.post("/learn/{course_slug}/progress")
def update_progress(course_slug: str, lesson_title: str, progress_percent: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    course = db.query(Course).filter(Course.slug == course_slug).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    enrollment = db.query(Enrollment).filter(Enrollment.user_id == user.id, Enrollment.course_id == course.id).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="Not enrolled")

    enrollment.progress_percent = max(0, min(100, progress_percent))
    enrollment.last_lesson = lesson_title
    enrollment.completed = enrollment.progress_percent >= 100
    db.commit()
    return {"message": "Progress updated", "progress_percent": enrollment.progress_percent}


@router.post("/learn/{course_slug}/notes")
def add_note(course_slug: str, lesson_title: str, note_text: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    course = db.query(Course).filter(Course.slug == course_slug).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    note = CourseNote(user_id=user.id, course_id=course.id, lesson_title=lesson_title, note_text=note_text)
    db.add(note)
    db.commit()
    return {"message": "Saved"}


@router.post("/learn/{course_slug}/quiz-submit")
def submit_quiz(course_slug: str, score: int, total: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    course = db.query(Course).filter(Course.slug == course_slug).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    db.add(QuizAttempt(user_id=user.id, course_id=course.id, score=score, total=total))
    db.commit()
    return {"message": "Quiz submitted"}


@router.get("/orders")
def student_orders(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(Order).filter(Order.user_id == user.id).order_by(Order.created_at.desc()).all()
    return {"items": [{"order_id": r.order_id, "course_id": r.course_id, "amount": r.amount, "status": r.status, "created_at": r.created_at} for r in rows]}


@router.get("/certificates")
def student_certificates(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(Certificate).filter(Certificate.user_id == user.id).order_by(Certificate.created_at.desc()).all()
    return {"items": [{"certificate_no": r.certificate_no, "course_id": r.course_id, "file_path": r.file_path} for r in rows]}


@router.get("/reviews")
def student_reviews(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(Review, Course).join(Course, Course.id == Review.course_id).filter(Review.user_id == user.id).all()
    return {"items": [{"id": r.id, "course": c.title, "rating": r.rating, "comment": r.comment, "status": r.status} for r, c in rows]}


@router.post("/reviews")
def add_review(course_id: int, rating: int, comment: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    rv = Review(user_id=user.id, course_id=course_id, rating=max(1, min(5, rating)), comment=comment, status="pending")
    db.add(rv)
    db.commit()
    return {"message": "Review submitted"}


@router.put("/reviews/{review_id}")
def update_review(review_id: int, rating: int, comment: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    rv = db.query(Review).filter(Review.id == review_id, Review.user_id == user.id).first()
    if not rv:
        raise HTTPException(status_code=404, detail="Review not found")
    rv.rating = max(1, min(5, rating))
    rv.comment = comment
    rv.status = "pending"
    db.commit()
    return {"message": "Review updated"}


@router.delete("/reviews/{review_id}")
def delete_review(review_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    rv = db.query(Review).filter(Review.id == review_id, Review.user_id == user.id).first()
    if not rv:
        raise HTTPException(status_code=404, detail="Review not found")
    db.delete(rv)
    db.commit()
    return {"message": "Review deleted"}


@router.get("/profile")
def get_profile(db: Session = Depends(get_db), user=Depends(get_current_user)):
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
    if not profile:
        profile = StudentProfile(user_id=user.id, phone="", city="", bio="", photo_url="")
        db.add(profile)
        db.commit()
    return {
        "full_name": user.full_name,
        "email": user.email,
        "phone": profile.phone or "",
        "city": profile.city or "",
        "bio": profile.bio or "",
        "photo_url": profile.photo_url or "",
    }


@router.put("/profile")
def update_profile(full_name: str, phone: str = "", city: str = "", bio: str = "", db: Session = Depends(get_db), user=Depends(get_current_user)):
    user.full_name = full_name
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
    if not profile:
        profile = StudentProfile(user_id=user.id)
        db.add(profile)
    profile.phone = phone
    profile.city = city
    profile.bio = bio
    db.commit()
    return {"message": "Profile updated"}


@router.post("/profile/photo")
def upload_photo(file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    ext = Path(file.filename).suffix.lower() or ".jpg"
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Unsupported format")

    target_dir = Path(settings.file_storage_dir) / "profile_photos"
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"user_{user.id}_{secrets.token_hex(6)}{ext}"
    content = file.file.read()
    path.write_bytes(content)

    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
    if not profile:
        profile = StudentProfile(user_id=user.id)
        db.add(profile)
    profile.photo_url = str(path)
    db.commit()

    return {"file_path": str(path)}


@router.get("/notifications")
def notifications(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).all()
    unread = len([x for x in rows if not x.is_read])
    return {"unread": unread, "items": [{"id": r.id, "title": r.title, "message": r.message, "is_read": r.is_read, "created_at": r.created_at} for r in rows]}


@router.post("/notifications/mark-all-read")
def mark_all_read(db: Session = Depends(get_db), user=Depends(get_current_user)):
    db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).update({"is_read": True})
    db.commit()
    return {"message": "Updated"}
