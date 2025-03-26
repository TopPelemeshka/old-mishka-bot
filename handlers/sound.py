import os
import json
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

# Папка, где хранятся звуковые файлы
SOUNDS_DIR = "sound_panel"
# Конфигурационный файл с отображаемыми названиями
SOUND_CONFIG_FILE = "sound_config.json"

SOUND_MAPPING = {}

logger = logging.getLogger(__name__)

def load_sound_config() -> dict:
    """
    Загружает конфигурацию звуков из SOUND_CONFIG_FILE.
    Ожидается формат: { "filename.mp3": "Отображаемое название", ... }
    """
    try:
        with open(SOUND_CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error("Ошибка загрузки конфигурации звуков: %s", e)
        return {}

async def sound_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = load_sound_config()
    if not config:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Конфигурация звуков не найдена.")
        return

    global SOUND_MAPPING
    SOUND_MAPPING = {}  # Обнуляем старое сопоставление
    keyboard = []
    row = []
    # Используем счетчик для генерации короткого ID
    for idx, (file_name, display_name) in enumerate(config.items(), start=1):
        short_id = f"sound:{idx}"  # например, "sound:1", "sound:2", ...
        SOUND_MAPPING[short_id] = file_name
        row.append(InlineKeyboardButton(display_name, callback_data=short_id))
        # Если в ряду 2 кнопки, добавляем ряд в клавиатуру и обнуляем ряд
        if len(row) == 2:
            keyboard.append(row)
            row = []
    # Если остались кнопки в ряду, добавляем их тоже
    if row:
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Выберите звук:",
        reply_markup=reply_markup
    )



async def sound_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    short_id = query.data  # теперь это, например, "sound:1"
    global SOUND_MAPPING
    file_name = SOUND_MAPPING.get(short_id)
    if not file_name:
        await query.edit_message_text("Аудиофайл не найден.")
        return

    file_path = os.path.join(SOUNDS_DIR, file_name)
    if not os.path.exists(file_path):
        await query.edit_message_text("Аудиофайл не найден.")
        return

    try:
        with open(file_path, "rb") as audio_file:
            await context.bot.send_audio(
                chat_id=update.effective_chat.id,
                audio=audio_file
            )
        await query.delete_message()
    except Exception as e:
        logger.error("Ошибка при отправке аудиофайла %s: %s", file_name, e)
        await query.edit_message_text("Ошибка при воспроизведении звука.")

