import json
import os
from pathlib import Path
from models import SchoolDB, Student, Teacher, Course

DB_PATH = Path("school_data.json")

class SchoolRepository:
    def __init__(self):
        self._db: SchoolDB = SchoolDB()
        self._load()
        # СТРОКУ atexit.register(self.save) — УДАЛЯЕМ

    def _load(self):
        if DB_PATH.exists():
            try:
                raw = DB_PATH.read_text(encoding="utf-8")
                if not raw.strip():
                    self._db = SchoolDB()
                    return
                self._db = SchoolDB.model_validate_json(raw)
            except Exception as exc:
                print(f"[repo] Could not load DB, starting fresh: {exc}")

    def save(self):
        # Оставляем вашу отличную атомарную запись
        temp_path = DB_PATH.with_suffix(".json.tmp")
        try:
            json_data = self._db.model_dump_json(indent=2)
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(json_data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, DB_PATH)
            print("[repo] Данные успешно сохранены на диск.") # Для отладки
        except Exception as exc:
            print(f"[repo] Critical error during saving data: {exc}")
            if temp_path.exists():
                temp_path.unlink()

    # ── Students ──────────────────────────────────────────────────────────────

    def get_all_students(self) -> list[Student]:
        return list(self._db.students.values())

    def get_student(self, sid: str) -> Student | None:
        return self._db.students.get(sid)

    def add_student(self, s: Student) -> Student:
        self._db.students[s.id] = s
        self.save()
        return s

    def update_student(self, s: Student):
        self._db.students[s.id] = s
        self.save()

    def delete_student(self, sid: str):
        self._db.students.pop(sid, None)
        self.save()

    # ── Teachers ─────────────────────────────────────────────────────────────

    def get_all_teachers(self) -> list[Teacher]:
        return list(self._db.teachers.values())

    def get_teacher(self, tid: str) -> Teacher | None:
        return self._db.teachers.get(tid)

    def add_teacher(self, t: Teacher) -> Teacher:
        self._db.teachers[t.id] = t
        self.save()
        return t

    def update_teacher(self, t: Teacher):
        self._db.teachers[t.id] = t
        self.save()

    def delete_teacher(self, tid: str):
        self._db.teachers.pop(tid, None)
        self.save()

    # ── Courses ───────────────────────────────────────────────────────────────

    def get_all_courses(self) -> list[Course]:
        return list(self._db.courses.values())

    def get_course(self, cid: str) -> Course | None:
        return self._db.courses.get(cid)

    def add_course(self, c: Course) -> Course:
        self._db.courses[c.id] = c
        self.save()
        return c

    def update_course(self, c: Course):
        self._db.courses[c.id] = c
        self.save()