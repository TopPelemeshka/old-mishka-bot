# handlers/roulette.py
"""
Модуль обработчика команды /roulette - интерактивная текстовая рулетка с выбором.
Реализует функциональность для выбора случайного варианта из списка,
предоставленного пользователем, с возможностью последовательного исключения вариантов.
"""
import random
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import ContextTypes
from utils import check_chat_and_execute
from state import ROULETTE_DATA

def format_roulette_list(roulette_dict: dict) -> str:
    """
    Форматирует список вариантов для отображения в сообщении.
    Зачеркивает уже удалённые варианты.
    
    Args:
        roulette_dict: Словарь с данными рулетки
        
    Returns:
        str: Отформатированный список вариантов с HTML-разметкой
    """
    original_list = roulette_dict["original_list"]
    removed_ids = roulette_dict["removed_list"]
    lines = []
    for item in original_list:
        if item["id"] in removed_ids:
            lines.append(f"<s>🔴 {item['value']}</s>")
        else:
            lines.append(f"🟢 {item['value']}")
    return "\n".join(lines)

def build_roulette_keyboard(roulette_dict: dict) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопками для взаимодействия с рулеткой.
    
    Args:
        roulette_dict: Словарь с данными рулетки
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками "Крутить" и "Начать заново"
    """
    current_list = roulette_dict["current_list"]
    if len(current_list) > 1:
        keyboard = [
            [
                InlineKeyboardButton("Крутить 🎰", callback_data="roulette|spin"),
                InlineKeyboardButton("Начать заново 🔁", callback_data="roulette|startover")
            ]
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton("Начать заново 🔁", callback_data="roulette|startover")
            ]
        ]
    return InlineKeyboardMarkup(keyboard)

async def roulette_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /roulette.
    Создает интерактивную рулетку с указанными пользователем вариантами.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    async def _roulette_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text  # Например: "/roulette Фильм1, Фильм2, Фильм1"
        _, _, text_after_command = text.partition(" ")

        if not text_after_command.strip():
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(
                    "Нужно указать варианты через запятую после /roulette.\n"
                    "Пример:\n/roulette Фильм1, Фильм2, Фильм1"
                )
            )
            return

        variants = [v.strip() for v in text_after_command.split(",") if v.strip()]
        if not variants:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Кажется, вы не указали корректные варианты. Попробуйте ещё раз."
            )
            return

        chat_id = update.effective_chat.id
        # Присваиваем каждому варианту уникальный id
        items = [{"id": i, "value": variant} for i, variant in enumerate(variants)]
        ROULETTE_DATA[chat_id] = {
            "original_list": items,
            "current_list": items[:],
            "removed_list": []  # Будем хранить id удалённых элементов
        }

        roulette_dict = ROULETTE_DATA[chat_id]
        text_list = format_roulette_list(roulette_dict)
        keyboard = build_roulette_keyboard(roulette_dict)

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"РОЛЯЯЯЕМ! 🎉\n\n{text_list}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    await check_chat_and_execute(update, context, _roulette_command)

async def roulette_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    chat_id = query.message.chat_id

    if chat_id not in ROULETTE_DATA:
        await query.edit_message_text(
            text="Нет активной рулетки. Сначала выполните /roulette."
        )
        return

    action = data.split("|")[1]
    roulette_dict = ROULETTE_DATA[chat_id]

    if action == "spin":
        if len(roulette_dict["current_list"]) > 1:
            # Выбираем случайный элемент из текущего списка
            removed_item = random.choice(roulette_dict["current_list"])
            roulette_dict["current_list"].remove(removed_item)
            roulette_dict["removed_list"].append(removed_item["id"])

            text_list = format_roulette_list(roulette_dict)
            if len(roulette_dict["current_list"]) == 1:
                winner = roulette_dict["current_list"][0]
                text_list += f"\n\nГОООООООООЛ! Победитель: <b>{winner['value']}</b> 🎊"

            keyboard = build_roulette_keyboard(roulette_dict)
            await query.edit_message_text(
                text=f"РОЛЯЯЯЕМ! 🎉\n\n{text_list}",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            text_list = format_roulette_list(roulette_dict)
            await query.edit_message_text(
                text=f"Рулетка уже закончена.\n\n{text_list}",
                parse_mode="HTML"
            )

    elif action == "startover":
        roulette_dict["current_list"] = roulette_dict["original_list"][:]
        roulette_dict["removed_list"] = []
        text_list = format_roulette_list(roulette_dict)
        keyboard = build_roulette_keyboard(roulette_dict)
        await query.edit_message_text(
            text=f"РОЛЯЯЯЕМ! 🎉\n\n{text_list}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
