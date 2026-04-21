"""
Lesson Quiz Router
- AI-generated MCQ questions per lesson (Anthropic claude-3-5-haiku)
- Admin can generate, review, approve/reject, edit, add manually
- Students take quiz after watching video; pass (≥70%) marks lesson complete
"""
import json
import re
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.entities import (
    Course, CourseLesson, Enrollment, LessonProgress,
    LessonQuestion, LessonQuizAttempt, User, Certificate,
)
from app.utils.config import get_settings
from app.utils.database import get_db
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/quiz", tags=["quiz"])

PASS_THRESHOLD = 0.70   # 70 % correct to pass


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class QuizSubmit(BaseModel):
    answers: dict[str, str]   # {question_id: chosen_option}  e.g. {"3": "B"}


class QuestionCreate(BaseModel):
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str
    explanation: str = ""


class QuestionUpdate(BaseModel):
    question: str | None = None
    option_a: str | None = None
    option_b: str | None = None
    option_c: str | None = None
    option_d: str | None = None
    correct_option: str | None = None
    explanation: str | None = None
    status: str | None = None     # pending | approved | rejected


# ── Helpers ───────────────────────────────────────────────────────────────────

def _q_to_dict(q: LessonQuestion) -> dict:
    return {
        "id": q.id,
        "lesson_id": q.lesson_id,
        "question": q.question,
        "option_a": q.option_a,
        "option_b": q.option_b,
        "option_c": q.option_c,
        "option_d": q.option_d,
        "correct_option": q.correct_option,
        "explanation": q.explanation,
        "status": q.status,
        "source": q.source,
        "order_index": q.order_index,
    }


QUIZ_PROMPT = """You are an expert educational content creator. Generate exactly 4 multiple-choice quiz questions to test student understanding of this lesson.

Course: {course_title}
Section: {section_title}
Lesson: {lesson_title}

Requirements:
- Questions should test key concepts from the lesson topic
- Each question must have exactly 4 options (A, B, C, D)
- Only ONE correct answer per question
- Include a short explanation (1-2 sentences) for the correct answer
- Mix question types: recall, understanding, application

Return ONLY a valid JSON array with NO markdown, NO commentary, just the raw JSON:
[{{"question":"...","option_a":"...","option_b":"...","option_c":"...","option_d":"...","correct_option":"A","explanation":"..."}}]"""


def _extract_json(text: str) -> list[dict]:
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise RuntimeError("AI did not return a valid JSON array")
    data = json.loads(match.group())
    if not isinstance(data, list) or len(data) == 0:
        raise RuntimeError("AI returned empty question list")
    return data


async def _generate_via_groq(
    course_title: str, section_title: str, lesson_title: str, api_key: str
) -> list[dict]:
    prompt = QUIZ_PROMPT.format(
        course_title=course_title, section_title=section_title, lesson_title=lesson_title
    )
    async with httpx.AsyncClient(timeout=40) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2048,
                "temperature": 0.7,
            },
        )
    if r.status_code != 200:
        raise RuntimeError(f"Groq API error {r.status_code}: {r.text[:300]}")
    text = r.json()["choices"][0]["message"]["content"]
    return _extract_json(text)


async def _generate_via_anthropic(
    course_title: str, section_title: str, lesson_title: str, api_key: str
) -> list[dict]:
    prompt = QUIZ_PROMPT.format(
        course_title=course_title, section_title=section_title, lesson_title=lesson_title
    )
    async with httpx.AsyncClient(timeout=40) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-3-5-haiku-20241022",
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
    if r.status_code != 200:
        raise RuntimeError(f"Anthropic API error {r.status_code}: {r.text[:300]}")
    text = r.json()["content"][0]["text"]
    return _extract_json(text)


