# 🌌 НЕКСУС АКАДЕМИЯ — Онлайн-система управления школой

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?style=for-the-badge&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![Style](https://img.shields.io/badge/UI-Sci--Fi%20Dark%20Mode-cyan?style=for-the-badge)](https://developer.mozilla.org/en-US/docs/Web/CSS)

**НЕКСУС АКАДЕМИЯ** — это современная веб-система управления онлайн-школой, построенная на базе **FastAPI (Python 3.14)** с использованием архитектурного паттерна **Clean Architecture (3-Tier)**. 

Интерфейс приложения выполнен в виде интерактивного Single Page Application (SPA) в футуристичном стиле **Sci-Fi Dark Mode** с использованием визуальных эффектов **Glassmorphism**.

---

## 🚀 Ключевые особенности и бизнес-логика

* **Архитектура Clean Architecture / 3-Tier:** Строгое разделение приложения на слои данных, бизнес-логики и представления (API/UI).
* **Умная JSON-персистентность:** Автоматическое сохранение изменений в `school_data.json`. Связи между сущностями (курсы, студенты, преподаватели) сохраняются через ID, исключая дублирование данных и циклические ссылки.
* **Валидация данных:** Интегрированная проверка корректности email-доменов (наличие `@`, проверка доменных зон) при создании и редактировании студентов.
* **Российская система оценок (2–5):** Выставление текущих оценок строго в диапазоне от 2 до 5.
* **Автоматическое завершение курса:**
    * При закрытии курса рассчитывается финальная средняя оценка для каждого студента с математическим округлением.
    * **Правило Аттестации:** Если у учащегося на курсе выставлено *менее 3 оценок*, в итоговый диплом/историю вместо оценки записывается **"Н/А"** (Не аттестован).
    * Данные курса переносятся в личную историю студентов, а сам курс архивируется.

---

## 📂 Структура проекта

```text
school_app/
├── main.py          # FastAPI app, регистрация роутов и API-эндпоинтов
├── models.py        # Сущности, Pydantic-модели и DTO для валидации
├── repository.py    # Менеджер состояния базы данных, JSON-сериализация
├── services.py      # Слой бизнес-логики (зачисление, оценки, аттестация)
├── requirements.txt # Зависимости проекта
├── school_data.json # Локальная база данных (создаётся автоматически)
└── static/
    └── index.html   # Фронтенд: SPA-интерфейс (Sci-Fi Dark Mode / Glassmorphism)
```

## 🛠 Запуск

Для работы приложения необходим Python 3.14.

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Запустить сервер
uvicorn main:app --reload --port 8000

# 3. Открыть в браузере
http://localhost:8000
```

## 📡 API Эндпоинты

| Метод  | URL                              | Описание                         |

|--------|----------------------------------|----------------------------------|

| GET    | /api/students                    | Список студентов                 |

| POST   | /api/students                    | Создать студента                 |

| GET    | /api/students/{id}/card          | Карточка студента (отчёт)        |

| GET    | /api/teachers                    | Список преподавателей            |

| POST   | /api/teachers                    | Создать преподавателя            |

| GET    | /api/courses                     | Список курсов (с деталями)       |

| POST   | /api/courses                     | Создать курс                     |

| POST   | /api/enroll                      | Зачислить студента на курс       |

| POST   | /api/assign-teacher              | Назначить преподавателя на курс  |

| POST   | /api/grade                       | Выставить оценку                 |

| POST   | /api/courses/{id}/complete       | Завершить курс                   |

## 📖 Интерактивная документация API

Доступна по адресу: http://localhost:8000/docs 

