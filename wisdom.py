# wisdom.py
"""
Модуль для публикации "Мудрости дня" в Telegram-чате.
Обеспечивает:
- Загрузку и сохранение списка мудрых фраз
- Случайный выбор фраз без повторений
- Ежедневную публикацию мудрости по расписанию
- Возможность включения/отключения функции
"""

import os
import datetime
import json
import random
from telegram import Update
from telegram.ext import ContextTypes
from config import POST_CHAT_ID, MATERIALS_DIR
from utils import random_time_in_range
import state  # используется для проверки включена ли публикация

WISDOM_FILE = os.path.join(MATERIALS_DIR, "wisdom.json")

def load_wisdoms() -> list[str]:
    """
    Загружает список мудрых фраз из JSON-файла.
    
    Returns:
        list[str]: Список строк с мудрыми фразами или пустой список,
                  если файл не существует или некорректен
    """
    if not os.path.exists(WISDOM_FILE):
        return []
    try:
        with open(WISDOM_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                # тут предполагаем, что это список строк
                return data
    except:
        pass
    return []

def save_wisdoms(wisdoms: list[str]):
    """
    Сохраняет список мудрых фраз в JSON-файл.
    
    Args:
        wisdoms: Список строк для сохранения
    """
    with open(WISDOM_FILE, "w", encoding="utf-8") as f:
        json.dump(wisdoms, f, ensure_ascii=False, indent=4)

def count_wisdoms() -> int:
    """
    Подсчитывает количество оставшихся мудрых фраз в файле.
    
    Returns:
        int: Количество мудрых фраз или 0, если файла нет или произошла ошибка
    """
    try:
        wisdoms = load_wisdoms()
        return len(wisdoms)
    except Exception:
        return 0

def get_random_wisdom() -> str | None:
    """
    Выбирает случайную мудрую фразу из списка и удаляет её,
    чтобы избежать повторений.
    
    Returns:
        str|None: Случайная мудрая фраза или None, если список пуст
    """
    ws = load_wisdoms()
    if not ws:
        return None
    
    # Выбираем случайную мудрость
    w = random.choice(ws)
    
    # Удаляем выбранную мудрость из списка
    ws.remove(w)
    
    # Сохраняем обновлённый список
    save_wisdoms(ws)
    
    return w


async def wisdom_post_callback(context: ContextTypes.DEFAULT_TYPE):
    """
    Callback-функция для ежедневной публикации "Мудрости дня".
    Вызывается планировщиком задач по расписанию.
    
    Args:
        context: Контекст от планировщика задач Telegram
    """
    # Проверяем, включена ли функция публикации мудрости
    if not state.wisdom_enabled:
        return

    text = get_random_wisdom()
    if not text:
        await context.bot.send_message(
            chat_id=POST_CHAT_ID,
            text="Мудрости дня закончились 😢"
        )
        return

    await context.bot.send_message(
        chat_id=POST_CHAT_ID,
        text=f"🦉 Мудрость дня:\n\n{text}"
    )

async def start_wisdom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды для включения функции "Мудрость дня".
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    state.wisdom_enabled = True
    # Сохраняем текущее состояние вместе с другими флагами
    state.save_state(state.autopost_enabled, state.quiz_enabled, state.wisdom_enabled)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Мудрость дня включена!"
    )

async def stop_wisdom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды для отключения функции "Мудрость дня".
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    state.wisdom_enabled = False
    state.save_state(state.autopost_enabled, state.quiz_enabled, state.wisdom_enabled)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Мудрость дня отключена!"
    )