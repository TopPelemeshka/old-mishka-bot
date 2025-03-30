# handlers/roll.py
"""
Модуль для обработки команды /roll - бросок виртуального кубика.
Поддерживает кубики с любым количеством граней и возможность перебросить результат.
"""
import random
import time
import asyncio

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaAnimation,
    InputMediaPhoto
)
from telegram.ext import ContextTypes
from utils import check_chat_and_execute
from config import DICE_GIF_ID, COOLDOWN
from state import last_roll_time

async def roll_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /roll - бросок виртуального кубика.
    Поддерживает указание максимального числа через аргумент, например "/roll 20".
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика с аргументами команды
    """
    async def _roll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        now = time.time()
        # Проверка кулдауна между бросками
        if user_id in last_roll_time:
            diff = now - last_roll_time[user_id]
            if diff < COOLDOWN:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Слишком быстрый бросок! Подождите {COOLDOWN - diff:.1f} секунд."
                )
                return
        last_roll_time[user_id] = now

        args = context.args
        try:
            # Определяем максимальное число на кубике (по умолчанию 6)
            max_number = int(args[0]) if args else 6
            if max_number < 1:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Число должно быть больше 0!"
                )
                return
        except ValueError:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Некорректное число. Пример: /roll 20"
            )
            return

        if not DICE_GIF_ID:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="У меня пока нет file_id для GIF! Сначала сделайте /getfileid"
            )
            return

        # Отправляем анимацию броска кубика
        msg = await context.bot.send_animation(
            chat_id=update.effective_chat.id,
            animation=DICE_GIF_ID,
            caption="Кубик катится... 🎲"
        )

        # Имитация задержки при броске
        await asyncio.sleep(1)

        # Генерация случайного результата
        result = random.randint(1, max_number)
        # Создаем кнопку для переброса
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "Перебросить (0)",
                callback_data=f"roll|{max_number}|0"
            )]
        ])

        # Обновляем сообщение с результатом броска
        with open("pictures/dice_result.png", "rb") as image_file:
            new_caption = (
                f"🎲 Результат: {result} (из {max_number})\n"
                f"🔄 Количество перебросов: 0"
            )
            media = InputMediaPhoto(image_file, caption=new_caption)
            await context.bot.edit_message_media(
                chat_id=msg.chat_id,
                message_id=msg.message_id,
                media=media,
                reply_markup=keyboard
            )
    await check_chat_and_execute(update, context, _roll_command)

async def roll_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик для кнопки переброса кубика.
    Обновляет сообщение с новым случайным результатом и увеличивает счетчик перебросов.
    
    Args:
        update: Объект обновления от Telegram (содержит callback_query)
        context: Контекст обработчика
    """
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    now = time.time()
    # Проверка кулдауна между перебросами
    if user_id in last_roll_time:
        diff = now - last_roll_time[user_id]
        if diff < COOLDOWN:
            await query.answer(
                text=f"Слишком быстро! Подождите {COOLDOWN - diff:.1f} секунд.",
                show_alert=True
            )
            return
    last_roll_time[user_id] = now

    # Разбор данных из callback_query
    data = query.data
    prefix, max_num_str, reroll_count_str = data.split("|")
    max_number = int(max_num_str)
    reroll_count = int(reroll_count_str)
    new_reroll_count = reroll_count + 1

    if not DICE_GIF_ID:
        await query.answer("Нет file_id! Сначала сделайте /getfileid.")
        return

    # Обновляем сообщение анимацией броска
    media_animation = InputMediaAnimation(
        media=DICE_GIF_ID,
        caption="Кубик катится... 🎲"
    )
    await query.edit_message_media(
        media=media_animation,
        reply_markup=None
    )

    # Имитация задержки при броске
    await asyncio.sleep(1)

    # Генерация нового случайного результата
    result = random.randint(1, max_number)
    # Обновляем кнопку с новым счетчиком перебросов
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"Перебросить ({new_reroll_count})",
            callback_data=f"roll|{max_number}|{new_reroll_count}"
        )]
    ])

    # Обновляем сообщение с новым результатом
    with open("pictures/dice_result.png", "rb") as image_file:
        new_text = (
            f"🎲 Результат: {result} (из {max_number})\n"
            f"🔄 Количество перебросов: {new_reroll_count}"
        )
        media_photo = InputMediaPhoto(image_file, caption=new_text)
        await query.edit_message_media(
            media=media_photo,
            reply_markup=keyboard
        )
