# SafeCall Voice Guard — MVP

Система детекции голосовых дипфейков в телефонных звонках.

**Курс:** ИТМО — ML System Design and My First Data Project  
**ДЗ №8:** Упаковка MVP

## Архитектура

```
Browser :8088 → Nginx (:80) → FastAPI (:8080)
                         ├── PostgreSQL (:5432)
                         └── RabbitMQ (:5672) → ML Worker(s) × N
```

5 сервисов в Docker Compose:
- **app** — FastAPI REST API + Jinja2 UI
- **ml_worker** — XLSR-53 inference (масштабируемый)
- **web** — Nginx reverse proxy
- **db** — PostgreSQL 16
- **rabbitmq** — очередь задач

Сервис упакован так, чтобы запускаться из этой папки одной командой `docker compose up -d --build`. Количество ML worker можно увеличивать через `--scale ml_worker=N`.

## ML Модель

| Метрика | Значение |
|---------|----------|
| Архитектура | Frozen XLSR-53 + MLP head |
| F1 (eval) | 0.927 |
| Recall | 0.969 |
| Precision | 0.871 |
| Threshold | 0.37 (cost-optimized) |
| Fusion (ML + Context) | 67% → 100% на реальных файлах |

Модель обучена в ДЗ №7 на датасетах: ASVspoof2019 LA, Common Voice RU, Golos, RU-Fake.

## Запуск (пошагово)

### 0. Предусловия

- **Docker Desktop** установлен и запущен (иконка в трее зелёная)
- **Минимум 6-8 GB** свободного места: при первом запуске скачивается XLSR-53 backbone
- Файл `ml_worker/weights/best_xlsr_head.pth` на месте (1.1 MB, из ДЗ7)

Проверка готовности (PowerShell):
```powershell
# Docker работает?
docker info --format "{{.ServerVersion}}"

# Свободное место?
Get-PSDrive C | Select-Object @{N='FreeGB';E={[math]::Round($_.Free/1GB,2)}}

# Head-модель на месте?
Test-Path "ml_worker\weights\best_xlsr_head.pth"
```

### 1. Первый запуск (из папки DZ8)

```powershell
cd "...\DZ8"

# Собрать и запустить все 5 сервисов
docker compose up -d --build
```

`.env` файлы уже не обязательны для Docker Compose: в `docker-compose.yaml` есть безопасные demo-defaults. Если нужно поменять пароли/секреты, скопируйте примеры:

```powershell
Copy-Item .env.example .env
Copy-Item app\.env.example app\.env
```

> ⚠️ **Первый запуск** скачает Python/PyTorch/transformers и XLSR-53 backbone.
> Это занимает 10-30 мин в зависимости от интернета.
> XLSR-53 кэшируется в Docker volume `hf_cache`, поэтому следующие запуски быстрее.

### 2. Проверка что всё поднялось

```powershell
# Статус контейнеров (все должны быть Up / healthy)
docker compose ps

# Логи (если что-то не стартует)
docker compose logs -f

# Только ML воркер
docker compose logs -f ml_worker

# Smoke-test API
Invoke-RestMethod http://localhost:8088/health
```

### 3. Открыть в браузере

| URL | Что |
|-----|-----|
| http://localhost:8088 | Главная страница SafeCall |
| http://localhost:8088/auth/login | Вход в систему |
| http://localhost:8088/api/predict/upload | Загрузка аудио |
| http://localhost:8088/api/predict/history | История проверок |
| http://localhost:15672 | RabbitMQ Management (rmuser / rmpassword) |
| http://localhost:8088/docs | Swagger API документация |

### 4. Повседневные команды

```powershell
# Остановить
docker compose down

# Запустить (без пересборки, быстро)
docker compose up -d

# Перезапустить один сервис
docker compose restart app

# Масштабировать воркеры (например 4 штуки)
docker compose up -d --scale ml_worker=4

# Тесты
docker compose exec app pytest tests/ -v

# Пересобрать после правок кода
docker compose up -d --build

# Полная остановка + удаление данных БД
docker compose down -v
```

### 5. Предсдачная проверка

