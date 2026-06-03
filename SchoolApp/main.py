from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from models import (
    CreateStudentRequest, UpdateStudentRequest,
    CreateTeacherRequest, UpdateTeacherRequest,
    CreateCourseRequest, UpdateCourseRequest,
    CreateModuleRequest, CreateLessonRequest, CreateHomeworkRequest,
    EnrollRequest, AssignTeacherRequest,
    AssignHomeworkRequest, GradeHomeworkRequest,
)
from repository import SchoolRepository
from services import SchoolService
from seed import seed as run_seed
import unicodedata
import re

repo = SchoolRepository()
svc = SchoolService(repo)


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_seed(repo)          # заполнить тестовыми данными если БД пустая
    yield
    repo.save()


app = FastAPI(title="Online School Management System v3", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse("static/index.html")


# ══════════════════════════════════════════════════════════════════════════════
# Students
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/students")
def list_students():
    return svc.list_students()

@app.post("/api/students", status_code=201)
def create_student(req: CreateStudentRequest):
    return svc.create_student(req)

@app.patch("/api/students/{sid}")
def update_student(sid: str, req: UpdateStudentRequest):
    return svc.update_student(sid, req)

@app.delete("/api/students/{sid}")
def delete_student(sid: str):
    return svc.delete_student(sid)

@app.get("/api/students/{sid}/card")
def student_card(sid: str):
    return svc.get_student_card(sid)

@app.get("/api/students/{sid}/stats")
def student_stats(sid: str):
    return svc.get_student_stats_visual(sid)

@app.get("/api/students/{sid}/submissions")
def student_submissions(sid: str, course_id: str | None = Query(default=None)):
    if course_id:
        return svc.get_submissions_for_student_course(sid, course_id)
    from repository import SchoolRepository
    return repo.get_submissions_for_student(sid)


# ══════════════════════════════════════════════════════════════════════════════
# Teachers
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/teachers")
def list_teachers():
    return svc.list_teachers()

@app.post("/api/teachers", status_code=201)
def create_teacher(req: CreateTeacherRequest):
    return svc.create_teacher(req)

@app.patch("/api/teachers/{tid}")
def update_teacher(tid: str, req: UpdateTeacherRequest):
    return svc.update_teacher(tid, req)

@app.delete("/api/teachers/{tid}")
def delete_teacher(tid: str):
    return svc.delete_teacher(tid)

@app.get("/api/teachers/{tid}/report")
def teacher_report(tid: str):
    return svc.get_teacher_report(tid)


# ══════════════════════════════════════════════════════════════════════════════
# Courses
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/courses")
def list_courses():
    return svc.list_course_cards()

@app.post("/api/courses", status_code=201)
def create_course(req: CreateCourseRequest):
    return svc.create_course(req)

@app.patch("/api/courses/{cid}")
def update_course(cid: str, req: UpdateCourseRequest):
    return svc.update_course(cid, req)

@app.get("/api/courses/{cid}/card")
def course_card(cid: str):
    return svc.get_course_card(cid)

@app.post("/api/courses/{cid}/complete")
def complete_course(cid: str):
    return svc.complete_course(cid)

# ── Modules ───────────────────────────────────────────────────────────────────

@app.post("/api/courses/{cid}/modules", status_code=201)
def add_module(cid: str, req: CreateModuleRequest):
    return svc.add_module(cid, req)

# ── Lessons ───────────────────────────────────────────────────────────────────

@app.post("/api/courses/{cid}/modules/{mid}/lessons", status_code=201)
def add_lesson(cid: str, mid: str, req: CreateLessonRequest):
    return svc.add_lesson(cid, mid, req)

# ── Homeworks ─────────────────────────────────────────────────────────────────

@app.post("/api/courses/{cid}/modules/{mid}/lessons/{lid}/homeworks", status_code=201)
def add_homework(cid: str, mid: str, lid: str, req: CreateHomeworkRequest):
    return svc.add_homework(cid, mid, lid, req)

@app.get("/api/courses/{cid}/submissions")
def course_submissions(cid: str):
    return svc.get_submissions_for_course(cid)


# ══════════════════════════════════════════════════════════════════════════════
# Actions
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/enroll")
def enroll(req: EnrollRequest):
    return svc.enroll_student(req.student_id, req.course_id)

@app.post("/api/assign-teacher")
def assign_teacher(req: AssignTeacherRequest):
    return svc.assign_teacher(req.teacher_id, req.course_id)

@app.post("/api/homework/assign")
def assign_homework(req: AssignHomeworkRequest):
    return svc.assign_homework(req)

@app.post("/api/homework/grade")
def grade_homework(req: GradeHomeworkRequest):
    return svc.grade_homework(req)


# ══════════════════════════════════════════════════════════════════════════════
# Analytics
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/analytics")
def analytics():
    return svc.get_analytics()


# ══════════════════════════════════════════════════════════════════════════════
# CSV Export
# ══════════════════════════════════════════════════════════════════════════════

def _safe_filename(name: str) -> str:
    """Убирает кириллицу и спецсимволы из имени файла."""
    # транслитерация через unicodedata не работает напрямую,
    # просто оставляем только ASCII
    ascii_name = name.encode('ascii', errors='ignore').decode()
    safe = re.sub(r'[^\w\-.]', '_', ascii_name)
    return safe or "export"

def _csv_response(content: str, filename: str) -> Response:
    safe = _safe_filename(filename)
    return Response(
        content=content.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=\"{safe}\"",
            "Content-Type": "text/csv; charset=utf-8",
        },
    )

@app.get("/api/export/student/{sid}")
def export_student(sid: str):
    csv_data = svc.export_student_csv(sid)
    return _csv_response(csv_data, f"student_{sid}.csv")

@app.get("/api/export/teacher/{tid}")
def export_teacher(tid: str):
    csv_data = svc.export_teacher_csv(tid)
    return _csv_response(csv_data, f"teacher_{tid}.csv")

@app.get("/api/export/course/{cid}")
def export_course(cid: str):
    csv_data = svc.export_course_csv(cid)
    return _csv_response(csv_data, f"course_{cid}.csv")

@app.post("/api/seed")
def force_seed():
    from seed import seed as run_seed
    # Временно сбрасываем флаг
    repo._db.students.clear()
    repo._db.teachers.clear()
    repo._db.courses.clear()
    repo._db.submissions.clear()
    run_seed(repo)
    return {"status": "ok"}