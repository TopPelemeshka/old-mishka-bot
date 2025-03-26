# handlers/all.py
from telegram import Update
from telegram.ext import ContextTypes
from utils import check_chat_and_execute
from config import MANUAL_USERNAMES
import logging

logger = logging.getLogger(__name__)

async def all_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async def _all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        
        # Собираем список username для финального вывода
        final_usernames = []

        try:
            admins = await context.bot.getChatAdministrators(chat_id)
            if admins:
                for admin in admins:
                    user = admin.user
                    if user.username:
                        final_usernames.append(f"@{user.username}")
                    else:
                        final_usernames.append(f'<a href="tg://user?id={user.id}">{user.first_name}</a>')
        except Exception as e:
            logger.warning(f"Не удалось получить список админов: {e}")
            final_usernames = MANUAL_USERNAMES

        if not final_usernames:
            final_usernames = MANUAL_USERNAMES

        text_mentions = " ".join(final_usernames)

        await context.bot.send_message(
            chat_id=chat_id,
            text=text_mentions,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    await check_chat_and_execute(update, context, _all_command)
