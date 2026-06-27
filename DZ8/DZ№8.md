# ДЗ №8 — SafeCall Voice Guard: упаковка MVP

> **Курс:** ML System Design and My First Data Project (ИТМО)  
> **Проект:** SafeCall Voice Guard — детекция голосовых дипфейков  
> **Формат сдачи:** Docker Compose MVP в папке `DZ8/`

---

## Цель работы

Упаковать ML-модель из ДЗ №7 в production-ready MVP: REST API, веб-интерфейс, очередь задач, БД, Docker и масштабируемые ML-воркеры.

## Чеклист требований

| № | Требование | Реализация |
|---|------------|------------|
| 1 | Доменная модель | `User`, `Prediction`, `TaskStatus` — `app/models/` |
| 2 | Хранение данных | PostgreSQL 16 + SQLModel ORM |
| 3 | REST-интерфейс | FastAPI: auth, predict, health, Swagger `/docs` |
| 4 | Пользовательский интерфейс | Jinja2 + Bootstrap: login, upload, history |
| 5 | Тесты | pytest: API + CRUD (`app/tests/`) |
| 6 | Docker-контейнер | 5 сервисов в `docker-compose.yaml` |
| 7 | Масштабирование воркеров | `docker compose up -d --scale ml_worker=N` |

## Быстрая проверка (для преподавателя)

```powershell
cd DZ8
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://localhost:8088/health
docker compose exec app pytest tests/ -v
```

**UI:** http://localhost:8088  
**Swagger:** http://localhost:8088/docs  
**RabbitMQ UI:** http://localhost:15672 (rmuser / rmpassword)

**Тестовый аккаунт:** `admin@safecall.ru` / `admin123`

> Первый запуск скачивает XLSR-53 backbone (~1.2 GB) — 10–30 мин.  
> Веса head-модели уже в репозитории: `ml_worker/weights/best_xlsr_head.pth` (из ДЗ7).

## Архитектура

```
Browser :8088 → Nginx → FastAPI (:8080)
                    ├── PostgreSQL
                    └── RabbitMQ → ML Worker × N (XLSR-53)
```

## Связь с предыдущими ДЗ

| ДЗ | Что использовано в MVP |
|----|------------------------|
| DZ1–DZ3 | Бизнес-контекст, бенчмаркинг |
| DZ4 | EDA, понимание ASVspoof 2019 LA |
| DZ5-6 | Baseline-модель |
| DZ7 | XLSR-53 + MLP head, threshold 0.37, fusion.py |

## Стек

- Python 3.12, FastAPI, SQLModel, PostgreSQL 16
- PyTorch 2.6 CPU, transformers (XLSR-53)
- RabbitMQ 3.13, Nginx, Docker Compose

Подробная инструкция по запуску, API и масштабированию — в [README.md](README.md).
