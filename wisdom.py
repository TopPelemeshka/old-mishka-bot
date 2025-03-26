# wisdom.py

import os
import datetime
import json
import random
from telegram import Update
from telegram.ext import ContextTypes
from config import POST_CHAT_ID, MATERIALS_DIR
import state  # если хотите проверять, включена ли публикация

WISDOM_FILE = os.path.join(MATERIALS_DIR, "wisdom.json")

def random_time_in_range(start: datetime.time, end: datetime.time) -> datetime.time:
    start_seconds = start.hour * 3600 + start.minute * 60 + start.second
    end_seconds = end.hour * 3600 + end.minute * 60 + end.second
    rand_sec = random.randint(start_seconds, end_seconds)
    hh = rand_sec // 3600
    mm = (rand_sec % 3600) // 60
    ss = rand_sec % 60
    return datetime.time(hour=hh, minute=mm, second=ss)

def load_wisdoms() -> list[str]:
    """Считываем список мудростей из файла JSON (массив строк)."""
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
    """Перезаписываем wisdom.json."""
    with open(WISDOM_FILE, "w", encoding="utf-8") as f:
        json.dump(wisdoms, f, ensure_ascii=False, indent=4)

def get_random_wisdom() -> str | None:
    """
    Берём случайную строку-мудрость из массива, удаляем её из файла.
    Возвращает None, если мудростей нет.
    """
    ws = load_wisdoms()
    if not ws:
        return None
    w = random.choice(ws)
    ws.remove(w)
    save_wisdoms(ws)
    return w


async def wisdom_post_callback(context: ContextTypes.DEFAULT_TYPE):
    """
    Публикация «Мудрости дня» — 1 раз в сутки.
    """
    # Если хотите возможность отключать, проверяем state:
    # if not state.some_wisdom_enabled:
    #    return

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
    state.wisdom_enabled = True
    # Сохраняем текущее состояние вместе с другими флагами
    state.save_state(state.autopost_enabled, state.quiz_enabled, state.wisdom_enabled)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Мудрость дня включена!"
    )

async def stop_wisdom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state.wisdom_enabled = False
    state.save_state(state.autopost_enabled, state.quiz_enabled, state.wisdom_enabled)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Мудрость дня отключена!"
    )