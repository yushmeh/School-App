from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


def make_client():
    from repository import SchoolRepository
    from services import SchoolService
    import main as main_module

    repo = SchoolRepository.__new__(SchoolRepository)
    from models import SchoolDB
    repo._db = SchoolDB()

    repo.save = lambda: None

    svc = SchoolService(repo)
    main_module.repo = repo
    main_module.svc = svc

    with patch("main.run_seed"):
        client = TestClient(main_module.app, raise_server_exceptions=True)

    return client, repo


@pytest.fixture
def client():
    c, _ = make_client()
    return c


@pytest.fixture
def client_repo():
    return make_client()


class TestStudents:

    def test_list_students_empty(self, client):
        r = client.get("/api/students")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_student_success(self, client):
        r = client.post("/api/students", json={"name": "Анна", "email": "anna@test.ru"})
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Анна"
        assert data["email"] == "anna@test.ru"
        assert "id" in data

    def test_create_student_invalid_email(self, client):
        r = client.post("/api/students", json={"name": "Тест", "email": "not-an-email"})
        assert r.status_code == 422

    def test_create_student_email_normalized_to_lowercase(self, client):
        r = client.post("/api/students", json={"name": "Борис", "email": "Boris@Test.RU"})
        assert r.status_code == 201
        assert r.json()["email"] == "boris@test.ru"

    def test_list_students_after_create(self, client):
        client.post("/api/students", json={"name": "Анна", "email": "anna@test.ru"})
        client.post("/api/students", json={"name": "Борис", "email": "boris@test.ru"})
        r = client.get("/api/students")
        assert len(r.json()) == 2

    def test_update_student(self, client):
        sid = client.post("/api/students", json={"name": "Анна", "email": "anna@test.ru"}).json()["id"]
        r = client.patch(f"/api/students/{sid}", json={"name": "Анна Петрова"})
        assert r.status_code == 200
        assert r.json()["name"] == "Анна Петрова"

    def test_update_student_not_found(self, client):
        r = client.patch("/api/students/nonexistent", json={"name": "X"})
        assert r.status_code == 404

    def test_delete_student(self, client):
        sid = client.post("/api/students", json={"name": "Анна", "email": "anna@test.ru"}).json()["id"]
        r = client.delete(f"/api/students/{sid}")
        assert r.status_code == 200
        assert r.json() == {"deleted": sid}
        assert client.get("/api/students").json() == []

    def test_delete_student_not_found(self, client):
        r = client.delete("/api/students/nonexistent")
        assert r.status_code == 404

    def test_student_card(self, client):
        sid = client.post("/api/students", json={"name": "Анна", "email": "anna@test.ru"}).json()["id"]
        r = client.get(f"/api/students/{sid}/card")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Анна"
        assert data["active_courses"] == []
        assert data["course_history"] == []

    def test_student_stats(self, client):
        sid = client.post("/api/students", json={"name": "Анна", "email": "anna@test.ru"}).json()["id"]
        r = client.get(f"/api/students/{sid}/stats")
        assert r.status_code == 200
        data = r.json()
        assert "overall_avg" in data
        assert "overall_bar" in data


