import random
import logging
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from balance import get_balance, update_balance

# Список символов для слотов
SLOT_SYMBOLS = ["🍒", "🍋", "🔔", "🍀", "💎", "7️⃣"]

async def handle_slots_callback(query, context):
    """
    Предлагаем выбрать ставку для слотов,
    вычисляя фиксированные значения как 1%, 5% и 10% от баланса пользователя.
    """
    await query.answer()
    user_id = query.from_user.id
    balance = get_balance(user_id)
    
    # Вычисляем ставки; минимальное значение – 1 монета
    bet_1 = max(int(balance * 0.01), 1)
    bet_5 = max(int(balance * 0.05), 1)
    bet_10 = max(int(balance * 0.1), 1)
    
    # Сохраняем ставку по умолчанию (1%)
    context.user_data['slots_bet'] = bet_1

    keyboard = [
        [InlineKeyboardButton(f"Ставка 1% ({bet_1} монет)", callback_data=f"slots_bet:{bet_1}")],
        [InlineKeyboardButton(f"Ставка 5% ({bet_5} монет)", callback_data=f"slots_bet:{bet_5}")],
        [InlineKeyboardButton(f"Ставка 10% ({bet_10} монет)", callback_data=f"slots_bet:{bet_10}")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    text = "Выберите ставку для слотов:"
    await query.edit_message_text(text, reply_markup=markup)

async def handle_slots_bet_callback(update, context):
    """
    Обрабатываем выбор ставки или повтор игры.
    Списываем ставку, запускаем игру в слоты и показываем результат с меню дальнейших действий.
    """
    query = update.callback_query
    await query.answer()
    
    # Извлекаем выбранную ставку из callback данных вида "slots_bet:XX"
    try:
        _, bet_str = query.data.split(":")
        bet = int(bet_str)
    except ValueError:
        logging.error("Неверный формат данных ставки.")
        return

    user_id = query.from_user.id
    balance_now = get_balance(user_id)
    
    if balance_now < bet:
        await query.edit_message_text("Недостаточно монет для этой ставки!")
        return

    # Сохраняем текущую ставку
    context.user_data['slots_bet'] = bet

    # Списываем ставку
    update_balance(user_id, -bet)

    # Генерируем результат игры (3 случайных символа)
    reel = [random.choice(SLOT_SYMBOLS) for _ in range(3)]
    result_text = " | ".join(reel)

    # Определяем выигрыш:
    if reel[0] == reel[1] == reel[2]:
        win = bet * 5
        update_balance(user_id, win)
        result_message = f"🎰 {result_text} 🎰\n\nДжекпот! Вы выиграли {win} монет!"
    elif reel[0] == reel[1] or reel[1] == reel[2] or reel[0] == reel[2]:
        win = bet * 2
        update_balance(user_id, win)
        result_message = f"🎰 {result_text} 🎰\n\nДве одинаковые! Вы выиграли {win} монет!"
    else:
        result_message = f"🎰 {result_text} 🎰\n\nНичего не совпало. Вы проиграли {bet} монет."

    new_balance = get_balance(user_id)
    result_message += f"\n\n💳 Ваш баланс: {new_balance} монет."

    # Клавиатура с кнопками: повторить игру и вернуться в меню казино
    keyboard = [
        [InlineKeyboardButton("🔄 Сыграть ещё раз", callback_data=f"slots_bet:{bet}")],
        [InlineKeyboardButton("🏠 В меню казино", callback_data="casino:menu")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.edit_message_text(result_message, reply_markup=markup)
    except Exception as e:
        logging.error(f"Ошибка при обновлении сообщения слотов: {e}")
