from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from models import (
    CreateStudentRequest, UpdateStudentRequest,
    CreateTeacherRequest, UpdateTeacherRequest,
    CreateCourseRequest, UpdateCourseRequest,
    EnrollRequest, AssignTeacherRequest, GradeRequest,
)
from repository import SchoolRepository
from services import SchoolService

repo = SchoolRepository()
svc = SchoolService(repo)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    repo.save()


app = FastAPI(title="Online School Management System", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse("static/index.html")


# ── Students ──────────────────────────────────────────────────────────────────

@app.get("/api/students")
def list_students():
    return svc.list_students()

@app.post("/api/students", status_code=201)
def create_student(req: CreateStudentRequest):
    return svc.create_student(req)

@app.patch("/api/students/{student_id}")
def update_student(student_id: str, req: UpdateStudentRequest):
    return svc.update_student(student_id, req)

@app.delete("/api/students/{student_id}")
def delete_student(student_id: str):
    return svc.delete_student(student_id)

@app.get("/api/students/{student_id}/card")
def student_card(student_id: str):
    return svc.get_student_card(student_id)


# ── Teachers ──────────────────────────────────────────────────────────────────

@app.get("/api/teachers")
def list_teachers():
    return svc.list_teachers()

@app.post("/api/teachers", status_code=201)
def create_teacher(req: CreateTeacherRequest):
    return svc.create_teacher(req)

@app.patch("/api/teachers/{teacher_id}")
def update_teacher(teacher_id: str, req: UpdateTeacherRequest):
    return svc.update_teacher(teacher_id, req)

@app.delete("/api/teachers/{teacher_id}")
def delete_teacher(teacher_id: str):
    return svc.delete_teacher(teacher_id)


# ── Courses ───────────────────────────────────────────────────────────────────

@app.get("/api/courses")
def list_courses():
    return svc.list_course_cards()

@app.post("/api/courses", status_code=201)
def create_course(req: CreateCourseRequest):
    return svc.create_course(req)

@app.patch("/api/courses/{course_id}")
def update_course(course_id: str, req: UpdateCourseRequest):
    return svc.update_course(course_id, req)

@app.get("/api/courses/{course_id}/card")
def course_card(course_id: str):
    return svc.get_course_card(course_id)

@app.post("/api/courses/{course_id}/complete")
def complete_course(course_id: str):
    return svc.complete_course(course_id)


# ── Actions ───────────────────────────────────────────────────────────────────

@app.post("/api/enroll")
def enroll(req: EnrollRequest):
    return svc.enroll_student(req.student_id, req.course_id)

@app.post("/api/assign-teacher")
def assign_teacher(req: AssignTeacherRequest):
    return svc.assign_teacher(req.teacher_id, req.course_id)

@app.post("/api/grade")
def grade(req: GradeRequest):
    return svc.add_grade(req.student_id, req.course_id, req.grade)


# ── Analytics ─────────────────────────────────────────────────────────────────

@app.get("/api/analytics")
def analytics():
    return svc.get_analytics()