```powershell
# Проверить конфигурацию compose
docker compose config --quiet

# Проверить масштабирование worker
docker compose up -d --scale ml_worker=2
docker compose ps

# Прогнать тесты API/БД
docker compose exec app pytest tests/ -v
```

### 6. Если мало места на диске

```powershell
# Посмотреть сколько Docker занимает
docker system df

# Очистить неиспользуемые образы/кэш (освободит гигабайты)
docker system prune -a -f

# Очистить HuggingFace cache (может быть 5+ GB)
docker volume rm safecall-mvp_hf_cache

# Очистить TEMP
Remove-Item "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue
```

### 7. Если Docker Desktop завис

```powershell
# Убить все процессы Docker
taskkill /f /im "Docker Desktop.exe"
taskkill /f /im "com.docker.backend.exe"

# Подождать 5 сек, перезапустить
Start-Sleep 5
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Подождать 30 сек, проверить
Start-Sleep 30
docker info --format "{{.ServerVersion}}"
```

## Тестовый аккаунт

- Email: `admin@safecall.ru`
- Пароль: `admin123`

## Мобильный клиент (Android / REST API)

MVP уже готов для подключения Android-клиента: мобильное приложение может использовать тот же REST API, что и web-интерфейс. Серверная логика остается без изменений: Android отправляет аудио в FastAPI, FastAPI кладет задачу в RabbitMQ, `ml_worker` выполняет inference и сохраняет результат в PostgreSQL.

### Что умеет текущий MVP

Текущая версия реализует **асинхронную проверку аудио**, а не автоматическую защиту во время системного телефонного звонка:

- пользователь записывает или выбирает аудиофайл на Android;
- мобильный клиент отправляет файл в `POST /api/predict/send_task`;
- сервер обрабатывает задачу в очереди RabbitMQ;
- Android получает результат через `GET /api/predict/tasks/{task_id}`.

Такой сценарий подходит для `post-call` проверки, демонстрации REST API и будущего мобильного клиента.

### Что нужно для live detection во время звонка

Автоматическое обнаружение дипфейка **во время обычного телефонного звонка на Android не входит в текущий MVP**. Для этого нужен отдельный live-режим:

- доступ к аудио звонка в реальном времени;
- нарезка потока на короткие окна, например 3-5 секунд;
- streaming или частая отправка аудиофрагментов на backend;
- быстрый inference и возврат предупреждения пользователю;
- Android-разрешения и совместимость с ограничениями записи звонков.

Важное ограничение: современные версии Android сильно ограничивают запись системных телефонных звонков для обычных приложений. Поэтому live-защита реалистичнее как следующий этап в одном из сценариев:

- VoIP-звонки внутри собственного приложения;
- корпоративное Android-окружение / MDM;
- интеграция на стороне АТС, оператора связи или колл-центра;
- демонстрационный режим через микрофон/громкую связь.

Итого: **ДЗ8 MVP закрывает REST API, UI, очередь, БД, Docker и масштабируемый ML worker для проверки аудиофайлов. Live detection во время звонка — roadmap следующей версии продукта.**

### Base URL для телефона

`localhost` работает только на том устройстве, где запущен Docker. Для Android нужно использовать один из вариантов:

| Сценарий | Base URL |
|----------|----------|
| Android Studio Emulator | `http://10.0.2.2:8088` |
| Реальный Android в той же Wi-Fi сети | `http://<IP_ноутбука>:8088` |
| Демо вне локальной сети | временный HTTPS tunnel: ngrok / Cloudflare Tunnel |

IP ноутбука в Windows можно посмотреть так:

```powershell
ipconfig
```

Нужен IPv4-адрес активного Wi-Fi/Ethernet адаптера, например `192.168.1.50`. Тогда с телефона API будет доступен как `http://192.168.1.50:8088`.

> Для Android 9+ обычный `http://` может быть заблокирован политикой cleartext traffic. Для учебного MVP можно временно разрешить cleartext для локального IP в `network_security_config.xml`, а для публичного демо лучше использовать HTTPS tunnel.

### REST-сценарий

1. Авторизация:

```http
POST /auth/token
Content-Type: application/x-www-form-urlencoded

username=admin@safecall.ru&password=admin123
```

