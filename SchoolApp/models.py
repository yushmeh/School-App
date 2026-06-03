from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date
import uuid
import re

EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')


def gen_id() -> str:
    return str(uuid.uuid4())


# ══════════════════════════════════════════════════════════════════════════════
# Вложенные сущности курса
# ══════════════════════════════════════════════════════════════════════════════

class Homework(BaseModel):
    """Домашнее задание, привязанное к уроку."""
    id: str = Field(default_factory=gen_id)
    title: str
    description: str = ""
    max_grade: int = 5          # максимальный балл (по умолчанию 5)


class Lesson(BaseModel):
    """Урок внутри модуля."""
    id: str = Field(default_factory=gen_id)
    title: str
    description: str = ""
    order: int = 1
    homeworks: list[Homework] = []


class Module(BaseModel):
    """Модуль внутри курса."""
    id: str = Field(default_factory=gen_id)
    title: str
    description: str = ""
    order: int = 1
    lessons: list[Lesson] = []


# ══════════════════════════════════════════════════════════════════════════════
# Оценки за ДЗ
# ══════════════════════════════════════════════════════════════════════════════

class HomeworkSubmission(BaseModel):
    """Запись о выданном/сданном ДЗ студенту."""
    id: str = Field(default_factory=gen_id)
    homework_id: str
    lesson_id: str
    module_id: str
    course_id: str
    student_id: str
    grade: Optional[int] = None          # None = ещё не оценено
    graded_by: Optional[str] = None      # teacher_id
    comment: str = ""
    assigned_at: str = Field(default_factory=lambda: date.today().isoformat())
    graded_at: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# Основные сущности
# ══════════════════════════════════════════════════════════════════════════════

class CourseHistory(BaseModel):
    course_id: str
    course_title: str
    final_grade: Optional[float] = None  # None → "Н/А"
    completed_at: Optional[str] = None


class Student(BaseModel):
    id: str = Field(default_factory=gen_id)
    name: str
    email: str
    course_history: list[CourseHistory] = []

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not EMAIL_RE.match(v):
            raise ValueError(f"Некорректный email: {v!r}")
        return v.lower()


class Teacher(BaseModel):
    id: str = Field(default_factory=gen_id)
    name: str
    specialization: str
    status: str = "active"   # "active" | "vacation"


class Course(BaseModel):
    id: str = Field(default_factory=gen_id)
    title: str
    topic: str
    status: str = "active"          # "active" | "completed"
    enrolled_student_ids: list[str] = []
    teacher_id: Optional[str] = None
    modules: list[Module] = []
    start_date: str = Field(default_factory=lambda: date.today().isoformat())
    end_date: Optional[str] = None  # устанавливается при complete


# ══════════════════════════════════════════════════════════════════════════════
# База данных
# ══════════════════════════════════════════════════════════════════════════════

class SchoolDB(BaseModel):
    students: dict[str, Student] = {}
    teachers: dict[str, Teacher] = {}
    courses: dict[str, Course] = {}
    submissions: dict[str, HomeworkSubmission] = {}  # id → submission


# ══════════════════════════════════════════════════════════════════════════════
# Request DTOs
# ══════════════════════════════════════════════════════════════════════════════

class CreateStudentRequest(BaseModel):
    name: str
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not EMAIL_RE.match(v):
            raise ValueError(f"Некорректный email: {v!r}")
        return v.lower()


class UpdateStudentRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not EMAIL_RE.match(v):
            raise ValueError(f"Некорректный email: {v!r}")
        return v.lower() if v else v


class CreateTeacherRequest(BaseModel):
    name: str
    specialization: str


class UpdateTeacherRequest(BaseModel):
    name: Optional[str] = None
    specialization: Optional[str] = None
    status: Optional[str] = None


class CreateCourseRequest(BaseModel):
    title: str
    topic: str


class UpdateCourseRequest(BaseModel):
    title: Optional[str] = None
    topic: Optional[str] = None


class CreateModuleRequest(BaseModel):
    title: str
    description: str = ""
    order: int = 1


class CreateLessonRequest(BaseModel):
    title: str
    description: str = ""
    order: int = 1


class CreateHomeworkRequest(BaseModel):
    title: str
    description: str = ""
    max_grade: int = Field(default=5, ge=2, le=5)


class EnrollRequest(BaseModel):
    student_id: str
    course_id: str


class AssignTeacherRequest(BaseModel):
    teacher_id: str
    course_id: str


class AssignHomeworkRequest(BaseModel):
    """Выдать ДЗ студенту (или всем зачисленным)."""
    homework_id: str
    lesson_id: str
    module_id: str
    course_id: str
    student_id: Optional[str] = None    # None = выдать всем студентам курса


class GradeHomeworkRequest(BaseModel):
    """Преподаватель выставляет оценку за ДЗ."""
    submission_id: str
    grade: int = Field(ge=2, le=5)
    teacher_id: str
    comment: str = ""


# ══════════════════════════════════════════════════════════════════════════════
# Response DTOs (богатые карточки для UI)
# ══════════════════════════════════════════════════════════════════════════════

class StudentCard(BaseModel):
    id: str
    name: str
    email: str
    active_courses: list[dict]
    course_history: list[CourseHistory]


class CourseCard(BaseModel):
    id: str
    title: str
    topic: str
    status: str
    start_date: str
    end_date: Optional[str]
    teacher: Optional[dict]
    enrolled_students: list[dict]
    modules: list[Module]
    total_lessons: int
    total_homeworks: int


class TeacherReport(BaseModel):
    teacher_id: str
    teacher_name: str
    specialization: str
    status: str
    active_courses_count: int
    active_courses: list[dict]
    completed_courses: list[dict]
    avg_student_performance: Optional[float]
    total_students: int
    total_graded_submissions: int