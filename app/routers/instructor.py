from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Course, Enrollment, Order, Review, User
from app.utils.database import get_db
from app.utils.deps import require_role

router = APIRouter(prefix="/api/instructor", tags=["instructor"])


@router.get("/dashboard")
def instructor_dashboard(db: Session = Depends(get_db), user: User = Depends(require_role("instructor", "admin"))):
    """Instructor's own dashboard — courses they teach, enrollment stats, revenue."""
    my_courses = db.query(Course).filter(Course.instructor == user.full_name).all()
    course_ids = [c.id for c in my_courses]

    total_students = (
        db.query(func.count(Enrollment.id))
        .filter(Enrollment.course_id.in_(course_ids))
        .scalar() or 0
    ) if course_ids else 0

    total_revenue = (
        db.query(func.coalesce(func.sum(Order.amount), 0))
        .filter(Order.course_id.in_(course_ids), Order.status == "paid")
        .scalar() or 0
    ) if course_ids else 0

    avg_rating = (
        db.query(func.avg(Course.rating))
        .filter(Course.id.in_(course_ids))
        .scalar() or 0.0
    ) if course_ids else 0.0

    pending_reviews = (
        db.query(func.count(Review.id))
        .filter(Review.course_id.in_(course_ids), Review.status == "pending")
        .scalar() or 0
    ) if course_ids else 0

    courses_out = []
    for c in my_courses:
        enrolled = db.query(func.count(Enrollment.id)).filter(Enrollment.course_id == c.id).scalar() or 0
        revenue = db.query(func.coalesce(func.sum(Order.amount), 0)).filter(
            Order.course_id == c.id, Order.status == "paid"
        ).scalar() or 0
        completed = db.query(func.count(Enrollment.id)).filter(
            Enrollment.course_id == c.id, Enrollment.completed == True
        ).scalar() or 0
        avg_prog = db.query(func.avg(Enrollment.progress_percent)).filter(
            Enrollment.course_id == c.id
        ).scalar() or 0

        courses_out.append({
            "id": c.id,
            "slug": c.slug,
            "title": c.title,
            "thumbnail": c.thumbnail,
            "category": c.category,
            "status": c.status,
            "rating": c.rating,
            "students_enrolled": enrolled,
            "completed_students": completed,
            "avg_progress_percent": round(float(avg_prog), 1),
            "revenue": int(revenue),
        })

    return {
        "stats": {
            "total_courses": len(my_courses),
            "total_students": total_students,
            "total_revenue": int(total_revenue),
            "avg_rating": round(float(avg_rating), 2),
            "pending_reviews": pending_reviews,
        },
        "courses": courses_out,
    }


@router.get("/courses")
def instructor_courses(db: Session = Depends(get_db), user: User = Depends(require_role("instructor", "admin"))):
    """List all courses this instructor teaches."""
    courses = db.query(Course).filter(Course.instructor == user.full_name).all()
    return {
        "items": [
            {
                "id": c.id,
                "slug": c.slug,
                "title": c.title,
                "thumbnail": c.thumbnail,
                "category": c.category,
                "status": c.status,
                "students_count": c.students_count,
                "rating": c.rating,
                "lessons_count": c.lessons_count,
                "price": c.price,
                "discount_price": c.discount_price,
            }
            for c in courses
        ],
        "total": len(courses),
    }


@router.get("/courses/{course_id}/students")
def course_students(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("instructor", "admin")),
):
    """Get enrolled students for one of the instructor's courses."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.instructor != user.full_name and user.role != "admin":
        raise HTTPException(status_code=403, detail="You do not teach this course")

    rows = (
        db.query(Enrollment, User)
        .join(User, User.id == Enrollment.user_id)
        .filter(Enrollment.course_id == course_id)
        .order_by(Enrollment.created_at.desc())
        .all()
    )
    return {
        "course_title": course.title,
        "items": [
            {
                "student_name": u.full_name,
                "email": u.email,
                "progress_percent": e.progress_percent,
                "completed": e.completed,
                "enrolled_at": e.created_at,
            }
            for e, u in rows
        ],
        "total": len(rows),
    }


@router.get("/courses/{course_id}/reviews")
def course_reviews(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("instructor", "admin")),
):
    """Get reviews for one of the instructor's courses."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.instructor != user.full_name and user.role != "admin":
        raise HTTPException(status_code=403, detail="You do not teach this course")

    rows = (
        db.query(Review, User)
        .join(User, User.id == Review.user_id)
        .filter(Review.course_id == course_id, Review.status == "approved")
        .order_by(Review.created_at.desc())
        .all()
    )
    return {
        "items": [
            {
                "student_name": u.full_name,
                "rating": r.rating,
                "comment": r.comment,
                "created_at": r.created_at,
            }
            for r, u in rows
        ],
        "total": len(rows),
    }


@router.get("/analytics")
def instructor_analytics(db: Session = Depends(get_db), user: User = Depends(require_role("instructor", "admin"))):
    """Aggregate analytics for all of instructor's courses."""
    courses = db.query(Course).filter(Course.instructor == user.full_name).all()
    course_ids = [c.id for c in courses]

    if not course_ids:
        return {"enrollment_by_course": [], "revenue_by_course": [], "rating_by_course": []}

    enrollment_by_course = []
    revenue_by_course = []
    rating_by_course = []

    for c in courses:
        enrolled = db.query(func.count(Enrollment.id)).filter(Enrollment.course_id == c.id).scalar() or 0
        revenue = db.query(func.coalesce(func.sum(Order.amount), 0)).filter(
            Order.course_id == c.id, Order.status == "paid"
        ).scalar() or 0

        enrollment_by_course.append({"course": c.title, "enrolled": enrolled})
        revenue_by_course.append({"course": c.title, "revenue": int(revenue)})
        rating_by_course.append({"course": c.title, "rating": c.rating})

    return {
        "enrollment_by_course": enrollment_by_course,
        "revenue_by_course": revenue_by_course,
        "rating_by_course": rating_by_course,
    }
