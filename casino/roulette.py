from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import asyncio
import random
from balance import get_balance, update_balance
from casino.roulette_utils import get_roulette_result
from telegram.error import TimedOut
import time
import json
import os

def load_file_ids():
    """Загрузка ID файлов из конфигурации"""
    config_path = os.path.join('config', 'file_ids.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

async def safe_delete_message(gif_message, retries=3, delay=1):
    """Функция для безопасного удаления сообщения с обработкой тайм-аута."""
    for _ in range(retries):
        try:
            await gif_message.delete()
            return  # Сообщение успешно удалено
        except TimedOut:
            print("Ошибка тайм-аута при удалении сообщения. Попробую снова...")
            await asyncio.sleep(delay)
    print("Не удалось удалить сообщение после нескольких попыток.")

async def handle_roulette_bet_callback(query, context: ContextTypes.DEFAULT_TYPE, bet_type: str):
    bet_amount = int(query.data.split(":")[-1])  
    user_id = query.from_user.id
    bal = get_balance(user_id)

    if bal < bet_amount:
        await query.answer("💸 У вас недостаточно средств для ставки.", show_alert=True)
        return

    update_balance(user_id, -bet_amount)
    result = get_roulette_result()

    # Загружаем ID гифок из конфига
    file_ids = load_file_ids()
    gif_ids = file_ids['animations']['roulette']

    if result == 'black':
        gif_id = random.choice(gif_ids['black'])
    elif result == 'red':
        gif_id = random.choice(gif_ids['red'])
    else:
        gif_id = random.choice(gif_ids['zero'])

    try:
        gif_message = await query.message.chat.send_animation(gif_id)
    except Exception as e:
        print(f"Ошибка при отправке гифки: {e}")
        return

    await asyncio.sleep(5.5)
    await safe_delete_message(gif_message)

    win = result == bet_type

    if win:
        base_winnings = 100 if bet_type != 'zero' else 1800
        winnings = int(base_winnings * (bet_amount / 50))
        if bet_type == 'zero':
            winnings = int(winnings)
        update_balance(user_id, winnings)
        message = f"🎉 *Поздравляем!* Вы выиграли {winnings} монет! 🎉"
    else:
        result_emoji = "⚫" if result == "black" else "🔴" if result == "red" else "🟢"
        message = f"😔 *Вы проиграли.* Выпало: {result_emoji}"

    new_balance = get_balance(user_id)
    message += f"\n\n💰 *Ваш текущий баланс*: {new_balance} монет."

    keyboard = [
        [InlineKeyboardButton("🎰 Сыграть ещё", callback_data=f"casino:roulette")],
        [InlineKeyboardButton("🏠 В меню казино", callback_data="casino:menu")]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    try:
        await query.message.edit_text(message, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        print(f"Ошибка при обновлении текста сообщения: {e}")

    await query.answer()




async def handle_roulette_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bal = get_balance(user_id)
    min_bet = 5
    max_bet = bal

    bet_amount = context.user_data.get('bet_amount', min_bet)
    bet_amount = max(min_bet, min(bet_amount, max_bet))

    keyboard = [
        [
            InlineKeyboardButton(f"⚫ Чёрное", callback_data=f"roulette_bet:black:{bet_amount}"),
            InlineKeyboardButton(f"🔴 Красное", callback_data=f"roulette_bet:red:{bet_amount}"),
            InlineKeyboardButton(f"🟢 Зеро", callback_data=f"roulette_bet:zero:{bet_amount}"),
        ],
        [
            InlineKeyboardButton(f"💰 Ставка +5", callback_data=f"change_bet:+5"),
            InlineKeyboardButton(f"💰 Ставка -5", callback_data=f"change_bet:-5")
        ],
        [
            InlineKeyboardButton("🏠 В меню казино", callback_data="casino:menu")  # Кнопка возврата в меню
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    text = (
        "🎰 **Рулетка**\n\n"
        f"💰 **Ставка**: {bet_amount} монет\n"
        "🎁 **Выигрыш**:\n"
        f"- **Чёрное / Красное**: {int(100 * (bet_amount / 50))} монет\n"
        f"- **Зеро**: {int(3600 * (bet_amount / 50))} монет\n\n"
        "Выберите ставку или измените сумму ставки:"
    )

    if update.callback_query:
        message = update.callback_query.message
    else:
        return

    try:
        await message.edit_text(text, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        print(f"Ошибка при обновлении текста сообщения с меню ставок: {e}")

    context.user_data['bet_amount'] = bet_amount
    await update.callback_query.answer()


async def handle_change_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bal = get_balance(user_id)
    min_bet = 5
    max_bet = bal

    bet_amount = context.user_data.get('bet_amount', min_bet)

    if update.callback_query.data == "change_bet:+5":
        bet_amount += 5
    elif update.callback_query.data == "change_bet:-5":
        bet_amount -= 5

    bet_amount = max(min_bet, min(bet_amount, max_bet))

    context.user_data['bet_amount'] = bet_amount

    await handle_roulette_bet(update, context)