class TestTeachers:

    def test_list_teachers_empty(self, client):
        assert client.get("/api/teachers").json() == []

    def test_create_teacher_success(self, client):
        r = client.post("/api/teachers", json={"name": "Мария", "specialization": "Python"})
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Мария"
        assert data["status"] == "active"

    def test_update_teacher_status_to_vacation(self, client):
        tid = client.post("/api/teachers", json={"name": "Мария", "specialization": "Python"}).json()["id"]
        r = client.patch(f"/api/teachers/{tid}", json={"status": "vacation"})
        assert r.status_code == 200
        assert r.json()["status"] == "vacation"

    def test_update_teacher_invalid_status(self, client):
        tid = client.post("/api/teachers", json={"name": "Мария", "specialization": "Python"}).json()["id"]
        r = client.patch(f"/api/teachers/{tid}", json={"status": "retired"})
        assert r.status_code == 400

    def test_delete_teacher_success(self, client):
        tid = client.post("/api/teachers", json={"name": "Мария", "specialization": "Python"}).json()["id"]
        r = client.delete(f"/api/teachers/{tid}")
        assert r.status_code == 200
        assert r.json() == {"deleted": tid}

    def test_delete_teacher_with_active_course_forbidden(self, client):
        tid = client.post("/api/teachers", json={"name": "Мария", "specialization": "Python"}).json()["id"]
        cid = client.post("/api/courses", json={"title": "Курс", "topic": "Тема"}).json()["id"]
        client.post("/api/assign-teacher", json={"teacher_id": tid, "course_id": cid})
        r = client.delete(f"/api/teachers/{tid}")
        assert r.status_code == 400
        assert "активный курс" in r.json()["detail"]

    def test_teacher_report(self, client):
        tid = client.post("/api/teachers", json={"name": "Мария", "specialization": "Python"}).json()["id"]
        r = client.get(f"/api/teachers/{tid}/report")
        assert r.status_code == 200
        data = r.json()
        assert data["teacher_name"] == "Мария"
        assert data["active_courses_count"] == 0


class TestCourses:

    def test_list_courses_empty(self, client):
        assert client.get("/api/courses").json() == []

    def test_create_course_success(self, client):
        r = client.post("/api/courses", json={"title": "Python", "topic": "Программирование"})
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "Python"
        assert data["status"] == "active"

    def test_update_course(self, client):
        cid = client.post("/api/courses", json={"title": "Python", "topic": "Программирование"}).json()["id"]
        r = client.patch(f"/api/courses/{cid}", json={"title": "Python Pro"})
        assert r.status_code == 200
        assert r.json()["title"] == "Python Pro"

    def test_course_card(self, client):
        cid = client.post("/api/courses", json={"title": "Python", "topic": "Программирование"}).json()["id"]
        r = client.get(f"/api/courses/{cid}/card")
        assert r.status_code == 200
        data = r.json()
        assert data["total_lessons"] == 0
        assert data["total_homeworks"] == 0

    def test_add_module_to_course(self, client):
        cid = client.post("/api/courses", json={"title": "Python", "topic": "Программирование"}).json()["id"]
        r = client.post(f"/api/courses/{cid}/modules", json={"title": "Модуль 1", "order": 1})
        assert r.status_code == 201
        assert len(r.json()["modules"]) == 1

    def test_add_lesson_to_module(self, client):
        cid = client.post("/api/courses", json={"title": "Python", "topic": "Программирование"}).json()["id"]
        mid = client.post(f"/api/courses/{cid}/modules", json={"title": "Модуль 1", "order": 1}).json()["modules"][0]["id"]
        r = client.post(f"/api/courses/{cid}/modules/{mid}/lessons", json={"title": "Урок 1", "order": 1})
        assert r.status_code == 201

    def test_add_homework_to_lesson(self, client):
        cid = client.post("/api/courses", json={"title": "Python", "topic": "Программирование"}).json()["id"]
        mid = client.post(f"/api/courses/{cid}/modules", json={"title": "Модуль 1", "order": 1}).json()["modules"][0]["id"]
        lid = client.post(f"/api/courses/{cid}/modules/{mid}/lessons", json={"title": "Урок 1", "order": 1}).json()["modules"][0]["lessons"][0]["id"]
        r = client.post(f"/api/courses/{cid}/modules/{mid}/lessons/{lid}/homeworks",
                        json={"title": "ДЗ 1", "max_grade": 5})
        assert r.status_code == 201

    def test_complete_course(self, client):
        sid = client.post("/api/students", json={"name": "Анна", "email": "anna@test.ru"}).json()["id"]
        cid = client.post("/api/courses", json={"title": "Python", "topic": "Программирование"}).json()["id"]
        client.post("/api/enroll", json={"student_id": sid, "course_id": cid})
        r = client.post(f"/api/courses/{cid}/complete")
        assert r.status_code == 200
        assert r.json()["status"] == "completed"

    def test_complete_course_twice_forbidden(self, client):
        cid = client.post("/api/courses", json={"title": "Python", "topic": "Программирование"}).json()["id"]
        client.post(f"/api/courses/{cid}/complete")
        r = client.post(f"/api/courses/{cid}/complete")
        assert r.status_code == 400


