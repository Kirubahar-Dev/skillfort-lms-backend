from app.routers.auth import router as auth_router
from app.routers.courses import router as courses_router
from app.routers.contact import router as contact_router
from app.routers.interview import router as interview_router
from app.routers.commerce import router as commerce_router
from app.routers.admin import router as admin_router
from app.routers.student import router as student_router

__all__ = ["auth_router", "courses_router", "contact_router", "interview_router", "commerce_router", "admin_router", "student_router"]
