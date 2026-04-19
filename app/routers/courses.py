from sqlalchemy import func
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.models import Course, CourseLesson, SiteSetting
from app.schemas.course import CourseCreate, CourseLessonOut, CourseLessonPayload, CourseListResponse, CourseOut, CourseUpdate
from app.utils.database import get_db
from app.utils.deps import require_role

router = APIRouter(prefix="/api/courses", tags=["courses"])


def to_out(course: Course) -> CourseOut:
    return CourseOut(
        id=course.id,
        slug=course.slug,
        title=course.title,
        thumbnail=course.thumbnail,
        description=course.description,
        price=course.price,
        discountPrice=course.discount_price,
        category=course.category,
        instructor=course.instructor,
        lessonsCount=course.lessons_count,
        quizzesCount=course.quizzes_count,
        durationMinutes=course.duration_minutes,
        studentsCount=course.students_count,
        rating=course.rating,
        status=course.status,
    )


def refresh_course_aggregates(db: Session, course: Course):
    total_duration = db.query(func.coalesce(func.sum(CourseLesson.duration_minutes), 0)).filter(CourseLesson.course_id == course.id).scalar() or 0
    lessons_count = db.query(CourseLesson).filter(CourseLesson.course_id == course.id).count()
    course.duration_minutes = int(total_duration)
    course.lessons_count = lessons_count


@router.get("", response_model=CourseListResponse)
def list_courses(
    category: str | None = None,
    price: str = Query(default="all"),
    sort: str = Query(default="latest"),
    db: Session = Depends(get_db),
):
    query = db.query(Course).filter(Course.status == "published")

    if category:
        query = query.filter(Course.category.ilike(f"%{category}%"))
    if price == "free":
        query = query.filter(Course.discount_price == 0)
    elif price == "paid":
        query = query.filter(Course.discount_price > 0)

    if sort == "price_low":
        query = query.order_by(Course.discount_price.asc())
    elif sort == "price_high":
        query = query.order_by(Course.discount_price.desc())
    elif sort == "oldest":
        query = query.order_by(Course.created_at.asc())
    else:
        query = query.order_by(Course.created_at.desc())

    items = query.all()
    return {"items": [to_out(x) for x in items], "total": len(items)}


