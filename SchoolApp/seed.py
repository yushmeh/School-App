from __future__ import annotations
from models import (
    Student, Teacher, Course, Module, Lesson, Homework,
    HomeworkSubmission,
)
from repository import SchoolRepository
from datetime import date, timedelta
import random


def seed(repo: SchoolRepository) -> None:
    """Добавляет тестовые данные, не затрагивая уже существующие записи.
    Дубликаты определяются по email (студенты), имени (преподаватели)
    и названию (курсы)."""

    rng = random.Random(42)
    today = date.today()

    # ── Фабрика модулей / уроков / ДЗ ────────────────────────────────────────
    def make_module(title: str, lessons_data: list[tuple[str, list[str]]], order: int) -> Module:
        lessons = []
        for lo, (lt, hw_titles) in enumerate(lessons_data, 1):
            hws = [Homework(title=hwt, description=f"Описание: {hwt}", max_grade=5) for hwt in hw_titles]
            lessons.append(Lesson(title=lt, description=f"Описание урока «{lt}»", order=lo, homeworks=hws))
        return Module(title=title, order=order, lessons=lessons)

    # ── Преподаватели ─────────────────────────────────────────────────────────
    teachers_data = [
        ("Алексей Смирнов",     "Python, Backend"),
        ("Мария Козлова",       "Data Science, ML"),
        ("Дмитрий Попов",       "Frontend, React"),
        ("Елена Новикова",      "DevOps, Kubernetes"),
        ("Иван Соколов",        "Математика, Алгоритмы"),
        ("Ольга Лебедева",      "UX/UI, Figma"),
    ]

    # Индекс существующих преподавателей по имени
    existing_teachers_by_name = {t.name: t for t in repo.get_all_teachers()}

    teachers = []
    for name, spec in teachers_data:
        if name in existing_teachers_by_name:
            # Преподаватель уже есть — берём существующего
            teachers.append(existing_teachers_by_name[name])
        else:
            t = Teacher(name=name, specialization=spec)
            repo.add_teacher(t)
            teachers.append(t)

    # ── Студенты ──────────────────────────────────────────────────────────────
    students_data = [
        ("Анна Петрова",        "anna.petrova@student.ru"),
        ("Борис Иванов",        "boris.ivanov@student.ru"),
        ("Виктория Сидорова",   "victoria.sidorova@student.ru"),
        ("Григорий Кузнецов",   "grigoriy.kuznetsov@student.ru"),
        ("Дарья Морозова",      "daria.morozova@student.ru"),
        ("Евгений Волков",      "evgeniy.volkov@student.ru"),
        ("Жанна Алексеева",     "zhanna.alekseeva@student.ru"),
    ]

    # Индекс существующих студентов по email
    existing_students_by_email = {s.email: s for s in repo.get_all_students()}

    students = []
    for name, email in students_data:
        if email in existing_students_by_email:
            # Студент уже есть — берём существующего
            students.append(existing_students_by_email[email])
        else:
            s = Student(name=name, email=email)
            repo.add_student(s)
            students.append(s)

    # ── Курсы с модулями ──────────────────────────────────────────────────────
    courses_raw = [
        {
            "title": "Python с нуля",
            "topic": "Программирование",
            "teacher": teachers[0],
            "modules": [
                ("Основы Python", [
                    ("Переменные и типы данных", ["ДЗ: типы данных", "ДЗ: конвертация"]),
                    ("Условия и циклы",          ["ДЗ: FizzBuzz", "ДЗ: числа Фибоначчи"]),
                ]),
                ("Функции и модули", [
                    ("Определение функций",      ["ДЗ: рекурсия"]),
                    ("Встроенные модули",         ["ДЗ: работа с os", "ДЗ: datetime"]),
                ]),
                ("ООП", [
                    ("Классы и объекты",         ["ДЗ: банковский счёт"]),
                    ("Наследование",              ["ДЗ: зоопарк ООП"]),
                ]),
            ],
        },
        {
            "title": "Data Science: Введение",
            "topic": "Наука о данных",
            "teacher": teachers[1],
            "modules": [
                ("Pandas и NumPy", [
                    ("Основы Pandas",            ["ДЗ: загрузка CSV", "ДЗ: фильтрация"]),
                    ("NumPy массивы",             ["ДЗ: матричные операции"]),
                ]),
                ("Визуализация данных", [
                    ("Построение графиков",      ["ДЗ: гистограмма продаж"]),
                    ("Seaborn и стили",           ["ДЗ: тепловая карта"]),
                ]),
                ("Статистика", [
                    ("Описательная статистика",  ["ДЗ: анализ датасета"]),
                    ("Гипотезы и тесты",          ["ДЗ: t-тест"]),
                ]),
            ],
        },
        {
            "title": "React для фронтенд-разработчиков",
            "topic": "Frontend",
            "teacher": teachers[2],
            "modules": [
                ("Основы React", [
                    ("JSX и компоненты",         ["ДЗ: первый компонент"]),
                    ("Props и State",              ["ДЗ: счётчик кликов"]),
                ]),
                ("Хуки и роутинг", [
                    ("useState и useEffect",     ["ДЗ: таймер", "ДЗ: API-запрос"]),
                    ("React Router",              ["ДЗ: мини-SPA"]),
                ]),
            ],
        },
        {
            "title": "DevOps: Docker и Kubernetes",
            "topic": "DevOps",
            "teacher": teachers[3],
            "modules": [
                ("Docker", [
                    ("Контейнеры и образы",      ["ДЗ: Dockerfile для Flask"]),
                    ("Docker Compose",             ["ДЗ: стек с базой данных"]),
                ]),
                ("Kubernetes", [
                    ("Pods и Deployments",       ["ДЗ: деплой приложения"]),
                    ("Services и Ingress",        ["ДЗ: настройка роутинга"]),
                ]),
            ],
        },
        {
            "title": "Алгоритмы и структуры данных",
            "topic": "Computer Science",
            "teacher": teachers[4],
            "modules": [
                ("Сложность и сортировки", [
                    ("Big-O нотация",            ["ДЗ: анализ сложности"]),
                    ("Сортировки",                ["ДЗ: merge sort", "ДЗ: quick sort"]),
                ]),
                ("Деревья и графы", [
                    ("Бинарные деревья",         ["ДЗ: обход дерева"]),
                    ("Графы и BFS/DFS",           ["ДЗ: кратчайший путь"]),
                ]),
            ],
        },
        {
            "title": "UX/UI Дизайн",
            "topic": "Дизайн",
            "teacher": teachers[5],
            "modules": [
                ("Основы дизайна", [
                    ("Теория цвета",             ["ДЗ: цветовая палитра"]),
                    ("Типографика",               ["ДЗ: выбор шрифтов"]),
                ]),
                ("Figma", [
                    ("Компоненты и авто-лейаут", ["ДЗ: дизайн-система"]),
                    ("Прототипирование",          ["ДЗ: интерактивный прототип"]),
                ]),
            ],
        },
    ]

    # Индекс существующих курсов по названию
    existing_courses_by_title = {c.title: c for c in repo.get_all_courses()}

    courses = []
    new_courses = []  # только что созданные — для них добавим зачисления и ДЗ
    for i, raw in enumerate(courses_raw):
        if raw["title"] in existing_courses_by_title:
            # Курс уже есть — берём существующий, зачисления не трогаем
            courses.append(existing_courses_by_title[raw["title"]])
        else:
            mods = [make_module(mt, ls, o + 1) for o, (mt, ls) in enumerate(raw["modules"])]
            c = Course(
                title=raw["title"],
                topic=raw["topic"],
                teacher_id=raw["teacher"].id,
                modules=mods,
                start_date=(today - timedelta(days=30 + i * 7)).isoformat(),
            )
            repo.add_course(c)
            courses.append(c)
            new_courses.append(c)

    # ── Зачисления — только для новых курсов ──────────────────────────────────
    enrollments = [
        (students[0], [courses[0], courses[1], courses[4]]),
        (students[1], [courses[0], courses[2], courses[3]]),
        (students[2], [courses[1], courses[2], courses[5]]),
        (students[3], [courses[3], courses[4], courses[0]]),
        (students[4], [courses[1], courses[5], courses[3]]),
        (students[5], [courses[0], courses[4], courses[2]]),
        (students[6], [courses[2], courses[5], courses[1]]),
    ]

    for stu, enrolled_courses in enrollments:
        for c in enrolled_courses:
            # Зачисляем только если курс новый и студент ещё не зачислен
            if c in new_courses and stu.id not in c.enrolled_student_ids:
                c.enrolled_student_ids.append(stu.id)
                repo.update_course(c)

    # ── Выдача и оценка ДЗ — только для новых курсов ─────────────────────────
    # Индекс уже существующих submissions чтобы не дублировать
    existing_sub_keys = {
        (s.student_id, s.homework_id)
        for s in repo.get_all_submissions()
    }

    for stu, enrolled_courses in enrollments:
        for c in enrolled_courses:
            if c not in new_courses:
                continue
            all_hws = [
                (mod, les, hw)
                for mod in c.modules
                for les in mod.lessons
                for hw in les.homeworks
            ]
            subset = all_hws[:max(1, int(len(all_hws) * rng.uniform(0.6, 1.0)))]
            for mod, les, hw in subset:
                key = (stu.id, hw.id)
                if key in existing_sub_keys:
                    continue
                sub = HomeworkSubmission(
                    homework_id=hw.id,
                    lesson_id=les.id,
                    module_id=mod.id,
                    course_id=c.id,
                    student_id=stu.id,
                    grade=rng.randint(3, 5),
                    graded_by=c.teacher_id,
                    graded_at=today.isoformat(),
                )
                repo.add_submission(sub)
                existing_sub_keys.add(key)

    added_t = sum(1 for name, _ in teachers_data if name not in {t.name: t for t in repo.get_all_teachers() if t.name != name})
    print(f"[seed] Готово: добавлено {len(new_courses)} новых курсов из {len(courses_raw)}. "
          f"Существующие данные сохранены.")