from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from urllib.parse import urlparse

from app.models import Category, Certificate, Coupon, Course, Enrollment, Order, Review, SiteSetting, User
from app.utils.database import get_db
from app.utils.deps import require_role
from app.utils.text import slugify

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    total_students = db.query(User).filter(User.role == "student").count()
    total_courses = db.query(Course).count()
    total_revenue = db.query(func.coalesce(func.sum(Order.amount), 0)).filter(Order.status == "paid").scalar()
    total_orders = db.query(Order).count()

    recent_orders = (
        db.query(Order, User, Course)
        .join(User, User.id == Order.user_id)
        .join(Course, Course.id == Order.course_id)
        .order_by(Order.created_at.desc())
        .limit(8)
        .all()
    )

    return {
        "stats": {
            "total_students": total_students,
            "total_courses": total_courses,
            "total_revenue": int(total_revenue or 0),
            "total_orders": total_orders,
        },
        "recent_orders": [
            {
                "order_id": o.order_id,
                "student": u.full_name,
                "course": c.title,
                "amount": o.amount,
                "status": o.status,
                "created_at": o.created_at,
            }
            for o, u, c in recent_orders
        ],
    }


@router.get("/students")
def list_students(
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str = Query(default=""),
    is_active: str = Query(default="all"),
):
    query = db.query(User).filter(User.role == "student")
    if search:
        query = query.filter(or_(User.full_name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%")))
    if is_active == "active":
        query = query.filter(User.is_active == True)
    elif is_active == "inactive":
        query = query.filter(User.is_active == False)
    total = query.count()
    rows = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for r in rows:
        paid_orders = db.query(Order).filter(Order.user_id == r.id, Order.status == "paid")
        paid_count = paid_orders.count()
        total_spent = paid_orders.with_entities(func.coalesce(func.sum(Order.amount), 0)).scalar() or 0
        last_payment_at = paid_orders.order_by(Order.created_at.desc()).first()
        items.append(
            {
                "id": r.id,
                "full_name": r.full_name,
                "email": r.email,
                "is_active": r.is_active,
                "created_at": r.created_at,
                "paid_orders": paid_count,
                "total_spent": int(total_spent),
                "last_payment_at": last_payment_at.created_at if last_payment_at else None,
            }
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": max(1, (total + page_size - 1) // page_size)}


@router.patch("/students/{user_id}/status")
def student_status(user_id: int, is_active: bool, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    u = db.query(User).filter(User.id == user_id, User.role == "student").first()
    if not u:
        raise HTTPException(status_code=404, detail="Student not found")
    u.is_active = is_active
    db.commit()
    return {"message": "updated"}


@router.get("/instructors")
def list_instructors(
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str = Query(default=""),
):
    query = db.query(User).filter(User.role == "instructor")
    if search:
        query = query.filter(or_(User.full_name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%")))
    total = query.count()
    rows = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    out = []
    for r in rows:
        course_count = db.query(Course).filter(Course.instructor == r.full_name).count()
        total_students = (
            db.query(func.count(func.distinct(0)))
            .select_from(__import__("app.models", fromlist=["Enrollment"]).Enrollment)
            .join(Course, Course.id == __import__("app.models", fromlist=["Enrollment"]).Enrollment.course_id)
            .filter(Course.instructor == r.full_name)
            .scalar() or 0
        )
        out.append(
            {
                "id": r.id,
                "full_name": r.full_name,
                "email": r.email,
                "is_active": r.is_active,
                "created_at": r.created_at,
                "courses_count": course_count,
            }
        )
    return {"items": out, "total": total, "page": page, "page_size": page_size, "pages": max(1, (total + page_size - 1) // page_size)}


@router.get("/instructors/{instructor_id}/history")
def instructor_history(instructor_id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    inst = db.query(User).filter(User.id == instructor_id, User.role == "instructor").first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instructor not found")
    courses = db.query(Course).filter(Course.instructor == inst.full_name).order_by(Course.created_at.desc()).all()
    course_rows = []
    total_enrollments = 0
    total_revenue = 0
    for c in courses:
        enroll_count = db.query(Enrollment).filter(Enrollment.course_id == c.id).count()
        revenue = db.query(func.coalesce(func.sum(Order.amount), 0)).filter(Order.course_id == c.id, Order.status == "paid").scalar() or 0
        total_enrollments += enroll_count
        total_revenue += int(revenue)
        course_rows.append(
            {
                "id": c.id,
                "title": c.title,
                "slug": c.slug,
                "status": c.status,
                "enrollments": enroll_count,
                "revenue": int(revenue),
                "created_at": c.created_at,
            }
        )
    return {
        "id": inst.id,
        "full_name": inst.full_name,
        "email": inst.email,
        "is_active": inst.is_active,
        "joined_at": inst.created_at,
        "courses_count": len(course_rows),
        "total_enrollments": total_enrollments,
        "total_revenue": total_revenue,
        "courses": course_rows,
    }


@router.get("/courses/insights")
def course_insights(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    rows = db.query(Course).order_by(Course.created_at.desc()).all()
    items = []
    for c in rows:
        enrolled = db.query(Enrollment).filter(Enrollment.course_id == c.id).count()
        live_students = db.query(Enrollment).filter(Enrollment.course_id == c.id, Enrollment.completed == False).count()
        income = db.query(func.coalesce(func.sum(Order.amount), 0)).filter(Order.course_id == c.id, Order.status == "paid").scalar() or 0
        items.append(
            {
                "id": c.id,
                "slug": c.slug,
                "title": c.title,
                "thumbnail": c.thumbnail,
                "description": c.description,
                "price": c.price,
                "discountPrice": c.discount_price,
                "category": c.category,
                "instructor": c.instructor,
                "lessonsCount": c.lessons_count,
                "quizzesCount": c.quizzes_count,
                "durationMinutes": c.duration_minutes,
                "studentsCount": c.students_count,
                "rating": c.rating,
                "status": c.status,
                "enrolledCount": enrolled,
                "income": int(income),
                "liveStudents": live_students,
            }
        )
    return {"items": items, "total": len(items)}


@router.post("/instructors")
def create_instructor(full_name: str, email: str, password: str, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    from app.utils.security import hash_password

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email exists")
    u = User(full_name=full_name, email=email, password_hash=hash_password(password), role="instructor", is_active=True)
    db.add(u)
    db.commit()
    return {"message": "created", "id": u.id}


@router.get("/categories")
def list_categories(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    rows = db.query(Category).order_by(Category.created_at.desc()).all()
    out = []
    for r in rows:
        count = db.query(Course).filter(Course.category == r.name).count()
        out.append({"id": r.id, "name": r.name, "slug": r.slug, "is_active": r.is_active, "courses_count": count})
    return {"items": out}


@router.post("/categories")
def create_category(name: str, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    slug = slugify(name)
    if db.query(Category).filter(Category.slug == slug).first():
        raise HTTPException(status_code=409, detail="Category exists")
    c = Category(name=name, slug=slug, is_active=True)
    db.add(c)
    db.commit()
    return {"message": "created", "id": c.id}


@router.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    c = db.query(Category).filter(Category.id == category_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(c)
    db.commit()
    return {"message": "deleted"}


@router.get("/orders")
def list_orders(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    rows = (
        db.query(Order, User, Course)
        .join(User, User.id == Order.user_id)
        .join(Course, Course.id == Order.course_id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": o.id,
                "order_id": o.order_id,
                "razorpay_order_id": o.razorpay_order_id,
                "razorpay_payment_id": o.razorpay_payment_id,
                "student": u.full_name,
                "student_email": u.email,
                "course": c.title,
                "course_slug": c.slug,
                "amount": o.amount,
                "status": o.status,
                "created_at": o.created_at,
            }
            for o, u, c in rows
        ]
    }


@router.get("/orders/{order_id}")
def order_detail(order_id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    row = (
        db.query(Order, User, Course)
        .join(User, User.id == Order.user_id)
        .join(Course, Course.id == Order.course_id)
        .filter(Order.id == order_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    o, u, c = row
    return {
        "id": o.id,
        "order_id": o.order_id,
        "razorpay_order_id": o.razorpay_order_id,
        "razorpay_payment_id": o.razorpay_payment_id,
        "status": o.status,
        "amount": o.amount,
        "created_at": o.created_at,
        "student": {"id": u.id, "name": u.full_name, "email": u.email},
        "course": {"id": c.id, "title": c.title, "slug": c.slug, "price": c.price, "discount_price": c.discount_price},
    }


@router.patch("/orders/{order_id}/status")
def order_status(order_id: int, status: str, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    o.status = status
    db.commit()
    return {"message": "updated"}


@router.get("/coupons")
def list_coupons(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    rows = db.query(Coupon).order_by(Coupon.created_at.desc()).all()
    return {
        "items": [
            {
                "id": r.id,
                "code": r.code,
                "discount_percent": r.discount_percent,
                "max_uses": r.max_uses,
                "used_count": r.used_count,
                "utilized_percent": int((r.used_count / r.max_uses) * 100) if r.max_uses else 0,
                "is_active": r.is_active,
            }
            for r in rows
        ]
    }


@router.post("/coupons")
def create_coupon(code: str, discount_percent: int, max_uses: int = 100, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    if db.query(Coupon).filter(Coupon.code == code).first():
        raise HTTPException(status_code=409, detail="Coupon exists")
    c = Coupon(code=code.upper(), discount_percent=discount_percent, max_uses=max_uses, used_count=0, is_active=True)
    db.add(c)
    db.commit()
    return {"message": "created", "id": c.id}


@router.patch("/coupons/{coupon_id}/status")
def coupon_status(coupon_id: int, is_active: bool, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    c = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Coupon not found")
    c.is_active = is_active
    db.commit()
    return {"message": "updated"}


@router.get("/reviews")
def list_reviews(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    rows = (
        db.query(Review, User, Course)
        .join(User, User.id == Review.user_id)
        .join(Course, Course.id == Review.course_id)
        .order_by(Review.created_at.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": r.id,
                "student": u.full_name,
                "course": c.title,
                "rating": r.rating,
                "comment": r.comment,
                "status": r.status,
                "created_at": r.created_at,
            }
            for r, u, c in rows
        ]
    }


@router.patch("/reviews/{review_id}/status")
def review_status(review_id: int, status: str, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    r = db.query(Review).filter(Review.id == review_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    r.status = status
    db.commit()
    return {"message": "updated"}


@router.get("/certificates")
def list_certificates(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    rows = (
        db.query(Certificate, User, Course)
        .join(User, User.id == Certificate.user_id)
        .join(Course, Course.id == Certificate.course_id)
        .order_by(Certificate.created_at.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": c.id,
                "certificate_no": c.certificate_no,
                "student": u.full_name,
                "course": cr.title,
                "file_path": c.file_path,
                "created_at": c.created_at,
            }
            for c, u, cr in rows
        ]
    }


@router.get("/settings")
def list_settings(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    rows = db.query(SiteSetting).order_by(SiteSetting.key.asc()).all()
    return {"items": [{"id": r.id, "key": r.key, "value": r.value} for r in rows]}


@router.put("/settings")
def upsert_setting(key: str, value: str, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    if key.startswith("social_"):
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid social URL")
    row = db.query(SiteSetting).filter(SiteSetting.key == key).first()
    if row:
        row.value = value
    else:
        row = SiteSetting(key=key, value=value)
        db.add(row)
    db.commit()
    return {"message": "saved"}
