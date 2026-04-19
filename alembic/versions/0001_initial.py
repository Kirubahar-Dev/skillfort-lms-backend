"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-18
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_id", "users", ["id"])

    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=150), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("thumbnail", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("discount_price", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("instructor", sa.String(length=120), nullable=False),
        sa.Column("lessons_count", sa.Integer(), nullable=True),
        sa.Column("quizzes_count", sa.Integer(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("students_count", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_courses_id", "courses", ["id"])

    op.create_table(
        "contact_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )

    op.create_table(
        "interview_domains",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(length=120), nullable=True),
        sa.Column("color_hex", sa.String(length=10), nullable=True),
        sa.Column("order", sa.Integer(), nullable=True),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "interview_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("domain_id", sa.Integer(), sa.ForeignKey("interview_domains.id"), nullable=True),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("hint", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("boilerplate_py", sa.Text(), nullable=True),
        sa.Column("boilerplate_js", sa.Text(), nullable=True),
        sa.Column("boilerplate_java", sa.Text(), nullable=True),
        sa.Column("boilerplate_cpp", sa.Text(), nullable=True),
        sa.Column("time_complexity", sa.String(length=60), nullable=True),
        sa.Column("space_complexity", sa.String(length=60), nullable=True),
        sa.Column("views", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("meta_title", sa.String(length=255), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.UniqueConstraint("slug", name="uq_interview_questions_slug"),
    )

    op.create_table("question_tags", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(length=80), nullable=False), sa.Column("slug", sa.String(length=100), nullable=False), sa.UniqueConstraint("slug"))
    op.create_table("question_tag_map", sa.Column("question_id", sa.Integer(), sa.ForeignKey("interview_questions.id"), primary_key=True), sa.Column("tag_id", sa.Integer(), sa.ForeignKey("question_tags.id"), primary_key=True))
    op.create_table("question_companies", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(length=120), nullable=False), sa.Column("slug", sa.String(length=120), nullable=False), sa.Column("logo_url", sa.String(length=500), nullable=True), sa.Column("interview_process", sa.Text(), nullable=True), sa.UniqueConstraint("slug"))
    op.create_table("question_company_map", sa.Column("question_id", sa.Integer(), sa.ForeignKey("interview_questions.id"), primary_key=True), sa.Column("company_id", sa.Integer(), sa.ForeignKey("question_companies.id"), primary_key=True))
    op.create_table("question_test_cases", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("question_id", sa.Integer(), sa.ForeignKey("interview_questions.id"), nullable=False), sa.Column("input", sa.Text(), nullable=False), sa.Column("expected_output", sa.Text(), nullable=False), sa.Column("is_hidden", sa.Boolean(), nullable=True))
    op.create_table("question_relations", sa.Column("question_id", sa.Integer(), sa.ForeignKey("interview_questions.id"), primary_key=True), sa.Column("related_question_id", sa.Integer(), sa.ForeignKey("interview_questions.id"), primary_key=True))

    op.create_table(
        "interview_topics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("domain_id", sa.Integer(), sa.ForeignKey("interview_domains.id"), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cheat_sheet", sa.Text(), nullable=True),
        sa.Column("study_resources_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.UniqueConstraint("slug"),
    )

    op.create_table("user_bookmarks", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("question_id", sa.Integer(), sa.ForeignKey("interview_questions.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True), sa.UniqueConstraint("user_id", "question_id", name="uq_user_bookmark"))
    op.create_table("mock_interviews", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("domain", sa.String(length=50), nullable=False), sa.Column("difficulty", sa.String(length=20), nullable=False), sa.Column("total_q", sa.Integer(), nullable=False), sa.Column("score", sa.Integer(), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))
    op.create_table("mock_interview_answers", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("mock_id", sa.Integer(), sa.ForeignKey("mock_interviews.id"), nullable=False), sa.Column("question_id", sa.Integer(), sa.ForeignKey("interview_questions.id"), nullable=False), sa.Column("user_answer", sa.Text(), nullable=True), sa.Column("is_correct", sa.Boolean(), nullable=True))
    op.create_table("study_planner_templates", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(length=120), nullable=False), sa.Column("duration_days", sa.Integer(), nullable=False), sa.Column("description", sa.Text(), nullable=True))
    op.create_table("study_planner_days", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("template_id", sa.Integer(), sa.ForeignKey("study_planner_templates.id"), nullable=False), sa.Column("day_number", sa.Integer(), nullable=False), sa.Column("topic_slug", sa.String(length=140), nullable=False), sa.Column("question_count", sa.Integer(), nullable=False), sa.Column("est_minutes", sa.Integer(), nullable=False))
    op.create_table("user_study_planner_progress", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("template_id", sa.Integer(), sa.ForeignKey("study_planner_templates.id"), nullable=False), sa.Column("day_number", sa.Integer(), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True), sa.UniqueConstraint("user_id", "template_id", "day_number", name="uq_planner_progress"))
    op.create_table("compiler_sessions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("session_token", sa.String(length=140), nullable=False), sa.Column("language", sa.String(length=30), nullable=False), sa.Column("code", sa.Text(), nullable=False), sa.Column("output", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True), sa.UniqueConstraint("session_token"))
    op.create_table("orders", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("order_id", sa.String(length=120), nullable=False), sa.Column("razorpay_order_id", sa.String(length=120), nullable=True), sa.Column("razorpay_payment_id", sa.String(length=120), nullable=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False), sa.Column("amount", sa.Integer(), nullable=False), sa.Column("status", sa.String(length=30), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True), sa.UniqueConstraint("order_id"))
    op.create_table("certificates", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False), sa.Column("certificate_no", sa.String(length=120), nullable=False), sa.Column("file_path", sa.String(length=500), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True), sa.UniqueConstraint("certificate_no"))
    op.create_table("email_logs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("recipient", sa.String(length=200), nullable=False), sa.Column("subject", sa.String(length=200), nullable=False), sa.Column("status", sa.String(length=30), nullable=False), sa.Column("error", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))


def downgrade() -> None:
    for table in [
        "email_logs",
        "certificates",
        "orders",
        "compiler_sessions",
        "user_study_planner_progress",
        "study_planner_days",
        "study_planner_templates",
        "mock_interview_answers",
        "mock_interviews",
        "user_bookmarks",
        "interview_topics",
        "question_relations",
        "question_test_cases",
        "question_company_map",
        "question_companies",
        "question_tag_map",
        "question_tags",
        "interview_questions",
        "interview_domains",
        "contact_messages",
        "courses",
        "users",
    ]:
        op.drop_table(table)