@router.get("/admin/list", response_model=CourseListResponse)
def list_courses_admin(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    items = db.query(Course).order_by(Course.created_at.desc()).all()
    return {"items": [to_out(x) for x in items], "total": len(items)}


@router.post("/admin", response_model=CourseOut)
def create_course(payload: CourseCreate, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    if db.query(Course).filter(Course.slug == payload.slug).first():
        raise HTTPException(status_code=409, detail="Slug already exists")
    computed_duration = payload.durationMinutes if payload.durationMinutes and payload.durationMinutes > 0 else payload.lessonsCount * 35
    c = Course(
        slug=payload.slug,
        title=payload.title,
        thumbnail=payload.thumbnail,
        description=payload.description,
        price=payload.price,
        discount_price=payload.discountPrice,
        category=payload.category,
        instructor=payload.instructor,
        lessons_count=payload.lessonsCount,
        quizzes_count=payload.quizzesCount,
        duration_minutes=computed_duration,
        students_count=payload.studentsCount,
        rating=payload.rating,
        status=payload.status,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return to_out(c)


@router.put("/admin/{course_id}", response_model=CourseOut)
def update_course(course_id: int, payload: CourseUpdate, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    c = db.query(Course).filter(Course.id == course_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Course not found")

    updates = payload.model_dump(exclude_unset=True)
    mapper = {
        "discountPrice": "discount_price",
        "lessonsCount": "lessons_count",
        "quizzesCount": "quizzes_count",
        "durationMinutes": "duration_minutes",
        "studentsCount": "students_count",
    }
    for key, value in updates.items():
        setattr(c, mapper.get(key, key), value)

    if ("durationMinutes" in updates and (updates.get("durationMinutes") in [None, 0])) or (
        "lessonsCount" in updates and "durationMinutes" not in updates
    ):
        c.duration_minutes = (c.lessons_count or 0) * 35

    db.commit()
    db.refresh(c)
    return to_out(c)


@router.delete("/admin/{course_id}")
def delete_course(course_id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    c = db.query(Course).filter(Course.id == course_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Course not found")
    db.delete(c)
    db.commit()
    return {"message": "Deleted"}


@router.get("/admin/{course_id}/lessons", response_model=list[CourseLessonOut])
def list_course_lessons(course_id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    rows = db.query(CourseLesson).filter(CourseLesson.course_id == course_id).order_by(CourseLesson.order_index.asc(), CourseLesson.id.asc()).all()
    return [
        CourseLessonOut(
            id=r.id,
            course_id=r.course_id,
            section_title=r.section_title,
            lesson_title=r.lesson_title,
            duration_minutes=r.duration_minutes,
            video_url=r.video_url,
            order_index=r.order_index,
            is_preview=r.is_preview,
        )
        for r in rows
    ]


@router.post("/admin/{course_id}/lessons", response_model=CourseLessonOut)
def create_course_lesson(course_id: int, payload: CourseLessonPayload, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    row = CourseLesson(course_id=course_id, **payload.model_dump())
    db.add(row)
    db.flush()
    refresh_course_aggregates(db, course)
    db.commit()
    db.refresh(row)
    return CourseLessonOut(
        id=row.id,
        course_id=row.course_id,
        section_title=row.section_title,
        lesson_title=row.lesson_title,
        duration_minutes=row.duration_minutes,
        video_url=row.video_url,
        order_index=row.order_index,
        is_preview=row.is_preview,
    )


@router.put("/admin/lessons/{lesson_id}", response_model=CourseLessonOut)
def update_course_lesson(lesson_id: int, payload: CourseLessonPayload, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    row = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Lesson not found")
    for k, v in payload.model_dump().items():
        setattr(row, k, v)
    course = db.query(Course).filter(Course.id == row.course_id).first()
    if course:
        refresh_course_aggregates(db, course)
    db.commit()
    db.refresh(row)
    return CourseLessonOut(
        id=row.id,
        course_id=row.course_id,
        section_title=row.section_title,
        lesson_title=row.lesson_title,
        duration_minutes=row.duration_minutes,
        video_url=row.video_url,
        order_index=row.order_index,
        is_preview=row.is_preview,
    )


@router.delete("/admin/lessons/{lesson_id}")
def delete_course_lesson(lesson_id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    row = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Lesson not found")
    course = db.query(Course).filter(Course.id == row.course_id).first()
    db.delete(row)
    if course:
        refresh_course_aggregates(db, course)
    db.commit()
    return {"message": "Deleted"}


@router.get("/pages/{slug}")
def get_static_page(slug: str, db: Session = Depends(get_db)):
    mapping = {
        "about-us": ("about_us_content", "About Us"),
        "terms-conditions": ("terms_conditions_content", "Terms & Conditions"),
        "privacy-policy": ("privacy_policy_content", "Privacy Policy"),
    }
    if slug not in mapping:
        raise HTTPException(status_code=404, detail="Page not found")
    key, title = mapping[slug]
    row = db.query(SiteSetting).filter(SiteSetting.key == key).first()
    content = row.value if row and row.value else ""
    return {"slug": slug, "title": title, "content": content}


@router.get("/{slug}")
def get_course(slug: str, db: Session = Depends(get_db)):
    item = db.query(Course).filter(Course.slug == slug, Course.status == "published").first()
    if not item:
        raise HTTPException(status_code=404, detail="Course not found")
    refresh_course_aggregates(db, item)
    db.commit()
    lessons = (
        db.query(CourseLesson)
        .filter(CourseLesson.course_id == item.id)
        .order_by(CourseLesson.order_index.asc(), CourseLesson.id.asc())
        .all()
    )
    return {
        **to_out(item).model_dump(),
        "syllabus": [
            {
                "id": l.id,
                "section_title": l.section_title,
                "lesson_title": l.lesson_title,
                "duration_minutes": l.duration_minutes,
                "video_url": l.video_url,
                "order_index": l.order_index,
                "is_preview": l.is_preview,
            }
            for l in lessons
        ],
    }
