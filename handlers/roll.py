# handlers/roll.py
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
    async def _roll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        now = time.time()
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

        msg = await context.bot.send_animation(
            chat_id=update.effective_chat.id,
            animation=DICE_GIF_ID,
            caption="Кубик катится... 🎲"
        )

        await asyncio.sleep(1)

        result = random.randint(1, max_number)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "Перебросить (0)",
                callback_data=f"roll|{max_number}|0"
            )]
        ])

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
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    now = time.time()
    if user_id in last_roll_time:
        diff = now - last_roll_time[user_id]
        if diff < COOLDOWN:
            await query.answer(
                text=f"Слишком быстро! Подождите {COOLDOWN - diff:.1f} секунд.",
                show_alert=True
            )
            return
    last_roll_time[user_id] = now

    data = query.data
    prefix, max_num_str, reroll_count_str = data.split("|")
    max_number = int(max_num_str)
    reroll_count = int(reroll_count_str)
    new_reroll_count = reroll_count + 1

    if not DICE_GIF_ID:
        await query.answer("Нет file_id! Сначала сделайте /getfileid.")
        return

    media_animation = InputMediaAnimation(
        media=DICE_GIF_ID,
        caption="Кубик катится... 🎲"
    )
    await query.edit_message_media(
        media=media_animation,
        reply_markup=None
    )

    await asyncio.sleep(1)

    result = random.randint(1, max_number)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"Перебросить ({new_reroll_count})",
            callback_data=f"roll|{max_number}|{new_reroll_count}"
        )]
    ])

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
