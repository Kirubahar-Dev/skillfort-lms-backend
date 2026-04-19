from pydantic import BaseModel, Field


class ContactRequest(BaseModel):
    name: str
    email: str
    phone: str | None = None
    subject: str
    message: str = Field(..., min_length=3)


class InterviewQuestionCreate(BaseModel):
    title: str
    body: str
    domain: str
    difficulty: str
    type: str
    tags: list[str] = []
    companies: list[str] = []
    hint: str | None = None
    answer: str | None = None
    boilerplate_py: str | None = ""
    boilerplate_js: str | None = ""
    boilerplate_java: str | None = ""
    boilerplate_cpp: str | None = ""
    test_cases: list[dict] = []
    time_complexity: str | None = None
    space_complexity: str | None = None
    status: str = "draft"
    meta_title: str | None = None
    meta_description: str | None = None


class InterviewQuestionUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    domain: str | None = None
    difficulty: str | None = None
    type: str | None = None
    tags: list[str] | None = None
    companies: list[str] | None = None
    hint: str | None = None
    answer: str | None = None
    boilerplate_py: str | None = None
    boilerplate_js: str | None = None
    boilerplate_java: str | None = None
    boilerplate_cpp: str | None = None
    test_cases: list[dict] | None = None
    time_complexity: str | None = None
    space_complexity: str | None = None
    status: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None


class InterviewQuestionOut(BaseModel):
    id: int
    slug: str
    title: str
    difficulty: str
    domain: str
    type: str
    tags: list[str]
    companies: list[str]
    views: int
    bookmarks: int
    body: str
    hint: str | None = None
    answer: str | None = None
    boilerplate_py: str = ""
    test_cases: list[dict] = []


class InterviewQuestionListResponse(BaseModel):
    items: list[InterviewQuestionOut]
    total: int


class TopicPayload(BaseModel):
    name: str
    slug: str
    domain: str
    description: str = ""
    cheat_sheet: str = ""
    study_resources_json: list[dict] = []
    status: str = "published"


class CompanyPayload(BaseModel):
    name: str
    slug: str
    logo_url: str | None = None
    interview_process: str | None = None


class CompilerRunRequest(BaseModel):
    language: str
    code: str
    stdin: str = ""


class CompilerRunResponse(BaseModel):
    status: str
    stdout: str | None = None
    stderr: str | None = None
    execution_time: str | None = None
    memory: str | None = None


class MockSubmitRequest(BaseModel):
    domain: str
    difficulty: str
    total_q: int
    score: int
    answers: list[dict] = []


class PlannerProgressRequest(BaseModel):
    template_id: int
    day_number: int
