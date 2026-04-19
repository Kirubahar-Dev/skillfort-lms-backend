import base64
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import (
    CompilerSession,
    InterviewDomain,
    InterviewQuestion,
    InterviewTopic,
    MockInterview,
    MockInterviewAnswer,
    QuestionCompany,
    QuestionCompanyMap,
    QuestionTag,
    QuestionTagMap,
    QuestionTestCase,
    StudyPlannerDay,
    StudyPlannerTemplate,
    UserBookmark,
)
from app.schemas.interview import (
    CompilerRunRequest,
    CompilerRunResponse,
    InterviewQuestionCreate,
    InterviewQuestionListResponse,
    InterviewQuestionUpdate,
    MockSubmitRequest,
    PlannerProgressRequest,
    TopicPayload,
    CompanyPayload,
)
from app.utils.config import get_settings
from app.utils.database import get_db
from app.utils.deps import get_current_user, require_role
from app.utils.text import slugify

router = APIRouter(prefix="/api/interview", tags=["interview"])
settings = get_settings()


def ensure_domain(db: Session, name_or_slug: str) -> InterviewDomain:
    slug = slugify(name_or_slug)
    domain = db.query(InterviewDomain).filter(InterviewDomain.slug == slug).first()
    if domain:
        return domain
    domain = InterviewDomain(name=name_or_slug, slug=slug, color_hex="#6C63FF")
    db.add(domain)
    db.flush()
    return domain


def to_question_out(db: Session, question: InterviewQuestion):
    bookmark_count = db.query(UserBookmark).filter(UserBookmark.question_id == question.id).count()
    return {
        "id": question.id,
        "slug": question.slug,
        "title": question.title,
        "difficulty": question.difficulty,
        "domain": question.domain.slug if question.domain else "general",
        "type": question.type,
        "tags": [t.tag.slug for t in question.tags],
        "companies": [c.company.name for c in question.companies],
        "views": question.views,
        "bookmarks": bookmark_count,
        "body": question.body,
        "hint": question.hint,
        "answer": question.answer,
        "boilerplate_py": question.boilerplate_py or "",
        "test_cases": [{"input": t.input, "expected_output": t.expected_output, "is_hidden": t.is_hidden} for t in question.test_cases],
    }