def _mark_lesson_complete(db: Session, user: User, lesson: CourseLesson):
    """Mark lesson as completed and recalculate course progress. Returns progress_percent."""
    prog = db.query(LessonProgress).filter(
        LessonProgress.student_id == user.id,
        LessonProgress.lesson_id == lesson.id,
    ).first()
    if not prog:
        prog = LessonProgress(
            student_id=user.id,
            lesson_id=lesson.id,
            course_id=lesson.course_id,
            completed=True,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(prog)
    elif not prog.completed:
        prog.completed = True
        prog.completed_at = datetime.now(timezone.utc)

    total = db.query(CourseLesson).filter(CourseLesson.course_id == lesson.course_id).count()
    done = db.query(LessonProgress).filter(
        LessonProgress.student_id == user.id,
        LessonProgress.course_id == lesson.course_id,
        LessonProgress.completed == True,
    ).count()
    pct = int((done / max(1, total)) * 100)

    enroll = db.query(Enrollment).filter(
        Enrollment.user_id == user.id,
        Enrollment.course_id == lesson.course_id,
    ).first()
    if enroll:
        enroll.progress_percent = pct

    db.commit()

    # Auto-certificate at 100 %
    if pct == 100:
        _ensure_cert(db, user, lesson.course_id)

    return pct


def _ensure_cert(db, user, course_id):
    import uuid
    cert = db.query(Certificate).filter(
        Certificate.user_id == user.id,
        Certificate.course_id == course_id,
    ).first()
    if not cert:
        cn = f"SF-{course_id:03d}-{user.id:05d}-{uuid.uuid4().hex[:6].upper()}"
        cert = Certificate(
            user_id=user.id, course_id=course_id,
            certificate_no=cn, file_path=f"/certificates/{cn}.pdf",
        )
        db.add(cert)
        db.commit()
    return cert


# ═══════════════════════════════════════════════════════════════════════════════
# STUDENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/lessons/{lesson_id}/questions")
def get_lesson_questions(
    lesson_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return approved questions for a lesson (student view — correct answer hidden)."""
    lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Lesson not found")

    # Verify enrollment (or allow admins/instructors)
    if user.role not in ("admin", "instructor"):
        enroll = db.query(Enrollment).filter(
            Enrollment.user_id == user.id,
            Enrollment.course_id == lesson.course_id,
        ).first()
        if not enroll:
            raise HTTPException(403, "Not enrolled in this course")

    questions = (
        db.query(LessonQuestion)
        .filter(LessonQuestion.lesson_id == lesson_id, LessonQuestion.status == "approved")
        .order_by(LessonQuestion.order_index, LessonQuestion.id)
        .all()
    )

    # Strip correct_option so frontend can't cheat via API response
    return [
        {
            "id": q.id,
            "question": q.question,
            "option_a": q.option_a,
            "option_b": q.option_b,
            "option_c": q.option_c,
            "option_d": q.option_d,
        }
        for q in questions
    ]


@router.post("/lessons/{lesson_id}/submit")
def submit_quiz(
    lesson_id: int,
    body: QuizSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Submit quiz answers. If passed → mark lesson complete and unlock next."""
    lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Lesson not found")

    # Verify enrollment
    enroll = db.query(Enrollment).filter(
        Enrollment.user_id == user.id,
        Enrollment.course_id == lesson.course_id,
    ).first()
    if not enroll:
        raise HTTPException(403, "Not enrolled in this course")

    questions = (
        db.query(LessonQuestion)
        .filter(LessonQuestion.lesson_id == lesson_id, LessonQuestion.status == "approved")
        .all()
    )
    if not questions:
        raise HTTPException(400, "No approved questions for this lesson")

    correct = 0
    results = []
    for q in questions:
        chosen = body.answers.get(str(q.id), "").upper()
        is_correct = chosen == q.correct_option.upper()
        if is_correct:
            correct += 1
        results.append({
            "id": q.id,
            "question": q.question,
            "chosen": chosen,
            "correct_option": q.correct_option,
            "is_correct": is_correct,
            "explanation": q.explanation,
        })

    total = len(questions)
    passed = (correct / total) >= PASS_THRESHOLD

    # Record attempt
    attempt = LessonQuizAttempt(
        student_id=user.id,
        lesson_id=lesson_id,
        score=correct,
        total=total,
        passed=passed,
    )
    db.add(attempt)
    db.commit()

    progress_percent = enroll.progress_percent
    if passed:
        progress_percent = _mark_lesson_complete(db, user, lesson)

    return {
        "passed": passed,
        "score": correct,
        "total": total,
        "percent": round((correct / total) * 100),
        "progress_percent": progress_percent,
        "results": results,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN / INSTRUCTOR ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

def _require_staff(user: User):
    if user.role not in ("admin", "instructor"):
        raise HTTPException(403, "Staff only")


@router.get("/admin/lessons/{lesson_id}/questions")
def admin_get_questions(
    lesson_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """All questions for a lesson (all statuses, correct answer included)."""
    _require_staff(user)
    qs = (
        db.query(LessonQuestion)
        .filter(LessonQuestion.lesson_id == lesson_id)
        .order_by(LessonQuestion.order_index, LessonQuestion.id)
        .all()
    )
    return [_q_to_dict(q) for q in qs]


@router.post("/admin/lessons/{lesson_id}/generate")
async def admin_generate_questions(
    lesson_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Use Anthropic Claude to generate 4 MCQ questions for this lesson."""
    _require_staff(user)
    settings = get_settings()

    if not settings.groq_api_key and not settings.anthropic_api_key:
        raise HTTPException(
            400,
            "No AI key configured. Add GROQ_API_KEY (free at groq.com) "
            "or ANTHROPIC_API_KEY to your environment variables.",
        )

    lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Lesson not found")

    course = db.query(Course).filter(Course.id == lesson.course_id).first()
    course_title = course.title if course else "Course"

    try:
        # Prefer Groq (free); fall back to Anthropic
        if settings.groq_api_key:
            generated = await _generate_via_groq(
                course_title, lesson.section_title, lesson.lesson_title,
                settings.groq_api_key,
            )
        else:
            generated = await _generate_via_anthropic(
                course_title, lesson.section_title, lesson.lesson_title,
                settings.anthropic_api_key,
            )
    except Exception as e:
        raise HTTPException(500, f"AI generation failed: {e}")

    created = []
    for i, item in enumerate(generated):
        correct = item.get("correct_option", "A").upper()
        if correct not in ("A", "B", "C", "D"):
            correct = "A"
        q = LessonQuestion(
            lesson_id=lesson_id,
            question=item.get("question", ""),
            option_a=item.get("option_a", ""),
            option_b=item.get("option_b", ""),
            option_c=item.get("option_c", ""),
            option_d=item.get("option_d", ""),
            correct_option=correct,
            explanation=item.get("explanation", ""),
            status="pending",
            source="ai",
            order_index=i,
        )
        db.add(q)
        created.append(q)

    db.commit()
    for q in created:
        db.refresh(q)

    return {"generated": len(created), "questions": [_q_to_dict(q) for q in created]}


@router.post("/admin/lessons/{lesson_id}/questions")
def admin_add_question(
    lesson_id: int,
    body: QuestionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Manually add a question."""
    _require_staff(user)
    if not db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first():
        raise HTTPException(404, "Lesson not found")

    correct = body.correct_option.upper()
    if correct not in ("A", "B", "C", "D"):
        raise HTTPException(400, "correct_option must be A, B, C or D")

    count = db.query(LessonQuestion).filter(LessonQuestion.lesson_id == lesson_id).count()
    q = LessonQuestion(
        lesson_id=lesson_id,
        question=body.question,
        option_a=body.option_a,
        option_b=body.option_b,
        option_c=body.option_c,
        option_d=body.option_d,
        correct_option=correct,
        explanation=body.explanation,
        status="approved",   # manually added = approved by default
        source="manual",
        order_index=count,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return _q_to_dict(q)


@router.patch("/admin/questions/{question_id}")
def admin_update_question(
    question_id: int,
    body: QuestionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update / approve / reject a question."""
    _require_staff(user)
    q = db.query(LessonQuestion).filter(LessonQuestion.id == question_id).first()
    if not q:
        raise HTTPException(404, "Question not found")

    for field, val in body.model_dump(exclude_none=True).items():
        setattr(q, field, val)
    db.commit()
    db.refresh(q)
    return _q_to_dict(q)


@router.delete("/admin/questions/{question_id}")
def admin_delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_staff(user)
    q = db.query(LessonQuestion).filter(LessonQuestion.id == question_id).first()
    if not q:
        raise HTTPException(404, "Question not found")
    db.delete(q)
    db.commit()
    return {"deleted": question_id}


@router.patch("/admin/questions/{question_id}/approve")
def admin_approve(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_staff(user)
    q = db.query(LessonQuestion).filter(LessonQuestion.id == question_id).first()
    if not q:
        raise HTTPException(404, "Question not found")
    q.status = "approved"
    db.commit()
    db.refresh(q)
    return _q_to_dict(q)


@router.patch("/admin/questions/{question_id}/reject")
def admin_reject(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_staff(user)
    q = db.query(LessonQuestion).filter(LessonQuestion.id == question_id).first()
    if not q:
        raise HTTPException(404, "Question not found")
    q.status = "rejected"
    db.commit()
    db.refresh(q)
    return _q_to_dict(q)
