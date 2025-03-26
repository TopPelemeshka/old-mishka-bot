# utils.py
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import ALLOWED_CHAT_IDS

logger = logging.getLogger(__name__)

def is_allowed_chat(chat_id: int) -> bool:
    return chat_id in ALLOWED_CHAT_IDS

async def check_chat_and_execute(update: Update, context: ContextTypes.DEFAULT_TYPE, handler_func):
    chat_id = update.effective_chat.id
    if not is_allowed_chat(chat_id):
        await context.bot.send_message(chat_id=chat_id, text="Извините, я могу работать только в разрешённых группах.")
        try:
            await context.bot.leave_chat(chat_id)
        except Exception as e:
            logger.error(f"Ошибка при попытке покинуть чат {chat_id}: {e}")
        return
    await handler_func(update, context)
