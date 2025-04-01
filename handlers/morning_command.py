"""
Модуль обработчика команды /morning.
Отправляет пользователю пожелания доброго утра из заранее подготовленного списка.
Система запоминает последнее отправленное пожелание и при следующем запросе 
показывает следующее в списке, обеспечивая ротацию пожеланий.
"""
import os
import json
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Путь к файлу с пожеланиями доброго утра (каждое пожелание с новой строки)
MORNING_WISHES_FILE = "phrases/morning_wishes.txt"
# Файл для хранения текущего индекса пожелания
MORNING_INDEX_FILE = "state_data/morning_index.json"

def load_morning_wishes() -> list[str]:
    """Считываем пожелания из файла. Пустые строки отбрасываются."""
    if not os.path.exists(MORNING_WISHES_FILE):
        return []
    with open(MORNING_WISHES_FILE, "r", encoding="utf-8") as f:
        wishes = [line.strip() for line in f if line.strip()]
    return wishes

def load_morning_index() -> int:
    """Загружаем текущий индекс из файла. Если файла нет — возвращаем 0."""
    if not os.path.exists(MORNING_INDEX_FILE):
        return 0
    try:
        with open(MORNING_INDEX_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "morning_index" in data:
                return data["morning_index"]
    except Exception as e:
        logger.error("Ошибка чтения файла индекса утра: %s", e)
    return 0

def save_morning_index(index: int):
    """Сохраняем новый индекс в файл."""
    try:
        with open(MORNING_INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump({"morning_index": index}, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error("Ошибка записи файла индекса утра: %s", e)

async def morning_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /morning.
    Отправляет пользователю пожелание доброго утра, выбирая следующее 
    из списка относительно предыдущего запроса.
    
    Функционал:
    1. Загружает список пожеланий из файла
    2. Определяет текущий индекс в списке пожеланий
    3. Отправляет очередное пожелание пользователю
    4. Обновляет индекс для следующего запроса
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    wishes = load_morning_wishes()
    if not wishes:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Пока нет пожеланий доброго утра. Попробуйте позже."
        )
        return

    # Загружаем текущий индекс
    index = load_morning_index()
    # Выбираем пожелание по индексу (с переходом к началу при достижении конца списка)
    wish = wishes[index % len(wishes)]
    # Отправляем пожелание
    await context.bot.send_message(chat_id=update.effective_chat.id, text=wish)
    # Увеличиваем индекс и сохраняем его
    index = (index + 1) % len(wishes)
    save_morning_index(index) 