import os
import logging
import json
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from sheets import load_contacts
from search import find_contacts
import anthropic

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
ALLOWED_USERS = set(map(int, os.environ.get("ALLOWED_USERS", "").split(","))) if os.environ.get("ALLOWED_USERS") else set()

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Кэш контактов
_contacts_cache = None
_cache_time = 0

def get_contacts():
    import time
    global _contacts_cache, _cache_time
    if _contacts_cache is None or time.time() - _cache_time > 3600:
        logger.info("Загружаю контакты из Google Sheets...")
        _contacts_cache = load_contacts(SPREADSHEET_ID)
        _cache_time = time.time()
        logger.info(f"Загружено {len(_contacts_cache)} контактов")
    return _contacts_cache

def parse_query_with_claude(user_message: str) -> dict:
    response = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": f"""Извлеки параметры поиска из запроса пользователя и верни JSON.

Запрос: "{user_message}"

Верни ТОЛЬКО JSON без markdown:
{{
  "name": "имя или фамилия если упомянуты, иначе null",
  "company": "название компании если упомянуто, иначе null",
  "position": "должность если упомянута, иначе null",
  "email": "email если упомянут, иначе null",
  "phone": "телефон если упомянут, иначе null"
}}"""
        }]
    )
    try:
        return json.loads(response.content[0].text.strip())
    except Exception:
        return {}

def format_contact(c: dict, index: int) -> str:
    lines = [f"*{index}. {c.get('Имя','')} {c.get('Фамилия','')}*".strip()]
    if c.get('Компания') and c['Компания'] not in ['-', '']:
        lines.append(f"🏢 {c['Компания']}")
    if c.get('Должность') and c['Должность'] not in ['-', '']:
        lines.append(f"💼 {c['Должность']}")
    if c.get('Email'):
        lines.append(f"📧 {c['Email']}")
    if c.get('Телефон'):
        lines.append(f"📞 {c['Телефон']}")
    if c.get('Сейлз'):
        lines.append(f"👤 Сейлз: {c['Сейлз']}")
    if c.get('Источник'):
        lines.append(f"📅 {c['Источник']}")
    if c.get('Не звонить') == 'ДА':
        lines.append("⛔️ *НЕ ЗВОНИТЬ*")
    return "\n".join(lines)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ALLOWED_USERS and user_id not in ALLOWED_USERS:
        await update.message.reply_text("⛔️ У вас нет доступа к этому боту.")
        return
    contacts = get_contacts()
    await update.message.reply_text(
        f"👋 Привет! Я помогаю искать контакты из B2B базы Changellenge.\n"
        f"📊 В базе {len(contacts)} контактов.\n\n"
        "Просто напиши что ищешь, например:\n"
        "• *Найди контакты из компании Лента*\n"
        "• *Где работает Михаил Иванов*\n"
        "• *HR-директора из Газпрома*\n\n"
        "Команды:\n"
        "/start — это сообщение\n"
        "/reload — обновить базу",
        parse_mode="Markdown"
    )

async def reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ALLOWED_USERS and user_id not in ALLOWED_USERS:
        await update.message.reply_text("⛔️ У вас нет доступа.")
        return
    global _contacts_cache, _cache_time
    _contacts_cache = None
    _cache_time = 0
    await update.message.reply_text("🔄 Обновляю базу...")
    contacts = get_contacts()
    await update.message.reply_text(f"✅ Готово. Загружено {len(contacts)} контактов.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    if ALLOWED_USERS and user_id not in ALLOWED_USERS:
        await update.message.reply_text("⛔️ У вас нет доступа к этому боту.")
        return

    user_text = update.message.text.strip()
    logger.info(f"Запрос от @{username} ({user_id}): {user_text}")

    await update.message.reply_text("🔍 Ищу...")

    try:
        # Парсим запрос через Claude с таймаутом 10 сек
        params = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, parse_query_with_claude, user_text),
            timeout=10.0
        )
    except asyncio.TimeoutError:
        await update.message.reply_text("⏱ Claude API не ответил вовремя. Попробуй ещё раз.")
        return

    logger.info(f"Параметры поиска: {params}")

    if not any(v for v in params.values() if v):
        await update.message.reply_text(
            "Не смог понять запрос 🤔\n\nПопробуй:\n"
            "• *Найди контакты из Лента*\n"
            "• *Михаил Иванов*\n"
            "• *HR из Газпрома*",
            parse_mode="Markdown"
        )
        return

    contacts = get_contacts()
    results = find_contacts(contacts, params)

    if not results:
        await update.message.reply_text(
            f"😔 По запросу *\"{user_text}\"* ничего не найдено.\n\n"
            "Попробуй изменить запрос или проверь написание.",
            parse_mode="Markdown"
        )
        return

    total = len(results)
    show = results[:10]
    header = f"✅ Найдено: *{total}* контакт{'ов' if total != 1 else ''}:\n\n"
    cards = "\n\n---\n\n".join(format_contact(c, i+1) for i, c in enumerate(show))
    footer = f"\n\n_Показаны первые 10 из {total}. Уточни запрос для фильтрации._" if total > 10 else ""
    message = header + cards + footer

    if len(message) > 4000:
        await update.message.reply_text(header + f"Результатов много ({total}), отправляю по частям...", parse_mode="Markdown")
        for i, c in enumerate(show):
            await update.message.reply_text(format_contact(c, i+1), parse_mode="Markdown")
    else:
        await update.message.reply_text(message, parse_mode="Markdown")

async def post_init(app):
    """Загружаем базу при старте бота."""
    logger.info("Загружаю базу при старте...")
    try:
        get_contacts()
        logger.info("База загружена и готова!")
    except Exception as e:
        logger.error(f"Ошибка загрузки базы при старте: {e}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reload", reload))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
