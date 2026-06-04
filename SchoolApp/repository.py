from __future__ import annotations
from pathlib import Path
from models import SchoolDB, Student, Teacher, Course, HomeworkSubmission

DB_PATH = Path(__file__).parent / "school_data.json"


class SchoolRepository:
    def __init__(self):
        self._db: SchoolDB = SchoolDB()
        self._load()

    def _load(self):
        if DB_PATH.exists():
            try:
                self._db = SchoolDB.model_validate_json(
                    DB_PATH.read_text(encoding="utf-8")
                )
            except Exception as exc:
                print(f"[repo] Не удалось загрузить БД, старт с чистого листа: {exc}")

    def save(self):
        DB_PATH.write_text(self._db.model_dump_json(indent=2), encoding="utf-8")

    def is_empty(self) -> bool:
        return not self._db.students and not self._db.teachers and not self._db.courses

    def reset(self):
        """Полностью очищает все данные в БД."""
        self._db.students.clear()
        self._db.teachers.clear()
        self._db.courses.clear()
        self._db.submissions.clear()
        self.save()

    def get_all_students(self) -> list[Student]:
        return list(self._db.students.values())

    def get_student(self, sid: str) -> Student | None:
        return self._db.students.get(sid)

    def add_student(self, s: Student) -> Student:
        self._db.students[s.id] = s; self.save(); return s

    def update_student(self, s: Student):
        self._db.students[s.id] = s; self.save()

    def delete_student(self, sid: str):
        self._db.students.pop(sid, None); self.save()

    def get_all_teachers(self) -> list[Teacher]:
        return list(self._db.teachers.values())

    def get_teacher(self, tid: str) -> Teacher | None:
        return self._db.teachers.get(tid)

    def add_teacher(self, t: Teacher) -> Teacher:
        self._db.teachers[t.id] = t; self.save(); return t

    def update_teacher(self, t: Teacher):
        self._db.teachers[t.id] = t; self.save()

    def delete_teacher(self, tid: str):
        self._db.teachers.pop(tid, None); self.save()

    def get_all_courses(self) -> list[Course]:
        return list(self._db.courses.values())

    def get_course(self, cid: str) -> Course | None:
        return self._db.courses.get(cid)

    def add_course(self, c: Course) -> Course:
        self._db.courses[c.id] = c; self.save(); return c

    def update_course(self, c: Course):
        self._db.courses[c.id] = c; self.save()

    def get_all_submissions(self) -> list[HomeworkSubmission]:
        return list(self._db.submissions.values())

    def get_submission(self, sid: str) -> HomeworkSubmission | None:
        return self._db.submissions.get(sid)

    def get_submissions_for_student(self, student_id: str) -> list[HomeworkSubmission]:
        return [s for s in self._db.submissions.values() if s.student_id == student_id]

    def get_submissions_for_course(
        self, course_id: str, student_id: str | None = None
    ) -> list[HomeworkSubmission]:
        return [
            s for s in self._db.submissions.values()
            if s.course_id == course_id
            and (student_id is None or s.student_id == student_id)
        ]

    def add_submission(self, sub: HomeworkSubmission) -> HomeworkSubmission:
        self._db.submissions[sub.id] = sub; self.save(); return sub

    def update_submission(self, sub: HomeworkSubmission):
        self._db.submissions[sub.id] = sub; self.save()