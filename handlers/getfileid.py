# handlers/getfileid.py
"""
Модуль для получения идентификаторов файлов в Telegram.
Предназначен для технических целей - позволяет получать file_id
анимаций и других файлов для их дальнейшего использования в боте.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from utils import check_chat_and_execute

logger = logging.getLogger(__name__)

async def getfileid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /getfileid.
    Отправляет пользователю сообщение с просьбой отправить файл для получения его file_id.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    async def _getfileid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "Отправьте, пожалуйста, файл (например, GIF, фото или видео), "
                "для которого я должен получить его file_id."
            )
        )
    await check_chat_and_execute(update, context, _getfileid_command)

# Если ранее использовался catch_animation_fileid для анимаций, его можно оставить:
async def catch_animation_fileid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик для перехвата и отображения file_id анимаций (GIF).
    Вызывается автоматически при получении любой анимации в чате.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    if update.message.animation:
        file_id = update.message.animation.file_id
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"Поймал file_id:\n<code>{file_id}</code>\n\n"
            ),
            parse_mode="HTML"
        )
        logger.info(f"Поймали file_id: {file_id}")