@router.get("/questions", response_model=InterviewQuestionListResponse)
def list_questions(
    domain: str | None = None,
    difficulty: str | None = None,
    type: str | None = None,
    company: str | None = None,
    tag: str | None = None,
    search: str | None = None,
    sort: str = Query(default="newest"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = db.query(InterviewQuestion).options(
        joinedload(InterviewQuestion.domain),
        joinedload(InterviewQuestion.tags).joinedload(QuestionTagMap.tag),
        joinedload(InterviewQuestion.companies).joinedload(QuestionCompanyMap.company),
        joinedload(InterviewQuestion.test_cases),
    ).filter(InterviewQuestion.status == "published")

    if domain:
        query = query.join(InterviewDomain, InterviewQuestion.domain_id == InterviewDomain.id).filter(InterviewDomain.slug == slugify(domain))
    if difficulty:
        query = query.filter(InterviewQuestion.difficulty.ilike(difficulty))
    if type:
        query = query.filter(InterviewQuestion.type.ilike(type))
    if search:
        query = query.filter(InterviewQuestion.title.ilike(f"%{search}%"))
    if company:
        query = query.join(QuestionCompanyMap, QuestionCompanyMap.question_id == InterviewQuestion.id).join(
            QuestionCompany, QuestionCompany.id == QuestionCompanyMap.company_id
        ).filter(QuestionCompany.slug == slugify(company))
    if tag:
        query = query.join(QuestionTagMap, QuestionTagMap.question_id == InterviewQuestion.id).join(
            QuestionTag, QuestionTag.id == QuestionTagMap.tag_id
        ).filter(QuestionTag.slug == slugify(tag))

    if sort == "most_viewed":
        query = query.order_by(InterviewQuestion.views.desc())
    elif sort == "difficulty_easy":
        query = query.order_by(func.case((InterviewQuestion.difficulty == "easy", 0), (InterviewQuestion.difficulty == "medium", 1), else_=2))
    elif sort == "difficulty_hard":
        query = query.order_by(func.case((InterviewQuestion.difficulty == "hard", 0), (InterviewQuestion.difficulty == "medium", 1), else_=2))
    else:
        query = query.order_by(InterviewQuestion.created_at.desc())

    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [to_question_out(db, q) for q in rows], "total": total}


@router.get("/questions/{id}/{slug}")
def get_question(id: int, slug: str, db: Session = Depends(get_db)):
    q = db.query(InterviewQuestion).options(
        joinedload(InterviewQuestion.domain),
        joinedload(InterviewQuestion.tags).joinedload(QuestionTagMap.tag),
        joinedload(InterviewQuestion.companies).joinedload(QuestionCompanyMap.company),
        joinedload(InterviewQuestion.test_cases),
    ).filter(InterviewQuestion.id == id, InterviewQuestion.slug == slug).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return to_question_out(db, q)


@router.post("/questions")
def create_question(payload: InterviewQuestionCreate, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    domain = ensure_domain(db, payload.domain)
    q = InterviewQuestion(
        title=payload.title,
        slug=slugify(payload.title),
        body=payload.body,
        domain_id=domain.id,
        difficulty=payload.difficulty,
        type=payload.type,
        hint=payload.hint,
        answer=payload.answer,
        boilerplate_py=payload.boilerplate_py,
        boilerplate_js=payload.boilerplate_js,
        boilerplate_java=payload.boilerplate_java,
        boilerplate_cpp=payload.boilerplate_cpp,
        time_complexity=payload.time_complexity,
        space_complexity=payload.space_complexity,
        status=payload.status,
        meta_title=payload.meta_title,
        meta_description=payload.meta_description,
    )
    db.add(q)
    db.flush()

    for t in payload.tags:
        ts = slugify(t)
        tag_obj = db.query(QuestionTag).filter(QuestionTag.slug == ts).first()
        if not tag_obj:
            tag_obj = QuestionTag(name=t, slug=ts)
            db.add(tag_obj)
            db.flush()
        db.add(QuestionTagMap(question_id=q.id, tag_id=tag_obj.id))

    for c in payload.companies:
        cs = slugify(c)
        comp = db.query(QuestionCompany).filter(QuestionCompany.slug == cs).first()
        if not comp:
            comp = QuestionCompany(name=c, slug=cs)
            db.add(comp)
            db.flush()
        db.add(QuestionCompanyMap(question_id=q.id, company_id=comp.id))

    for tc in payload.test_cases:
        db.add(
            QuestionTestCase(
                question_id=q.id,
                input=tc.get("input", ""),
                expected_output=tc.get("expected_output", ""),
                is_hidden=bool(tc.get("is_hidden", False)),
            )
        )

    db.commit()
    return {"message": "created", "id": q.id, "slug": q.slug}


@router.put("/questions/{id}")
def update_question(id: int, payload: InterviewQuestionUpdate, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    q = db.query(InterviewQuestion).filter(InterviewQuestion.id == id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    updates = payload.model_dump(exclude_unset=True)
    if "domain" in updates:
        domain = ensure_domain(db, updates.pop("domain"))
        q.domain_id = domain.id

    if "title" in updates:
        q.slug = slugify(updates["title"])

    for k, v in updates.items():
        if k in {"tags", "companies", "test_cases"}:
            continue
        setattr(q, k, v)

    if "tags" in updates:
        db.query(QuestionTagMap).filter(QuestionTagMap.question_id == q.id).delete()
        for t in updates["tags"]:
            ts = slugify(t)
            tag_obj = db.query(QuestionTag).filter(QuestionTag.slug == ts).first()
            if not tag_obj:
                tag_obj = QuestionTag(name=t, slug=ts)
                db.add(tag_obj)
                db.flush()
            db.add(QuestionTagMap(question_id=q.id, tag_id=tag_obj.id))

    if "companies" in updates:
        db.query(QuestionCompanyMap).filter(QuestionCompanyMap.question_id == q.id).delete()
        for c in updates["companies"]:
            cs = slugify(c)
            comp = db.query(QuestionCompany).filter(QuestionCompany.slug == cs).first()
            if not comp:
                comp = QuestionCompany(name=c, slug=cs)
                db.add(comp)
                db.flush()
            db.add(QuestionCompanyMap(question_id=q.id, company_id=comp.id))

    if "test_cases" in updates:
        db.query(QuestionTestCase).filter(QuestionTestCase.question_id == q.id).delete()
        for tc in updates["test_cases"]:
            db.add(
                QuestionTestCase(
                    question_id=q.id,
                    input=tc.get("input", ""),
                    expected_output=tc.get("expected_output", ""),
                    is_hidden=bool(tc.get("is_hidden", False)),
                )
            )

    db.commit()
    return {"message": "updated"}


@router.delete("/questions/{id}")
def delete_question(id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    q = db.query(InterviewQuestion).filter(InterviewQuestion.id == id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(q)
    db.commit()
    return {"message": "deleted"}


@router.post("/questions/{id}/view")
def increment_view(id: int, db: Session = Depends(get_db)):
    q = db.query(InterviewQuestion).filter(InterviewQuestion.id == id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    q.views += 1
    db.commit()
    return {"views": q.views}


@router.post("/bookmarks/toggle")
def toggle_bookmark(question_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    existing = db.query(UserBookmark).filter(UserBookmark.user_id == user.id, UserBookmark.question_id == question_id).first()
    if existing:
        db.delete(existing)
        saved = False
    else:
        db.add(UserBookmark(user_id=user.id, question_id=question_id))
        saved = True
    db.commit()
    count = db.query(UserBookmark).filter(UserBookmark.user_id == user.id).count()
    return {"saved": saved, "count": count}


@router.get("/bookmarks/my")
def my_bookmarks(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = (
        db.query(InterviewQuestion)
        .join(UserBookmark, UserBookmark.question_id == InterviewQuestion.id)
        .filter(UserBookmark.user_id == user.id)
        .all()
    )
    return {"items": [to_question_out(db, q) for q in rows]}


@router.get("/topics")
def list_topics(db: Session = Depends(get_db)):
    rows = db.query(InterviewTopic).options(joinedload(InterviewTopic.domain)).all()
    items = []
    for t in rows:
        q_count = db.query(InterviewQuestion).filter(InterviewQuestion.domain_id == t.domain_id, InterviewQuestion.status == "published").count()
        items.append(
            {
                "id": t.id,
                "slug": t.slug,
                "name": t.name,
                "domain": t.domain.slug if t.domain else "general",
                "description": t.description,
                "status": t.status,
                "count": q_count,
            }
        )
    return {"items": items}


@router.get("/topics/{slug}")
def topic_detail(slug: str, db: Session = Depends(get_db)):
    t = db.query(InterviewTopic).options(joinedload(InterviewTopic.domain)).filter(InterviewTopic.slug == slug).first()
    related = []
    if t:
        related = (
            db.query(InterviewQuestion)
            .filter(InterviewQuestion.domain_id == t.domain_id, InterviewQuestion.status == "published")
            .order_by(InterviewQuestion.views.desc())
            .limit(15)
            .all()
        )
    else:
        domain = db.query(InterviewDomain).filter(InterviewDomain.slug == slug).first()
        if not domain:
            raise HTTPException(status_code=404, detail="Topic not found")
        related = (
            db.query(InterviewQuestion)
            .filter(InterviewQuestion.domain_id == domain.id, InterviewQuestion.status == "published")
            .order_by(InterviewQuestion.views.desc())
            .limit(15)
            .all()
        )
        t = InterviewTopic(
            id=0,
            slug=slug,
            name=domain.name,
            domain_id=domain.id,
            description=f"Core interview questions and patterns for {domain.name}.",
            cheat_sheet=f"Quick revision points for {domain.name}.",
            study_resources_json=[{"label": "Skillfort Interview Prep", "url": "https://course.skillfortinstitute.com"}],
            status="published",
        )
    return {
        "id": t.id,
        "slug": t.slug,
        "name": t.name,
        "domain": t.domain.slug if t.domain else "general",
        "description": t.description,
        "cheat_sheet": t.cheat_sheet,
        "study_resources_json": t.study_resources_json or [],
        "questions": [to_question_out(db, q) for q in related],
        "patterns": ["Recognize recurrence", "Pick state", "Optimize transitions"],
    }


@router.post("/topics")
def create_topic(payload: TopicPayload, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    domain = ensure_domain(db, payload.domain)
    t = InterviewTopic(
        name=payload.name,
        slug=payload.slug,
        domain_id=domain.id,
        description=payload.description,
        cheat_sheet=payload.cheat_sheet,
        study_resources_json=payload.study_resources_json,
        status=payload.status,
    )
    db.add(t)
    db.commit()
    return {"message": "created", "id": t.id}


@router.put("/topics/{id}")
def update_topic(id: int, payload: TopicPayload, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    t = db.query(InterviewTopic).filter(InterviewTopic.id == id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Topic not found")
    domain = ensure_domain(db, payload.domain)
    t.name = payload.name
    t.slug = payload.slug
    t.domain_id = domain.id
    t.description = payload.description
    t.cheat_sheet = payload.cheat_sheet
    t.study_resources_json = payload.study_resources_json
    t.status = payload.status
    db.commit()
    return {"message": "updated"}


@router.delete("/topics/{id}")
def delete_topic(id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    t = db.query(InterviewTopic).filter(InterviewTopic.id == id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Topic not found")
    db.delete(t)
    db.commit()
    return {"message": "deleted"}


@router.get("/companies")
def list_companies(db: Session = Depends(get_db)):
    rows = db.query(QuestionCompany).all()
    items = []
    for c in rows:
        q_count = db.query(QuestionCompanyMap).filter(QuestionCompanyMap.company_id == c.id).count()
        items.append(
            {
                "id": c.id,
                "name": c.name,
                "slug": c.slug,
                "logo_url": c.logo_url,
                "interview_process": c.interview_process,
                "questions_tagged": q_count,
            }
        )
    return {"items": items}


@router.get("/companies/{slug}")
def company_detail(slug: str, db: Session = Depends(get_db)):
    c = db.query(QuestionCompany).filter(QuestionCompany.slug == slug).first()
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")
    qs = (
        db.query(InterviewQuestion)
        .join(QuestionCompanyMap, QuestionCompanyMap.question_id == InterviewQuestion.id)
        .filter(QuestionCompanyMap.company_id == c.id)
        .all()
    )
    return {"id": c.id, "name": c.name, "slug": c.slug, "logo_url": c.logo_url, "interview_process": c.interview_process, "questions": [to_question_out(db, q) for q in qs]}


@router.post("/companies")
def create_company(payload: CompanyPayload, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    if db.query(QuestionCompany).filter(QuestionCompany.slug == payload.slug).first():
        raise HTTPException(status_code=409, detail="Company slug already exists")
    c = QuestionCompany(name=payload.name, slug=payload.slug, logo_url=payload.logo_url, interview_process=payload.interview_process)
    db.add(c)
    db.commit()
    return {"message": "created", "id": c.id}


@router.put("/companies/{id}")
def update_company(id: int, payload: CompanyPayload, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    c = db.query(QuestionCompany).filter(QuestionCompany.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")
    c.name = payload.name
    c.slug = payload.slug
    c.logo_url = payload.logo_url
    c.interview_process = payload.interview_process
    db.commit()
    return {"message": "updated"}


@router.post("/mock/generate")
def generate_mock(domain: str = "dsa", difficulty: str = "mixed", total_q: int = 5, db: Session = Depends(get_db), _=Depends(get_current_user)):
    query = db.query(InterviewQuestion).filter(InterviewQuestion.status == "published")
    if domain:
        d = db.query(InterviewDomain).filter(InterviewDomain.slug == slugify(domain)).first()
        if d:
            query = query.filter(InterviewQuestion.domain_id == d.id)
    if difficulty != "mixed":
        query = query.filter(InterviewQuestion.difficulty == difficulty)
    qs = query.order_by(func.random()).limit(total_q).all()
    return {"items": [to_question_out(db, q) for q in qs], "domain": domain, "difficulty": difficulty}


@router.post("/mock/submit")
def submit_mock(payload: MockSubmitRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    mock = MockInterview(user_id=user.id, domain=payload.domain, difficulty=payload.difficulty, total_q=payload.total_q, score=payload.score)
    db.add(mock)
    db.flush()
    for ans in payload.answers:
        db.add(
            MockInterviewAnswer(
                mock_id=mock.id,
                question_id=ans.get("question_id"),
                user_answer=ans.get("user_answer", ""),
                is_correct=bool(ans.get("is_correct", False)),
            )
        )
    db.commit()
    return {"message": "Mock saved", "id": mock.id}


@router.get("/mock/my")
def my_mock_history(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(MockInterview).filter(MockInterview.user_id == user.id).order_by(MockInterview.completed_at.desc()).all()
    return {"items": [{"id": r.id, "domain": r.domain, "difficulty": r.difficulty, "total_q": r.total_q, "score": r.score, "completed_at": r.completed_at} for r in rows]}


@router.get("/mock/{id}")
def mock_detail(id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    r = db.query(MockInterview).filter(MockInterview.id == id, MockInterview.user_id == user.id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Mock not found")
    answers = db.query(MockInterviewAnswer).filter(MockInterviewAnswer.mock_id == r.id).all()
    return {
        "id": r.id,
        "domain": r.domain,
        "difficulty": r.difficulty,
        "score": r.score,
        "answers": [{"question_id": a.question_id, "user_answer": a.user_answer, "is_correct": a.is_correct} for a in answers],
    }


@router.post("/compiler/run", response_model=CompilerRunResponse)
async def run_compiler(payload: CompilerRunRequest):
    language_ids = {"python": 71, "javascript": 63, "java": 62, "cpp": 54, "c": 50, "sql": 82}
    lang_id = language_ids.get(payload.language.lower())
    if not lang_id:
        raise HTTPException(status_code=400, detail="Unsupported language")

    if not settings.judge0_api_key:
        return CompilerRunResponse(status="Success", stdout="Judge0 key missing. Running in local demo mode.")

    headers = {
        "X-RapidAPI-Key": settings.judge0_api_key,
        "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com",
        "Content-Type": "application/json",
    }

    body = {
        "source_code": base64.b64encode(payload.code.encode()).decode(),
        "language_id": lang_id,
        "stdin": base64.b64encode(payload.stdin.encode()).decode() if payload.stdin else "",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        create = await client.post(f"{settings.judge0_api_url}/submissions?base64_encoded=true&wait=true", headers=headers, json=body)
        create.raise_for_status()
        out = create.json()

    stdout = base64.b64decode(out["stdout"]).decode() if out.get("stdout") else ""
    stderr = base64.b64decode(out["stderr"]).decode() if out.get("stderr") else ""

    return CompilerRunResponse(
        status=out.get("status", {}).get("description", "Unknown"),
        stdout=stdout,
        stderr=stderr,
        execution_time=str(out.get("time", "")),
        memory=str(out.get("memory", "")),
    )


@router.post("/compiler/share")
def share_code(language: str, code: str, db: Session = Depends(get_db)):
    token = uuid.uuid4().hex[:12]
    item = CompilerSession(session_token=token, language=language, code=code)
    db.add(item)
    db.commit()
    return {"token": token, "url": f"/interview-prep/compiler?share={token}"}


@router.get("/compiler/share/{token}")
def get_shared_code(token: str, db: Session = Depends(get_db)):
    item = db.query(CompilerSession).filter(CompilerSession.session_token == token).first()
    if not item:
        raise HTTPException(status_code=404, detail="Share not found")
    return {"language": item.language, "code": item.code, "output": item.output}


@router.get("/planner/templates")
def planner_templates(db: Session = Depends(get_db)):
    rows = db.query(StudyPlannerTemplate).all()
    return {"items": [{"id": x.id, "name": x.name, "duration_days": x.duration_days, "description": x.description} for x in rows]}


@router.get("/planner/templates/{id}")
def planner_template_detail(id: int, db: Session = Depends(get_db)):
    t = db.query(StudyPlannerTemplate).filter(StudyPlannerTemplate.id == id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    days = db.query(StudyPlannerDay).filter(StudyPlannerDay.template_id == id).order_by(StudyPlannerDay.day_number.asc()).all()
    if not days:
        days = [StudyPlannerDay(day_number=d, template_id=id, topic_slug="dynamic-programming", question_count=8, est_minutes=90) for d in range(1, t.duration_days + 1)]
        db.add_all(days)
        db.commit()
    return {
        "id": t.id,
        "name": t.name,
        "days": [{"day_number": d.day_number, "topic_slug": d.topic_slug, "question_count": d.question_count, "est_minutes": d.est_minutes} for d in days],
    }


@router.post("/planner/progress")
def mark_progress(payload: PlannerProgressRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    from app.models import UserStudyPlannerProgress

    existing = db.query(UserStudyPlannerProgress).filter(
        UserStudyPlannerProgress.user_id == user.id,
        UserStudyPlannerProgress.template_id == payload.template_id,
        UserStudyPlannerProgress.day_number == payload.day_number,
    ).first()
    if not existing:
        db.add(UserStudyPlannerProgress(user_id=user.id, template_id=payload.template_id, day_number=payload.day_number))
        db.commit()
    count = db.query(UserStudyPlannerProgress).filter(
        UserStudyPlannerProgress.user_id == user.id,
        UserStudyPlannerProgress.template_id == payload.template_id,
    ).count()
    return {"completed": count}


@router.get("/planner/my-progress")
def my_progress(template_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    from app.models import UserStudyPlannerProgress

    rows = db.query(UserStudyPlannerProgress).filter(
        UserStudyPlannerProgress.user_id == user.id,
        UserStudyPlannerProgress.template_id == template_id,
    ).all()
    return {"days": sorted([r.day_number for r in rows])}


@router.get("/admin/analytics/overview")
def analytics_overview(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    return {
        "question_views_30d": db.query(func.coalesce(func.sum(InterviewQuestion.views), 0)).scalar(),
        "bookmarks": db.query(UserBookmark).count(),
        "compiler_sessions": db.query(CompilerSession).count(),
        "mock_completions": db.query(MockInterview).count(),
    }


@router.get("/admin/analytics/top-questions")
def top_questions(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    rows = db.query(InterviewQuestion).order_by(InterviewQuestion.views.desc()).limit(10).all()
    return {"items": [{"id": r.id, "title": r.title, "views": r.views} for r in rows]}


@router.get("/admin/analytics/compiler-stats")
def compiler_stats(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    rows = (
        db.query(CompilerSession.language, func.count(CompilerSession.id))
        .group_by(CompilerSession.language)
        .all()
    )
    return {"items": [{"language": r[0], "count": r[1]} for r in rows]}
