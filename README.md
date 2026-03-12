# Changellenge BizDev Bot

Telegram-бот для поиска B2B контактов по базе вебинаров.

## Структура файлов

```
bot/
├── bot.py              # Основной файл бота
├── sheets.py           # Загрузка контактов из Google Sheets
├── search.py           # Логика поиска
├── credentials.json    # Ключ сервисного аккаунта Google (не коммить в git!)
├── requirements.txt    # Зависимости
├── Procfile            # Для Railway
└── .env.example        # Шаблон переменных окружения
```

---

## Шаг 1 — Создай бота в Telegram

1. Напиши [@BotFather](https://t.me/BotFather) в Telegram
2. Отправь `/newbot`
3. Придумай имя (например: `Changellenge BizDev`)
4. Придумай username (например: `changellenge_bizdev_bot`)
5. Скопируй **токен** — он понадобится на шаге деплоя

---

## Шаг 2 — Узнай Telegram user_id участников команды

Каждый, кто должен иметь доступ к боту, должен написать [@userinfobot](https://t.me/userinfobot) — он ответит их числовым ID.

Собери ID через запятую: `123456789,987654321,111222333`

---

## Шаг 3 — Получи Anthropic API ключ

1. Зайди на [console.anthropic.com](https://console.anthropic.com)
2. API Keys → Create Key
3. Скопируй ключ

---

## Шаг 4 — Деплой на Railway

### 4.1 Создай аккаунт
Зайди на [railway.app](https://railway.app) и войди через GitHub.

### 4.2 Создай новый проект
- "New Project" → "Deploy from GitHub repo"
- Залей папку `bot/` как репозиторий на GitHub (или используй Railway CLI)

**Через Railway CLI (проще):**
```bash
# Установи Railway CLI
npm install -g @railway/cli

# Войди
railway login

# Из папки bot/
cd bot
railway init
railway up
```

### 4.3 Добавь переменные окружения
В Railway → твой проект → Variables, добавь:

| Переменная | Значение |
|-----------|---------|
| `TELEGRAM_TOKEN` | токен от BotFather |
| `ANTHROPIC_API_KEY` | ключ от Anthropic |
| `SPREADSHEET_ID` | `1_rCq5ZB7Xr9cwwAhUMrhpJHIVnFY0Eoj` |
| `ALLOWED_USERS` | ID через запятую: `123456789,987654321` |
| `GOOGLE_CREDENTIALS_PATH` | `credentials.json` |

### 4.4 Загрузи credentials.json
Файл `credentials.json` (ключ сервисного аккаунта Google) нельзя хранить в git.

**Вариант A — через Railway Volumes (рекомендуется):**
```bash
# Загрузи файл через Railway CLI
railway run --service <service-name> -- sh -c "cat > credentials.json" < credentials.json
```

**Вариант B — через переменную окружения:**
1. Открой `credentials.json`, скопируй всё содержимое
2. В Railway добавь переменную `GOOGLE_CREDENTIALS_JSON` со значением — полный JSON одной строкой
3. В `sheets.py` замени загрузку credentials:
```python
import os, json
from google.oauth2 import service_account

creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
if creds_json:
    creds_info = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
else:
    creds = service_account.Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
```

---

## Использование бота

После деплоя найди бота в Telegram по username и напиши:

```
/start
```

Примеры запросов:
- `Найди контакты из компании Лента`
- `Где работает Михаил Иванов`
- `HR-директора из Газпрома`
- `Покажи контакт ivanov@mail.ru`
- `Рекрутеры из банков`

### Команды:
- `/start` — приветствие и инструкция
- `/reload` — обновить базу из Google Sheets (если добавили новые контакты)

---

## Обновление базы контактов

База кэшируется и автоматически обновляется раз в час.  
Для ручного обновления — напиши `/reload` в боте.

Чтобы добавить новые контакты — просто добавь строки в Google Sheets.  
Формат колонок: `Имя | Фамилия | Email | Телефон | Компания | Должность | Сейлз | Дата | Источник | Запрос | Не звонить`
