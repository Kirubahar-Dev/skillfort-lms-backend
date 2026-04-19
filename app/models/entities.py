from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from app.utils.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="student")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(150), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    thumbnail = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    price = Column(Integer, nullable=False)
    discount_price = Column(Integer, nullable=False)
    category = Column(String(100), nullable=False)
    instructor = Column(String(120), nullable=False)
    lessons_count = Column(Integer, default=0)
    quizzes_count = Column(Integer, default=0)
    duration_minutes = Column(Integer, default=0)
    students_count = Column(Integer, default=0)
    rating = Column(Float, default=0)
    status = Column(String(20), default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CourseLesson(Base):
    __tablename__ = "course_lessons"

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    section_title = Column(String(160), nullable=False)
    lesson_title = Column(String(180), nullable=False)
    duration_minutes = Column(Integer, default=15)
    video_url = Column(String(500), nullable=True)
    order_index = Column(Integer, default=0)
    is_preview = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(120), nullable=False)
    phone = Column(String(30), nullable=True)
    subject = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InterviewDomain(Base):
    __tablename__ = "interview_domains"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(120), unique=True, nullable=False)
    description = Column(Text)
    icon = Column(String(120))
    color_hex = Column(String(10))
    order = Column(Integer, default=0)


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    domain_id = Column(Integer, ForeignKey("interview_domains.id"), nullable=True)
    difficulty = Column(String(20), nullable=False)
    type = Column(String(30), nullable=False)
    hint = Column(Text)
    answer = Column(Text)
    boilerplate_py = Column(Text)
    boilerplate_js = Column(Text)
    boilerplate_java = Column(Text)
    boilerplate_cpp = Column(Text)
    time_complexity = Column(String(60))
    space_complexity = Column(String(60))
    views = Column(Integer, default=0)
    status = Column(String(20), default="draft")
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    domain = relationship("InterviewDomain")
    tags = relationship("QuestionTagMap", cascade="all, delete-orphan")
    companies = relationship("QuestionCompanyMap", cascade="all, delete-orphan")
    test_cases = relationship("QuestionTestCase", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("slug", name="uq_interview_questions_slug"),)


class QuestionTag(Base):
    __tablename__ = "question_tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)


class QuestionTagMap(Base):
    __tablename__ = "question_tag_map"

    question_id = Column(Integer, ForeignKey("interview_questions.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("question_tags.id"), primary_key=True)
    tag = relationship("QuestionTag")


class QuestionCompany(Base):
    __tablename__ = "question_companies"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(120), unique=True, nullable=False)
    logo_url = Column(String(500))
    interview_process = Column(Text)


class QuestionCompanyMap(Base):
    __tablename__ = "question_company_map"

    question_id = Column(Integer, ForeignKey("interview_questions.id"), primary_key=True)
    company_id = Column(Integer, ForeignKey("question_companies.id"), primary_key=True)
    company = relationship("QuestionCompany")


class QuestionTestCase(Base):
    __tablename__ = "question_test_cases"

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("interview_questions.id"), nullable=False)
    input = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=False)
    is_hidden = Column(Boolean, default=False)


class QuestionRelation(Base):
    __tablename__ = "question_relations"

    question_id = Column(Integer, ForeignKey("interview_questions.id"), primary_key=True)
    related_question_id = Column(Integer, ForeignKey("interview_questions.id"), primary_key=True)


class InterviewTopic(Base):
    __tablename__ = "interview_topics"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(140), unique=True, nullable=False)
    domain_id = Column(Integer, ForeignKey("interview_domains.id"), nullable=True)
    description = Column(Text)
    cheat_sheet = Column(Text)
    study_resources_json = Column(JSON)
    status = Column(String(20), default="published")

    domain = relationship("InterviewDomain")


class UserBookmark(Base):
    __tablename__ = "user_bookmarks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("interview_questions.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "question_id", name="uq_user_bookmark"),)


class MockInterview(Base):
    __tablename__ = "mock_interviews"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    domain = Column(String(50), nullable=False)
    difficulty = Column(String(20), nullable=False)
    total_q = Column(Integer, nullable=False)
    score = Column(Integer, nullable=False)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())


class MockInterviewAnswer(Base):
    __tablename__ = "mock_interview_answers"

    id = Column(Integer, primary_key=True)
    mock_id = Column(Integer, ForeignKey("mock_interviews.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("interview_questions.id"), nullable=False)
    user_answer = Column(Text)
    is_correct = Column(Boolean, default=False)


class StudyPlannerTemplate(Base):
    __tablename__ = "study_planner_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    duration_days = Column(Integer, nullable=False)
    description = Column(Text)


class StudyPlannerDay(Base):
    __tablename__ = "study_planner_days"

    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("study_planner_templates.id"), nullable=False)
    day_number = Column(Integer, nullable=False)
    topic_slug = Column(String(140), nullable=False)
    question_count = Column(Integer, nullable=False)
    est_minutes = Column(Integer, nullable=False)


class UserStudyPlannerProgress(Base):
    __tablename__ = "user_study_planner_progress"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("study_planner_templates.id"), nullable=False)
    day_number = Column(Integer, nullable=False)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "template_id", "day_number", name="uq_planner_progress"),)


class CompilerSession(Base):
    __tablename__ = "compiler_sessions"

    id = Column(Integer, primary_key=True)
    session_token = Column(String(140), unique=True, nullable=False)
    language = Column(String(30), nullable=False)
    code = Column(Text, nullable=False)
    output = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    order_id = Column(String(120), unique=True, nullable=False)
    razorpay_order_id = Column(String(120), nullable=True)
    razorpay_payment_id = Column(String(120), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    status = Column(String(30), default="created")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    certificate_no = Column(String(120), unique=True, nullable=False)
    file_path = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True)
    recipient = Column(String(200), nullable=False)
    subject = Column(String(200), nullable=False)
    status = Column(String(30), nullable=False)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), unique=True, nullable=False)
    slug = Column(String(140), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    discount_percent = Column(Integer, nullable=False)
    max_uses = Column(Integer, default=100)
    used_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SiteSetting(Base):
    __tablename__ = "site_settings"

    id = Column(Integer, primary_key=True)
    key = Column(String(120), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    progress_percent = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    last_lesson = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_enrollment"),)


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    phone = Column(String(30), nullable=True)
    city = Column(String(120), nullable=True)
    bio = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("user_id", name="uq_student_profile"),)


class CourseNote(Base):
    __tablename__ = "course_notes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    lesson_title = Column(String(255), nullable=False)
    note_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(180), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    score = Column(Integer, nullable=False)
    total = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True)
    email = Column(String(120), nullable=False, index=True)
    token = Column(String(180), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