class TestEnrollAndAssign:

    def test_enroll_student_success(self, client):
        sid = client.post("/api/students", json={"name": "Анна", "email": "anna@test.ru"}).json()["id"]
        cid = client.post("/api/courses", json={"title": "Python", "topic": "Программирование"}).json()["id"]
        r = client.post("/api/enroll", json={"student_id": sid, "course_id": cid})
        assert r.status_code == 200
        assert sid in r.json()["enrolled_student_ids"]

    def test_enroll_student_twice_forbidden(self, client):
        sid = client.post("/api/students", json={"name": "Анна", "email": "anna@test.ru"}).json()["id"]
        cid = client.post("/api/courses", json={"title": "Python", "topic": "Программирование"}).json()["id"]
        client.post("/api/enroll", json={"student_id": sid, "course_id": cid})
        r = client.post("/api/enroll", json={"student_id": sid, "course_id": cid})
        assert r.status_code == 400

    def test_enroll_into_completed_course_forbidden(self, client):
        sid = client.post("/api/students", json={"name": "Анна", "email": "anna@test.ru"}).json()["id"]
        cid = client.post("/api/courses", json={"title": "Python", "topic": "Программирование"}).json()["id"]
        client.post(f"/api/courses/{cid}/complete")
        r = client.post("/api/enroll", json={"student_id": sid, "course_id": cid})
        assert r.status_code == 400

    def test_assign_teacher_success(self, client):
        tid = client.post("/api/teachers", json={"name": "Мария", "specialization": "Python"}).json()["id"]
        cid = client.post("/api/courses", json={"title": "Python", "topic": "Программирование"}).json()["id"]
        r = client.post("/api/assign-teacher", json={"teacher_id": tid, "course_id": cid})
        assert r.status_code == 200
        assert r.json()["teacher_id"] == tid

    def test_assign_teacher_on_vacation_forbidden(self, client):
        tid = client.post("/api/teachers", json={"name": "Мария", "specialization": "Python"}).json()["id"]
        client.patch(f"/api/teachers/{tid}", json={"status": "vacation"})
        cid = client.post("/api/courses", json={"title": "Python", "topic": "Программирование"}).json()["id"]
        r = client.post("/api/assign-teacher", json={"teacher_id": tid, "course_id": cid})
        assert r.status_code == 400


