# SafeCall Voice Guard — ML System Design (ИТМО)

Сервис в режиме, близком к реальному времени, анализирует аудиофрагмент телефонного звонка и предупреждает пользователя о высокой вероятности подделки голоса — тем самым **снижая долю успешных мошеннических звонков с использованием голосовых дипфейков**.

## 📁 Структура репозитория

| Папка | Тема | Формат |
|-------|------|--------|
| [DZ1/](DZ1/) | Бизнес-анализ | Markdown |
| [DZ2/](DZ2/) | Консультация с экспертом | Markdown |
| [DZ3/](DZ3/) | Бенчмаркинг | Markdown |
| [DZ4/](DZ4/) | Данные и валидация (EDA) | Jupyter Notebook + Markdown |
| [DZ5-6/](DZ5-6/) | ML Baseline | Jupyter Notebook |
| [DZ7/](DZ7/) | Улучшение модели | Jupyter Notebook |
| [DZ8/](DZ8/) | **Упаковка MVP** | Docker Compose + FastAPI + ML Worker |

## 🚀 ДЗ №8 — быстрый старт

```powershell
cd DZ8
docker compose up -d --build
```

Открыть http://localhost:8088 — логин `admin@safecall.ru` / `admin123`.

Подробности: [DZ8/DZ№8.md](DZ8/DZ№8.md) и [DZ8/README.md](DZ8/README.md).

## 🔬 Датасет

**ASVspoof 2019 LA** — 122 299 аудиофайлов (bonafide + spoof), 19 атакующих TTS/VC-систем.

## 🛠 Стек

- Python 3.12, FastAPI, SQLModel, PostgreSQL, RabbitMQ
- PyTorch, transformers (XLSR-53), Docker Compose
- ASVspoof 2019 LA, Common Voice RU, Golos, RU-Fake (обучение в DZ7)
