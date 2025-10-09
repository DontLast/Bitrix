## BitrixCorp — FastAPI + Bitrix24 вебхук

### Запуск на Windows (PowerShell)
1. Создайте и активируйте виртуальное окружение:
   ```powershell
   python -m venv .venv
   .\\.venv\\Scripts\\Activate.ps1
   ```
2. Установите зависимости:
   ```powershell
   pip install -r requirements.txt
   ```
3. Заполните переменные окружения (необязательно):
   - Скопируйте `.env.example` в `.env` и при необходимости задайте:
     - `BITRIX_WEBHOOK_SECRET` — секрет для вашего входящего маршрута.
     - `BITRIX_WEBHOOK_URL` — URL вебхука Bitrix24 для REST вызовов (например, `https://b24-25ltxt.bitrix24.ru/rest/1/0lkqo0totvtp3btp/profile.json`).

4. Запустите сервер разработки:
   ```powershell
   uvicorn app.main:app --reload
   ```

### Использование
- HTML-страница: `GET /` — выводит список компаний и контактов в двух таблицах.
- Локальная генерация в БД: `POST /bitrix/webhook?secret=...` — генерирует 100 компаний и 100 контактов в SQLite и случайно привязывает контакты к компаниям.
- Создание в Bitrix24 через REST: `POST /bitrix/webhook/push-to-bitrix?secret=...&count=100` — создаёт компании и контакты напрямую в вашем портале Bitrix24. Требуется `BITRIX_WEBHOOK_URL`.

### Где вставить ссылку на вебхук Bitrix24
- Откройте файл `.env` и добавьте строку с вашим вебхуком:
  ```
  BITRIX_WEBHOOK_URL=https://b24-25ltxt.bitrix24.ru/rest/1/0lkqo0totvtp3btp/profile.json
  ```
- Клиент автоматически нормализует URL, даже если он оканчивается на `.json`.
- Либо передайте URL программно при создании клиента `BitrixClient(base_url=...)`.

### Структура
- `app/main.py` — точка входа FastAPI и маршруты.
- `app/database.py` — подключение к SQLite и сессии.
- `app/models.py` — модели SQLAlchemy: Company и Contact.
- `app/routers/webhook.py` — обработчики вебхуков (локальная генерация и push в Bitrix24).
- `app/bitrix_client.py` — простой REST клиент Bitrix24.
- `app/templates/index.html` — HTML с таблицами компаний и контактов.

### Хранилище данных
- SQLite файл `data.db` создаётся автоматически в корне проекта.