class TestHomework:

    @staticmethod
    def _setup_course_with_hw(client) -> dict:
        sid = client.post("/api/students", json={"name": "Анна", "email": "anna@test.ru"}).json()["id"]
        tid = client.post("/api/teachers", json={"name": "Мария", "specialization": "Python"}).json()["id"]
        cid = client.post("/api/courses", json={"title": "Python", "topic": "Программирование"}).json()["id"]
        client.post("/api/enroll", json={"student_id": sid, "course_id": cid})
        mid = client.post(f"/api/courses/{cid}/modules", json={"title": "Модуль 1", "order": 1}).json()["modules"][0]["id"]
        course_data = client.post(f"/api/courses/{cid}/modules/{mid}/lessons",
                                   json={"title": "Урок 1", "order": 1}).json()
        lid = course_data["modules"][0]["lessons"][0]["id"]
        course_data = client.post(f"/api/courses/{cid}/modules/{mid}/lessons/{lid}/homeworks",
                                   json={"title": "ДЗ 1", "max_grade": 5}).json()
        hwid = course_data["modules"][0]["lessons"][0]["homeworks"][0]["id"]
        return {"sid": sid, "tid": tid, "cid": cid, "mid": mid, "lid": lid, "hwid": hwid}

    def test_assign_homework_to_student(self, client):
        ids = self._setup_course_with_hw(client)
        r = client.post("/api/homework/assign", json={
            "homework_id": ids["hwid"], "lesson_id": ids["lid"],
            "module_id": ids["mid"], "course_id": ids["cid"],
            "student_id": ids["sid"],
        })
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_assign_homework_to_all_students(self, client):
        ids = self._setup_course_with_hw(client)
        sid2 = client.post("/api/students", json={"name": "Борис", "email": "boris@test.ru"}).json()["id"]
        client.post("/api/enroll", json={"student_id": sid2, "course_id": ids["cid"]})
        r = client.post("/api/homework/assign", json={
            "homework_id": ids["hwid"], "lesson_id": ids["lid"],
            "module_id": ids["mid"], "course_id": ids["cid"],
        })
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_assign_homework_twice_ignored(self, client):
        ids = self._setup_course_with_hw(client)
        payload = {"homework_id": ids["hwid"], "lesson_id": ids["lid"],
                   "module_id": ids["mid"], "course_id": ids["cid"], "student_id": ids["sid"]}
        client.post("/api/homework/assign", json=payload)
        r = client.post("/api/homework/assign", json=payload)
        assert r.status_code == 200
        assert len(r.json()) == 0

    def test_grade_homework(self, client):
        ids = self._setup_course_with_hw(client)
        sub_id = client.post("/api/homework/assign", json={
            "homework_id": ids["hwid"], "lesson_id": ids["lid"],
            "module_id": ids["mid"], "course_id": ids["cid"],
            "student_id": ids["sid"],
        }).json()[0]["id"]
        r = client.post("/api/homework/grade", json={
            "submission_id": sub_id, "teacher_id": ids["tid"],
            "grade": 5, "comment": "Отлично",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["grade"] == 5
        assert data["comment"] == "Отлично"

    def test_grade_homework_invalid_grade(self, client):
        r = client.post("/api/homework/grade", json={
            "submission_id": "x", "teacher_id": "x", "grade": 6,
        })
        assert r.status_code == 422

    def test_course_submissions(self, client):
        ids = self._setup_course_with_hw(client)
        client.post("/api/homework/assign", json={
            "homework_id": ids["hwid"], "lesson_id": ids["lid"],
            "module_id": ids["mid"], "course_id": ids["cid"],
            "student_id": ids["sid"],
        })
        r = client.get(f"/api/courses/{ids['cid']}/submissions")
        assert r.status_code == 200
        assert len(r.json()) == 1


class TestFinalGrade:

    @staticmethod
    def _enroll_and_grade(client, grades: list[int]) -> tuple[str, str]:
        sid = client.post("/api/students", json={"name": "Анна", "email": "anna@test.ru"}).json()["id"]
        tid = client.post("/api/teachers", json={"name": "Мария", "specialization": "Python"}).json()["id"]
        cid = client.post("/api/courses", json={"title": "Python", "topic": "Программирование"}).json()["id"]
        client.post("/api/enroll", json={"student_id": sid, "course_id": cid})
        mid = client.post(f"/api/courses/{cid}/modules", json={"title": "М1", "order": 1}).json()["modules"][0]["id"]

        for i, grade in enumerate(grades):
            course_data = client.post(f"/api/courses/{cid}/modules/{mid}/lessons",
                                       json={"title": f"Урок {i}", "order": i + 1}).json()
            lid = course_data["modules"][0]["lessons"][i]["id"]
            hw_data = client.post(f"/api/courses/{cid}/modules/{mid}/lessons/{lid}/homeworks",
                                   json={"title": f"ДЗ {i}", "max_grade": 5}).json()
            hwid = hw_data["modules"][0]["lessons"][i]["homeworks"][0]["id"]
            sub_id = client.post("/api/homework/assign", json={
                "homework_id": hwid, "lesson_id": lid,
                "module_id": mid, "course_id": cid, "student_id": sid,
            }).json()[0]["id"]
            client.post("/api/homework/grade", json={
                "submission_id": sub_id, "teacher_id": tid, "grade": grade,
            })
        return sid, cid

    def test_final_grade_calculated_correctly(self, client):
        sid, cid = self._enroll_and_grade(client, [3, 4, 5])
        client.post(f"/api/courses/{cid}/complete")
        history = client.get(f"/api/students/{sid}/card").json()["course_history"]
        assert len(history) == 1
        assert history[0]["final_grade"] == 4.0

    def test_final_grade_na_when_less_than_3_grades(self, client):
        sid, cid = self._enroll_and_grade(client, [5, 5])
        client.post(f"/api/courses/{cid}/complete")
        history = client.get(f"/api/students/{sid}/card").json()["course_history"]
        assert history[0]["final_grade"] is None

    def test_final_grade_na_when_no_grades(self, client):
        sid = client.post("/api/students", json={"name": "Анна", "email": "anna@test.ru"}).json()["id"]
        cid = client.post("/api/courses", json={"title": "Python", "topic": "Программирование"}).json()["id"]
        client.post("/api/enroll", json={"student_id": sid, "course_id": cid})
        client.post(f"/api/courses/{cid}/complete")
        history = client.get(f"/api/students/{sid}/card").json()["course_history"]
        assert history[0]["final_grade"] is None


class TestAnalytics:

    def test_analytics_empty_db(self, client):
        r = client.get("/api/analytics")
        assert r.status_code == 200
        data = r.json()
        assert data["total_students"] == 0
        assert data["total_teachers"] == 0
        assert data["active_courses"] == 0

    def test_analytics_counts_correctly(self, client):
        client.post("/api/students", json={"name": "Анна", "email": "anna@test.ru"})
        client.post("/api/teachers", json={"name": "Мария", "specialization": "Python"})
        client.post("/api/courses", json={"title": "Python", "topic": "Программирование"})
        data = client.get("/api/analytics").json()
        assert data["total_students"] == 1
        assert data["total_teachers"] == 1
        assert data["active_courses"] == 1

    def test_analytics_top_courses(self, client):
        sid = client.post("/api/students", json={"name": "Анна", "email": "anna@test.ru"}).json()["id"]
        cid = client.post("/api/courses", json={"title": "Python", "topic": "Программирование"}).json()["id"]
        client.post("/api/enroll", json={"student_id": sid, "course_id": cid})
        data = client.get("/api/analytics").json()
        assert len(data["top_courses"]) == 1
        assert data["top_courses"][0]["student_count"] == 1


class TestCSVExport:

    def test_export_student_csv(self, client):
        sid = client.post("/api/students", json={"name": "Анна", "email": "anna@test.ru"}).json()["id"]
        r = client.get(f"/api/export/student/{sid}")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        assert "Анна" in r.text

    def test_export_teacher_csv(self, client):
        tid = client.post("/api/teachers", json={"name": "Мария", "specialization": "Python"}).json()["id"]
        r = client.get(f"/api/export/teacher/{tid}")
        assert r.status_code == 200
        assert "Мария" in r.text

    def test_export_course_csv(self, client):
        cid = client.post("/api/courses", json={"title": "Python", "topic": "Программирование"}).json()["id"]
        r = client.get(f"/api/export/course/{cid}")
        assert r.status_code == 200
        assert "Python" in r.text

    def test_export_student_not_found(self, client):
        r = client.get("/api/export/student/nonexistent")
        assert r.status_code == 404


class TestSeedEndpoint:

    def test_force_seed_returns_ok(self, client):
        r = client.post("/api/seed")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_force_seed_clears_custom_data_and_repopulates(self, client):
        client.post("/api/students", json={"name": "Уникальный Тест", "email": "unique@test.ru"})
        client.post("/api/seed")
        names = [s["name"] for s in client.get("/api/students").json()]
        assert "Уникальный Тест" not in names
        assert "Анна Петрова" in names

    def test_force_seed_populates_courses(self, client):
        client.post("/api/seed")
        assert len(client.get("/api/courses").json()) == 6

    def test_force_seed_populates_teachers(self, client):
        client.post("/api/seed")
        assert len(client.get("/api/teachers").json()) == 6