# Heat Forecast

Веб-приложение для прогнозирования тепловых нагрузок с помощью нейронных сетей.

## Что это?

Учебный проект системы прогнозирования потребления тепла. Загружаете исторические данные, система обучает модель и строит прогноз.

## Стек

**Backend:** FastAPI, PostgreSQL, TimescaleDB, Redis Queue, TensorFlow, SQLAlchemy

**Frontend:** React, TypeScript, TanStack Query, Vite

## Запуск

```bash
docker-compose up -d
```

- Frontend: http://localhost:5173
- API: http://localhost:8000/docs

## Тестовые данные

Примеры CSV файлов для загрузки находятся в папке `samples for testing/`

## Структура

```
src/
├── users/      - регистрация, JWT авторизация
├── files/      - загрузка данных
├── forecasts/  - обучение моделей, прогнозы
└── reports/    - отчеты по качеству данных
```

## Как работает

1. Регистрация/логин
2. Загрузка CSV с историческими данными
3. Создание прогноза (модель обучается в фоне)
4. Просмотр результатов и метрик

## API

```
POST /users/register, /users/login
POST /files/upload
GET  /files/batches
POST /forecasts
GET  /forecasts, /forecasts/{id}
GET  /reports/quality/{batch_id}
```

Документация: http://localhost:8000/docs

## Docker сервисы

`app`, `worker-files`, `worker-forecasts`, `frontend`, `db`, `timescaledb`, `redis`, `migrate`
