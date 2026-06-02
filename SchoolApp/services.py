from fastapi import HTTPException
from models import (
    Student, Teacher, Course, CourseHistory,
    CreateStudentRequest, UpdateStudentRequest,
    CreateTeacherRequest, UpdateTeacherRequest,
    CreateCourseRequest, UpdateCourseRequest,
    StudentCard, CourseCard,
)
from repository import SchoolRepository


MIN_GRADES_FOR_FINAL = 3  # менее 3 оценок → Н/А


def _avg(grades: list[int]) -> float | None:
    """Возвращает средний балл или None если оценок < MIN_GRADES_FOR_FINAL."""
    if len(grades) < MIN_GRADES_FOR_FINAL:
        return None
    return round(sum(grades) / len(grades), 2)


def _avg_display(grades: list[int]) -> float:
    """Для отображения текущих оценок — всегда число (0.0 если пусто)."""
    return round(sum(grades) / len(grades), 2) if grades else 0.0


class SchoolService:
    def __init__(self, repo: SchoolRepository):
        self.repo = repo

    # ── Create ───────────────────────────────────────────────────────────────

    def create_student(self, req: CreateStudentRequest) -> Student:
        student = Student(name=req.name, email=req.email)
        return self.repo.add_student(student)

    def create_teacher(self, req: CreateTeacherRequest) -> Teacher:
        teacher = Teacher(name=req.name, specialization=req.specialization)
        return self.repo.add_teacher(teacher)

    def create_course(self, req: CreateCourseRequest) -> Course:
        course = Course(title=req.title, topic=req.topic)
        return self.repo.add_course(course)

    # ── Update ───────────────────────────────────────────────────────────────

    def update_student(self, student_id: str, req: UpdateStudentRequest) -> Student:
        student = self._require_student(student_id)
        if req.name is not None:
            student.name = req.name
        if req.email is not None:
            student.email = req.email
        self.repo.update_student(student)
        return student

    def update_teacher(self, teacher_id: str, req: UpdateTeacherRequest) -> Teacher:
        teacher = self._require_teacher(teacher_id)
        if req.name is not None:
            teacher.name = req.name
        if req.specialization is not None:
            teacher.specialization = req.specialization
        if req.status is not None:
            if req.status not in ("active", "vacation"):
                raise HTTPException(400, "Статус должен быть 'active' или 'vacation'.")
            teacher.status = req.status
        self.repo.update_teacher(teacher)
        return teacher

    def update_course(self, course_id: str, req: UpdateCourseRequest) -> Course:
        course = self._require_course(course_id)
        if req.title is not None:
            course.title = req.title
        if req.topic is not None:
            course.topic = req.topic
        self.repo.update_course(course)
        return course

    # ── Delete ───────────────────────────────────────────────────────────────

    def delete_teacher(self, teacher_id: str) -> dict:
        self._require_teacher(teacher_id)
        # Проверка: назначен ли на активный курс
        for course in self.repo.get_all_courses():
            if course.status == "active" and course.teacher_id == teacher_id:
                raise HTTPException(
                    400,
                    f"Нельзя удалить: преподаватель назначен на активный курс «{course.title}»."
                )
        self.repo.delete_teacher(teacher_id)
        return {"deleted": teacher_id}

    def delete_student(self, student_id: str) -> dict:
        self._require_student(student_id)
        self.repo.delete_student(student_id)
        return {"deleted": student_id}

    # ── Enrollment ───────────────────────────────────────────────────────────

    def enroll_student(self, student_id: str, course_id: str) -> Course:
        self._require_student(student_id)
        course = self._require_course(course_id)

        if course.status != "active":
            raise HTTPException(400, "Нельзя зачислить: курс не активен.")
        if student_id in course.enrolled_student_ids:
            raise HTTPException(400, "Студент уже зачислен на этот курс.")

        course.enrolled_student_ids.append(student_id)
        course.grades[student_id] = []
        self.repo.update_course(course)
        return course

    # ── Assign teacher ───────────────────────────────────────────────────────

    def assign_teacher(self, teacher_id: str, course_id: str) -> Course:
        teacher = self._require_teacher(teacher_id)
        course = self._require_course(course_id)

        if teacher.status == "vacation":
            raise HTTPException(400, "Нельзя назначить: преподаватель в отпуске.")

        course.teacher_id = teacher_id
        self.repo.update_course(course)
        return course

    # ── Grade ────────────────────────────────────────────────────────────────

    def add_grade(self, student_id: str, course_id: str, grade: int) -> Course:
        self._require_student(student_id)
        course = self._require_course(course_id)

        if course.status != "active":
            raise HTTPException(400, "Нельзя выставить оценку: курс не активен.")
        if student_id not in course.enrolled_student_ids:
            raise HTTPException(400, "Студент не зачислен на этот курс.")

        course.grades.setdefault(student_id, []).append(grade)
        self.repo.update_course(course)
        return course

    # ── Complete course ──────────────────────────────────────────────────────

    def complete_course(self, course_id: str) -> Course:
        course = self._require_course(course_id)

        if course.status == "completed":
            raise HTTPException(400, "Курс уже завершён.")

        for sid in course.enrolled_student_ids:
            student = self.repo.get_student(sid)
            if student:
                grades = course.grades.get(sid, [])
                final = _avg(grades)  # None если < 3 оценок
                student.course_history.append(
                    CourseHistory(
                        course_id=course.id,
                        course_title=course.title,
                        final_grade=final,
                    )
                )
                self.repo.update_student(student)

        course.status = "completed"
        course.grades = {}
        course.enrolled_student_ids = []
        self.repo.update_course(course)
        return course

    # ── Rich cards ───────────────────────────────────────────────────────────

    def get_student_card(self, student_id: str) -> StudentCard:
        student = self._require_student(student_id)

        active_courses = []
        for course in self.repo.get_all_courses():
            if course.status == "active" and student_id in course.enrolled_student_ids:
                g = course.grades.get(student_id, [])
                active_courses.append({
                    "course_id": course.id,
                    "title": course.title,
                    "current_grades": g,
                    "avg": _avg_display(g),
                })

        return StudentCard(
            id=student.id,
            name=student.name,
            email=student.email,
            active_courses=active_courses,
            course_history=student.course_history,
        )

    def get_course_card(self, course_id: str) -> CourseCard:
        course = self._require_course(course_id)

        teacher_info = None
        if course.teacher_id:
            t = self.repo.get_teacher(course.teacher_id)
            if t:
                teacher_info = {
                    "id": t.id,
                    "name": t.name,
                    "specialization": t.specialization,
                    "status": t.status,
                }

        enrolled = []
        for sid in course.enrolled_student_ids:
            s = self.repo.get_student(sid)
            if s:
                g = course.grades.get(sid, [])
                enrolled.append({
                    "id": s.id,
                    "name": s.name,
                    "grades": g,
                    "avg": _avg_display(g),
                })

        return CourseCard(
            id=course.id,
            title=course.title,
            topic=course.topic,
            status=course.status,
            teacher=teacher_info,
            enrolled_students=enrolled,
        )

    # ── Lists ─────────────────────────────────────────────────────────────────

    def list_students(self) -> list[Student]:
        return self.repo.get_all_students()

    def list_teachers(self) -> list[Teacher]:
        return self.repo.get_all_teachers()

    def list_course_cards(self) -> list[CourseCard]:
        return [self.get_course_card(c.id) for c in self.repo.get_all_courses()]

    def get_analytics(self) -> dict:
        students = self.repo.get_all_students()
        teachers = self.repo.get_all_teachers()
        courses = self.repo.get_all_courses()
        course_cards = self.list_course_cards()

        active = [c for c in courses if c.status == "active"]
        completed = [c for c in courses if c.status == "completed"]

        # Топ-3 по числу студентов
        top3 = sorted(course_cards, key=lambda c: len(c.enrolled_students), reverse=True)[:3]

        # Средний балл по школе (все активные оценки)
        all_grades: list[int] = []
        for c in courses:
            for g_list in c.grades.values():
                all_grades.extend(g_list)
        school_avg = round(sum(all_grades) / len(all_grades), 2) if all_grades else None

        return {
            "total_students": len(students),
            "total_teachers": len(teachers),
            "active_courses": len(active),
            "completed_courses": len(completed),
            "total_enrollments": sum(len(c.enrolled_student_ids) for c in active),
            "school_avg": school_avg,
            "top_courses": [
                {
                    "id": c.id,
                    "title": c.title,
                    "topic": c.topic,
                    "student_count": len(c.enrolled_students),
                    "status": c.status,
                }
                for c in top3
            ],
        }

    # ── Guards ───────────────────────────────────────────────────────────────

    def _require_student(self, sid: str) -> Student:
        s = self.repo.get_student(sid)
        if not s:
            raise HTTPException(404, f"Студент {sid} не найден.")
        return s

    def _require_teacher(self, tid: str) -> Teacher:
        t = self.repo.get_teacher(tid)
        if not t:
            raise HTTPException(404, f"Преподаватель {tid} не найден.")
        return t

    def _require_course(self, cid: str) -> Course:
        c = self.repo.get_course(cid)
        if not c:
            raise HTTPException(404, f"Курс {cid} не найден.")
        return c
