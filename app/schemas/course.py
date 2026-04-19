from pydantic import BaseModel


class CourseBase(BaseModel):
    slug: str
    title: str
    thumbnail: str | None = None
    description: str | None = None
    price: int
    discountPrice: int
    category: str
    instructor: str
    lessonsCount: int = 0
    quizzesCount: int = 0
    durationMinutes: int = 0
    studentsCount: int = 0
    rating: float = 0
    status: str = "draft"


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    title: str | None = None
    thumbnail: str | None = None
    description: str | None = None
    price: int | None = None
    discountPrice: int | None = None
    category: str | None = None
    instructor: str | None = None
    lessonsCount: int | None = None
    quizzesCount: int | None = None
    durationMinutes: int | None = None
    studentsCount: int | None = None
    rating: float | None = None
    status: str | None = None


class CourseOut(CourseBase):
    id: int


class CourseListResponse(BaseModel):
    items: list[CourseOut]
    total: int


class CourseLessonPayload(BaseModel):
    section_title: str
    lesson_title: str
    duration_minutes: int = 15
    video_url: str | None = None
    order_index: int = 0
    is_preview: bool = False


class CourseLessonOut(CourseLessonPayload):
    id: int
    course_id: int
