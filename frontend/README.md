# heat_ml frontend

Одностраничное приложение на React + Vite для работы с API (`/api`).

## Стэк
- React 18 + TypeScript
- React Router 6
- TanStack Query для запросов
- Axios

## Установка
```bash
cd frontend
npm install
```

## Режим разработки
```bash
npm run dev
```
Откроется `http://localhost:5173`, запросы на `/api` проксируются на `http://localhost:8000` (настроено в `vite.config.ts`).

## Продакшен-сборка
```bash
npm run build
npm run preview
```

## Структура
- `src/routes` — конфиг роутов и защита по токену
- `src/context/AuthContext.tsx` — хранит access / refresh токены
- `src/pages` — экраны (Datasets, Forecasts, Reports, Login)
- `src/lib/api.ts` — обёртка над Axios + набор методов API
- `src/components` — Shell / Sidebar / TopBar

## Интеграция
Готовую сборку (`dist/`) можно отдавать через любой фронтенд-сервер или nginx, проксируя `/api` на backend. Для SSR/дизайна — подключайте Chakra/MUI либо Tailwind. EOF