Ответ выставляет cookie `SAFECALL_API` с JWT. Мобильный клиент может хранить cookie в `CookieJar` или передавать JWT как `Authorization: Bearer <token>`.

2. Загрузка аудио:

```http
POST /api/predict/send_task
Content-Type: multipart/form-data

file=<audio.wav|audio.ogg|audio.mp3>
```

Ответ:

```json
{
  "message": "Task sent successfully!",
  "task_id": 2
}
```

3. Получение результата:

```http
GET /api/predict/tasks/{task_id}
```

Пока задача обрабатывается, статус будет `queued`. После обработки:

```json
{
  "id": 2,
  "status": "completed",
  "verdict": "SPOOF",
  "spoof_probability": 0.7994,
  "confidence": 0.7994,
  "threshold_used": 0.37,
  "processing_time_ms": 876.6,
  "model_version": "xlsr-53-head-v1"
}
```

Для мобильного MVP достаточно polling-логики: после upload опрашивать `GET /api/predict/tasks/{task_id}` раз в 1-2 секунды до статуса `completed` или `failed`.

### Минимальный Retrofit-интерфейс

```kotlin
interface SafeCallApi {
    @FormUrlEncoded
    @POST("auth/token")
    suspend fun login(
        @Field("username") email: String,
        @Field("password") password: String
    ): Response<Unit>

    @Multipart
    @POST("api/predict/send_task")
    suspend fun uploadAudio(
        @Part file: MultipartBody.Part
    ): UploadResponse

    @GET("api/predict/tasks/{taskId}")
    suspend fun getTask(
        @Path("taskId") taskId: Long
    ): PredictionResponse
}
```

Рекомендуемый клиент для Android: Retrofit + OkHttp + `JavaNetCookieJar` или свой `CookieJar`, чтобы автоматически сохранять cookie `SAFECALL_API` после login.

## Стек

- Python 3.12, FastAPI, SQLModel, PostgreSQL 16
- PyTorch 2.6 CPU, torchaudio, transformers (XLSR-53)
- RabbitMQ 3.13, pika
- Nginx, Docker Compose
- python-jose (JWT), passlib (bcrypt)
- Jinja2 (templates), Bootstrap 5
- imageio-ffmpeg для MP3/OGG конвертации без системного ffmpeg в контейнере
- `HF_HUB_DISABLE_XET=1`, `HF_HUB_DOWNLOAD_TIMEOUT=120` для более стабильного скачивания XLSR-53 в Docker

## Лицензия

Проект распространяется под лицензией MIT. См. файл `LICENSE`.

## Структура проекта

```
DZ8/
├── docker-compose.yaml
├── .env / .env.example
├── LICENSE
├── README.md
├── app/                    # FastAPI + Auth + Templates
│   ├── api.py              # Entry point
│   ├── database/           # Settings, engine, init
│   ├── models/             # User, Prediction (SQLModel)
│   ├── routes/             # home, auth, predict
│   ├── auth/               # JWT, bcrypt, authenticate
│   ├── services/           # CRUD, RabbitMQ, auth helpers
│   ├── view/               # Jinja2 templates
│   ├── tests/              # pytest + SQLite
│   └── .env.example        # app settings example
├── ml_worker/              # ML inference worker
│   ├── predictor.py        # SafeCallPredictor (from ДЗ7)
│   ├── fusion.py           # ML + Context fusion
│   ├── rmq/                # RabbitMQ consumer
│   └── weights/
│       ├── best_xlsr_head.pth  # 1.1 MB (from ДЗ7 training)
│       └── xlsr_feature_extractor/preprocessor_config.json
├── nginx/nginx.conf
└── models/                 # optional local copy of model artifacts
```

## Чеклист ДЗ

- [x] 1. Доменная модель (User, Prediction, TaskStatus)
- [x] 2. Хранение данных (PostgreSQL + SQLModel ORM)
- [x] 3. REST-интерфейс (FastAPI: send_task, tasks, auth)
- [x] 4. Пользовательский интерфейс (Jinja2 + Bootstrap)
- [x] 5. Тесты (pytest: API + DB, SQLite + StaticPool)
- [x] 6. Docker-контейнер (docker-compose, 5 сервисов)
- [x] 7. Масштабирование воркеров (--scale ml_worker=N)
