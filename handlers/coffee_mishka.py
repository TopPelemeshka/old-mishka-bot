# handlers/coffee_mishka.py
"""
Модуль обработчиков для развлекательных команд бота.
Содержит обработчики для команд:
- /coffee - Отправляет изображение кофе (с пасхалкой при частом вызове)
- /mishka - Отправляет изображение мишки (аватар бота)
- /durka - Отправляет юмористическое изображение
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from utils import check_chat_and_execute
import time  # для работы с отметками времени

logger = logging.getLogger(__name__)

# Глобальный список для хранения времени вызовов команды /coffee
coffee_invocations = []

async def coffee_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /coffee - отправляет изображение кофе.
    
    Имеет пасхалку: если команду вызвать несколько раз за короткий 
    промежуток времени (10 секунд), отправляет специальное изображение.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    global coffee_invocations
    now = time.time()
    # Оставляем в списке только вызовы за последние 10 секунд
    coffee_invocations = [t for t in coffee_invocations if now - t < 10]
    coffee_invocations.append(now)

    # Если накопилось хотя бы 2 вызова за 10 секунд — отправляем специальную картинку
    if len(coffee_invocations) >= 2:
        # Сбрасываем список, чтобы не сработать несколько раз подряд
        coffee_invocations = []
        with open("pictures/alcgaimer.jpg", "rb") as sc:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=sc,
            )
        return

    # Если условие не выполнено — отправляем обычное изображение кофе
    async def _coffee_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        with open("pictures/coffee.jpg", "rb") as cf:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=cf,
            )
    await check_chat_and_execute(update, context, _coffee_command)

async def mishka_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /mishka - отправляет изображение мишки (аватар бота).
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    async def _mishka_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        with open("pictures/mishka.jpg", "rb") as mf:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=mf,
                caption="Это я! 🐻"
            )
    await check_chat_and_execute(update, context, _mishka_command)

async def durka_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /durka - отправляет юмористическое изображение.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    async def _durka_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        with open("pictures/durka.jpg", "rb") as cf:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=cf,
            )
    await check_chat_and_execute(update, context, _durka_command)