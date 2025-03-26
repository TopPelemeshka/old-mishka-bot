import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import POST_CHAT_ID  # Или, если нужен другой чат, определите другой ID

async def technical_work_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /technical_work — сообщает о начале технических работ.
    Отправляет в указанный чат картинку technical_work.jpg и забавный текст.
    """
    try:
        with open("pictures/technical_work.jpg", "rb") as photo:
            await context.bot.send_photo(
                chat_id=POST_CHAT_ID,
                photo=photo,
                caption="⚙️ Ведутся технические работы, бот будет недоступен.\n\nГотовьтесь к обновлениям, отдыхайте, пока можете! 😄"
            )
    except Exception as e:
        logging.error(f"Ошибка отправки technical_work.jpg: {e}")
        await context.bot.send_message(
            chat_id=POST_CHAT_ID,
            text="Ошибка: не удалось отправить сообщение о технических работах."
        )
