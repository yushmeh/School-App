from __future__ import annotations
import csv
import io
from datetime import date
from fastapi import HTTPException
from models import (
    Student, Teacher, Course, CourseHistory,
    Module, Lesson, Homework, HomeworkSubmission,
    CreateStudentRequest, UpdateStudentRequest,
    CreateTeacherRequest, UpdateTeacherRequest,
    CreateCourseRequest, UpdateCourseRequest,
    CreateModuleRequest, CreateLessonRequest, CreateHomeworkRequest,
    AssignHomeworkRequest, GradeHomeworkRequest,
    StudentCard, CourseCard, TeacherReport,
)
from repository import SchoolRepository

MIN_GRADES_FOR_FINAL = 3


def _safe_avg(values: list[int | float]) -> float | None:
    """Средний балл или None если оценок меньше MIN_GRADES_FOR_FINAL."""
    if len(values) < MIN_GRADES_FOR_FINAL:
        return None
    return round(sum(values) / len(values), 2)


def _avg_or_zero(values: list[int | float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def _bar(ratio: float, width: int = 20) -> str:
    """ASCII прогресс-бар вида [████████░░] 80%."""
    filled = round(ratio * width)
    return f"[{'█' * filled}{'░' * (width - filled)}] {round(ratio * 100)}%"


class SchoolService:
    def __init__(self, repo: SchoolRepository):
        self.repo = repo

    def create_student(self, req: CreateStudentRequest) -> Student:
        return self.repo.add_student(Student(name=req.name, email=req.email))

    def update_student(self, sid: str, req: UpdateStudentRequest) -> Student:
        s = self._req_student(sid)
        if req.name is not None:
            s.name = req.name
        if req.email is not None:
            s.email = req.email
        self.repo.update_student(s)
        return s

    def delete_student(self, sid: str) -> dict:
        self._req_student(sid)
        self.repo.delete_student(sid)
        return {"deleted": sid}

    def list_students(self) -> list[Student]:
        return self.repo.get_all_students()

    def create_teacher(self, req: CreateTeacherRequest) -> Teacher:
        return self.repo.add_teacher(Teacher(name=req.name, specialization=req.specialization))

    def update_teacher(self, tid: str, req: UpdateTeacherRequest) -> Teacher:
        t = self._req_teacher(tid)
        if req.name is not None:
            t.name = req.name
        if req.specialization is not None:
            t.specialization = req.specialization
        if req.status is not None:
            if req.status not in ("active", "vacation"):
                raise HTTPException(400, "Статус должен быть 'active' или 'vacation'.")
            t.status = req.status
        self.repo.update_teacher(t)
        return t

    def delete_teacher(self, tid: str) -> dict:
        """Запрещает удаление если преподаватель ведёт активный курс."""
        self._req_teacher(tid)
        for c in self.repo.get_all_courses():
            if c.status == "active" and c.teacher_id == tid:
                raise HTTPException(400, f"Нельзя удалить: преподаватель ведёт активный курс «{c.title}».")
        self.repo.delete_teacher(tid)
        return {"deleted": tid}

    def list_teachers(self) -> list[Teacher]:
        return self.repo.get_all_teachers()

    def create_course(self, req: CreateCourseRequest) -> Course:
        return self.repo.add_course(Course(title=req.title, topic=req.topic))

    def update_course(self, cid: str, req: UpdateCourseRequest) -> Course:
        c = self._req_course(cid)
        if req.title is not None:
            c.title = req.title
        if req.topic is not None:
            c.topic = req.topic
        self.repo.update_course(c)
        return c

    def list_course_cards(self) -> list[CourseCard]:
        return [self._build_course_card(c) for c in self.repo.get_all_courses()]

    def get_course_card(self, cid: str) -> CourseCard:
        return self._build_course_card(self._req_course(cid))

    def add_module(self, course_id: str, req: CreateModuleRequest) -> Course:
        c = self._req_course(course_id)
        c.modules.append(Module(title=req.title, description=req.description, order=req.order))
        self.repo.update_course(c)
        return c

    def add_lesson(self, course_id: str, module_id: str, req: CreateLessonRequest) -> Course:
        c = self._req_course(course_id)
        m = self._req_module(c, module_id)
        m.lessons.append(Lesson(title=req.title, description=req.description, order=req.order))
        self.repo.update_course(c)
        return c

    def add_homework(self, course_id: str, module_id: str, lesson_id: str, req: CreateHomeworkRequest) -> Course:
        c = self._req_course(course_id)
        m = self._req_module(c, module_id)
        lesson = self._req_lesson(m, lesson_id)
        lesson.homeworks.append(Homework(title=req.title, description=req.description, max_grade=req.max_grade))
        self.repo.update_course(c)
        return c

    def enroll_student(self, student_id: str, course_id: str) -> Course:
        self._req_student(student_id)
        c = self._req_course(course_id)
        if c.status != "active":
            raise HTTPException(400, "Нельзя зачислить: курс не активен.")
        if student_id in c.enrolled_student_ids:
            raise HTTPException(400, "Студент уже зачислен.")
        c.enrolled_student_ids.append(student_id)
        self.repo.update_course(c)
        return c

    def assign_teacher(self, teacher_id: str, course_id: str) -> Course:
        """Запрещает назначение если преподаватель в отпуске."""
        t = self._req_teacher(teacher_id)
        if t.status == "vacation":
            raise HTTPException(400, "Нельзя назначить: преподаватель в отпуске.")
        c = self._req_course(course_id)
        c.teacher_id = teacher_id
        self.repo.update_course(c)
        return c

    def assign_homework(self, req: AssignHomeworkRequest) -> list[HomeworkSubmission]:
        """Выдаёт ДЗ одному студенту или всем зачисленным. Повторная выдача игнорируется."""
        c = self._req_course(req.course_id)
        m = self._req_module(c, req.module_id)
        lesson = self._req_lesson(m, req.lesson_id)
        hw = next((h for h in lesson.homeworks if h.id == req.homework_id), None)
        if not hw:
            raise HTTPException(404, "Домашнее задание не найдено.")
        targets = [req.student_id] if req.student_id else c.enrolled_student_ids
        created: list[HomeworkSubmission] = []
        for sid in targets:
            already = [
                s for s in self.repo.get_submissions_for_student(sid)
                if s.homework_id == req.homework_id and s.course_id == req.course_id
            ]
            if already:
                continue
            sub = HomeworkSubmission(
                homework_id=req.homework_id,
                lesson_id=req.lesson_id,
                module_id=req.module_id,
                course_id=req.course_id,
                student_id=sid,
            )
            self.repo.add_submission(sub)
            created.append(sub)
        return created

    def grade_homework(self, req: GradeHomeworkRequest) -> HomeworkSubmission:
        sub = self.repo.get_submission(req.submission_id)
        if not sub:
            raise HTTPException(404, "Сдача ДЗ не найдена.")
        self._req_teacher(req.teacher_id)
        sub.grade = req.grade
        sub.graded_by = req.teacher_id
        sub.comment = req.comment
        sub.graded_at = date.today().isoformat()
        self.repo.update_submission(sub)
        return sub

    def get_submissions_for_student_course(self, student_id: str, course_id: str) -> list[HomeworkSubmission]:
        return self.repo.get_submissions_for_course(course_id, student_id)

    def get_submissions_for_course(self, course_id: str) -> list[HomeworkSubmission]:
        return self.repo.get_submissions_for_course(course_id)

    def complete_course(self, course_id: str) -> Course:
        """Завершает курс: итоговый балл = среднее по оценённым ДЗ (Н/А если < 3 оценок)."""
        c = self._req_course(course_id)
        if c.status == "completed":
            raise HTTPException(400, "Курс уже завершён.")
        today = date.today().isoformat()
        for sid in c.enrolled_student_ids:
            student = self.repo.get_student(sid)
            if not student:
                continue
            graded = [s.grade for s in self.repo.get_submissions_for_course(course_id, sid) if s.grade is not None]
            student.course_history.append(CourseHistory(
                course_id=c.id,
                course_title=c.title,
                final_grade=_safe_avg(graded),
                completed_at=today,
            ))
            self.repo.update_student(student)
        c.status = "completed"
        c.end_date = today
        self.repo.update_course(c)
        return c

    def get_student_card(self, student_id: str) -> StudentCard:
        s = self._req_student(student_id)
        active_courses = []
        for c in self.repo.get_all_courses():
            if c.status == "active" and student_id in c.enrolled_student_ids:
                subs = self.repo.get_submissions_for_course(c.id, student_id)
                graded = [x.grade for x in subs if x.grade is not None]
                active_courses.append({
                    "course_id": c.id, "title": c.title,
                    "hw_submitted": len(subs), "hw_graded": len(graded),
                    "avg": _avg_or_zero(graded),
                    "bar": _bar((_avg_or_zero(graded) - 2) / 3 if graded else 0),
                })
        return StudentCard(id=s.id, name=s.name, email=s.email,
                           active_courses=active_courses, course_history=s.course_history)

    def get_student_stats_visual(self, student_id: str) -> dict:
        """Статистика студента с ASCII-визуализацией успеваемости по каждому курсу."""
        s = self._req_student(student_id)
        courses_data = []
        for c in self.repo.get_all_courses():
            if student_id not in c.enrolled_student_ids:
                continue
            subs = self.repo.get_submissions_for_course(c.id, student_id)
            graded = [x.grade for x in subs if x.grade is not None]
            avg = _avg_or_zero(graded)
            ratio = (avg - 2) / 3 if graded else 0.0
            courses_data.append({
                "course_id": c.id, "title": c.title, "status": c.status,
                "hw_total": len(subs), "hw_graded": len(graded),
                "avg": avg, "bar": _bar(ratio, 24), "grades": graded,
            })
        all_grades = [g for cd in courses_data for g in cd["grades"]]
        overall_avg = _avg_or_zero(all_grades)
        overall_ratio = (overall_avg - 2) / 3 if all_grades else 0.0
        history_data = []
        for h in s.course_history:
            bar = _bar((h.final_grade - 2) / 3, 24) if h.final_grade is not None else "[Н/А]"
            history_data.append({
                "title": h.course_title, "final_grade": h.final_grade,
                "completed_at": h.completed_at, "bar": bar,
            })
        return {
            "student": {"id": s.id, "name": s.name, "email": s.email},
            "overall_avg": overall_avg,
            "overall_bar": _bar(overall_ratio, 30),
            "active_courses": courses_data,
            "history": history_data,
        }

    def get_teacher_report(self, teacher_id: str) -> TeacherReport:
        """Аналитика по преподавателю: курсы, средняя успеваемость, количество студентов."""
        t = self._req_teacher(teacher_id)
        all_courses = self.repo.get_all_courses()
        active = [c for c in all_courses if c.teacher_id == teacher_id and c.status == "active"]
        completed = [c for c in all_courses if c.teacher_id == teacher_id and c.status == "completed"]
        all_grades: list[int] = []
        student_ids: set[str] = set()
        graded_count = 0
        for c in active + completed:
            for sub in self.repo.get_submissions_for_course(c.id):
                student_ids.add(sub.student_id)
                if sub.grade is not None:
                    all_grades.append(sub.grade)
                    graded_count += 1
        return TeacherReport(
            teacher_id=t.id, teacher_name=t.name,
            specialization=t.specialization, status=t.status,
            active_courses_count=len(active),
            active_courses=[{"id": c.id, "title": c.title, "topic": c.topic,
                              "students": len(c.enrolled_student_ids), "start_date": c.start_date}
                             for c in active],
            completed_courses=[{"id": c.id, "title": c.title, "topic": c.topic,
                                 "start_date": c.start_date, "end_date": c.end_date}
                                for c in completed],
            avg_student_performance=_avg_or_zero(all_grades) if all_grades else None,
            total_students=len(student_ids),
            total_graded_submissions=graded_count,
        )

    def get_analytics(self) -> dict:
        students = self.repo.get_all_students()
        teachers = self.repo.get_all_teachers()
        courses = self.repo.get_all_courses()
        active = [c for c in courses if c.status == "active"]
        completed = [c for c in courses if c.status == "completed"]
        all_subs = self.repo.get_all_submissions()
        all_grades = [s.grade for s in all_subs if s.grade is not None]
        school_avg = _avg_or_zero(all_grades) if all_grades else None
        cards = self.list_course_cards()
        top3 = sorted(cards, key=lambda c: len(c.enrolled_students), reverse=True)[:3]
        return {
            "total_students": len(students),
            "total_teachers": len(teachers),
            "active_courses": len(active),
            "completed_courses": len(completed),
            "total_enrollments": sum(len(c.enrolled_student_ids) for c in active),
            "total_submissions": len(all_subs),
            "graded_submissions": len(all_grades),
            "school_avg": school_avg,
            "school_avg_bar": _bar((school_avg - 2) / 3 if school_avg else 0, 20),
            "top_courses": [{"id": c.id, "title": c.title,
                              "student_count": len(c.enrolled_students), "status": c.status}
                             for c in top3],
        }

    def export_student_csv(self, student_id: str) -> str:
        """CSV-отчёт: активные курсы, история, все оценки за ДЗ."""
        s = self._req_student(student_id)
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["Студент", s.name])
        w.writerow(["Email", s.email])
        w.writerow([])
        w.writerow(["=== АКТИВНЫЕ КУРСЫ ==="])
        w.writerow(["Курс", "ДЗ выдано", "ДЗ оценено", "Средний балл", "Шкала"])
        for c in self.repo.get_all_courses():
            if c.status == "active" and student_id in c.enrolled_student_ids:
                subs = self.repo.get_submissions_for_course(c.id, student_id)
                graded = [x.grade for x in subs if x.grade is not None]
                avg = _avg_or_zero(graded)
                ratio = (avg - 2) / 3 if graded else 0.0
                w.writerow([c.title, len(subs), len(graded), avg, _bar(ratio)])
        w.writerow([])
        w.writerow(["=== ИСТОРИЯ КУРСОВ ==="])
        w.writerow(["Курс", "Итоговый балл", "Дата завершения"])
        for h in s.course_history:
            w.writerow([h.course_title, h.final_grade if h.final_grade is not None else "Н/А", h.completed_at or ""])
        w.writerow([])
        w.writerow(["=== ВСЕ ОЦЕНКИ ЗА ДЗ ==="])
        w.writerow(["Курс", "Модуль", "Урок", "ДЗ", "Оценка", "Комментарий", "Дата"])
        for sub in self.repo.get_submissions_for_student(student_id):
            course = self.repo.get_course(sub.course_id)
            if not course:
                continue
            hw_title, lesson_title, module_title = "–", "–", "–"
            for mod in course.modules:
                if mod.id == sub.module_id:
                    module_title = mod.title
                    for les in mod.lessons:
                        if les.id == sub.lesson_id:
                            lesson_title = les.title
                            for hw in les.homeworks:
                                if hw.id == sub.homework_id:
                                    hw_title = hw.title
            w.writerow([course.title, module_title, lesson_title, hw_title,
                        sub.grade if sub.grade is not None else "Не оценено",
                        sub.comment, sub.graded_at or ""])
        return out.getvalue()

    def export_teacher_csv(self, teacher_id: str) -> str:
        """CSV-отчёт: метрики преподавателя, активные и завершённые курсы."""
        report = self.get_teacher_report(teacher_id)
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["Преподаватель", report.teacher_name])
        w.writerow(["Специализация", report.specialization])
        w.writerow(["Статус", "Активен" if report.status == "active" else "В отпуске"])
        w.writerow(["Активных курсов", report.active_courses_count])
        w.writerow(["Всего студентов", report.total_students])
        w.writerow(["Оценено ДЗ", report.total_graded_submissions])
        w.writerow(["Средняя успеваемость", report.avg_student_performance or "Н/А"])
        w.writerow([])
        w.writerow(["=== АКТИВНЫЕ КУРСЫ ==="])
        w.writerow(["Название", "Тема", "Студентов", "Дата начала"])
        for c in report.active_courses:
            w.writerow([c["title"], c["topic"], c["students"], c["start_date"]])
        w.writerow([])
        w.writerow(["=== ЗАВЕРШЁННЫЕ КУРСЫ ==="])
        w.writerow(["Название", "Тема", "Дата начала", "Дата окончания"])
        for c in report.completed_courses:
            w.writerow([c["title"], c["topic"], c["start_date"], c.get("end_date", "–")])
        return out.getvalue()

    def export_course_csv(self, course_id: str) -> str:
        """CSV-отчёт: структура курса и успеваемость студентов."""
        c = self._req_course(course_id)
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["Курс", c.title])
        w.writerow(["Тема", c.topic])
        w.writerow(["Статус", c.status])
        teacher = self.repo.get_teacher(c.teacher_id) if c.teacher_id else None
        w.writerow(["Преподаватель", teacher.name if teacher else "Не назначен"])
        w.writerow([])
        w.writerow(["=== СТРУКТУРА КУРСА ==="])
        w.writerow(["Модуль", "Урок", "ДЗ"])
        for mod in c.modules:
            for les in mod.lessons:
                if les.homeworks:
                    for hw in les.homeworks:
                        w.writerow([mod.title, les.title, hw.title])
                else:
                    w.writerow([mod.title, les.title, "–"])
        w.writerow([])
        w.writerow(["=== УСПЕВАЕМОСТЬ СТУДЕНТОВ ==="])
        w.writerow(["Студент", "Email", "ДЗ выдано", "ДЗ оценено", "Средний балл", "Шкала"])
        for sid in c.enrolled_student_ids:
            stu = self.repo.get_student(sid)
            if not stu:
                continue
            subs = self.repo.get_submissions_for_course(course_id, sid)
            graded = [s.grade for s in subs if s.grade is not None]
            avg = _avg_or_zero(graded)
            ratio = (avg - 2) / 3 if graded else 0.0
            w.writerow([stu.name, stu.email, len(subs), len(graded), avg, _bar(ratio)])
        return out.getvalue()

    def _build_course_card(self, c: Course) -> CourseCard:
        teacher_info = None
        if c.teacher_id:
            t = self.repo.get_teacher(c.teacher_id)
            if t:
                teacher_info = {"id": t.id, "name": t.name,
                                "specialization": t.specialization, "status": t.status}
        enrolled = []
        for sid in c.enrolled_student_ids:
            s = self.repo.get_student(sid)
            if not s:
                continue
            subs = self.repo.get_submissions_for_course(c.id, sid)
            graded = [x.grade for x in subs if x.grade is not None]
            avg = _avg_or_zero(graded)
            ratio = (avg - 2) / 3 if graded else 0.0
            enrolled.append({"id": s.id, "name": s.name,
                              "hw_submitted": len(subs), "hw_graded": len(graded),
                              "avg": avg, "bar": _bar(ratio)})
        total_lessons = sum(len(m.lessons) for m in c.modules)
        total_hw = sum(len(les.homeworks) for m in c.modules for les in m.lessons)
        return CourseCard(
            id=c.id, title=c.title, topic=c.topic,
            status=c.status, start_date=c.start_date, end_date=c.end_date,
            teacher=teacher_info, enrolled_students=enrolled,
            modules=c.modules, total_lessons=total_lessons, total_homeworks=total_hw,
        )

    def _req_student(self, sid: str) -> Student:
        s = self.repo.get_student(sid)
        if not s:
            raise HTTPException(404, f"Студент {sid} не найден.")
        return s

    def _req_teacher(self, tid: str) -> Teacher:
        t = self.repo.get_teacher(tid)
        if not t:
            raise HTTPException(404, f"Преподаватель {tid} не найден.")
        return t

    def _req_course(self, cid: str) -> Course:
        c = self.repo.get_course(cid)
        if not c:
            raise HTTPException(404, f"Курс {cid} не найден.")
        return c

    @staticmethod
    def _req_module(course: Course, mid: str) -> Module:
        m = next((x for x in course.modules if x.id == mid), None)
        if not m:
            raise HTTPException(404, f"Модуль {mid} не найден в курсе.")
        return m

    @staticmethod
    def _req_lesson(module: Module, lid: str) -> Lesson:
        lesson = next((x for x in module.lessons if x.id == lid), None)
        if not lesson:
            raise HTTPException(404, f"Урок {lid} не найден в модуле.")
        return lesson