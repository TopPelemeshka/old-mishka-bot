# handlers/chatid.py
import logging
from telegram import Update
from telegram.ext import ContextTypes
from utils import check_chat_and_execute

logger = logging.getLogger(__name__)

async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async def _chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Chat ID: {chat_id}"
        )
        logger.info(f"Chat ID: {chat_id}")
    await check_chat_and_execute(update, context, _chatid_command)
    # Нужно заменить строчку, чтобы отключить проверку для chatid
    #await _chatid_command(update, context) 
