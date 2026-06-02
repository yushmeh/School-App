from pydantic import BaseModel, Field, field_validator
from typing import Optional
import uuid
import re


def gen_id() -> str:
    return str(uuid.uuid4())


EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')


# --- Core Entities ---

class CourseHistory(BaseModel):
    course_id: str
    course_title: str
    final_grade: Optional[float] = None  # None → "Н/А" (менее 3 оценок)


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
    status: str = "active"  # "active" | "vacation"


class Course(BaseModel):
    id: str = Field(default_factory=gen_id)
    title: str
    topic: str
    status: str = "active"  # "active" | "completed"
    enrolled_student_ids: list[str] = []
    teacher_id: Optional[str] = None
    grades: dict[str, list[int]] = {}  # {student_id: [grade, ...]}


# --- Database Schema ---

class SchoolDB(BaseModel):
    students: dict[str, Student] = {}
    teachers: dict[str, Teacher] = {}
    courses: dict[str, Course] = {}


# --- Request / Response DTOs ---

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


class EnrollRequest(BaseModel):
    student_id: str
    course_id: str


class AssignTeacherRequest(BaseModel):
    teacher_id: str
    course_id: str


class GradeRequest(BaseModel):
    student_id: str
    course_id: str
    grade: int = Field(ge=2, le=5)  # русская шкала 2–5


# --- Rich Response DTOs ---

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
    teacher: Optional[dict]
    enrolled_students: list[dict]
