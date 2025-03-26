from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import asyncio
import random
from balance import get_balance, update_balance
from casino.roulette_utils import get_roulette_result
from telegram.error import TimedOut
import time

# Списки для ставок на черное, красное и зеро (ID гифок)
black_gif_ids = ['CgACAgIAAxkBAAID9me45nkKknU5sVQLgvQmhnoqxbCQAAJDcwACklXISTmzQBaNQ8e7NgQ', 
                 'CgACAgIAAxkBAAID8me45mVuztHElvA3oc_G6ZxNxmZkAAJBcwACklXISVCKm-JFsIkJNgQ',
                 'CgACAgIAAxkBAAID8Ge45lpSuXqKhrqfDmKrPwi95YZpAAJAcwACklXISXW0_1OtReg5NgQ',
                 'CgACAgIAAxkBAAID7me45k5YndtHTUby34RzbaTDbfhXAAI_cwACklXISXXZjcu2g88GNgQ',
                 'CgACAgIAAxkBAAID7Ge45kXFm2Wp0t5IVNe04v1VJYjiAAI-cwACklXIScZXS4xDdgABIDYE',
                 'CgACAgIAAxkBAAID6me45jpovYQKCY8lRPQ-O5JAtSxAAAI9cwACklXISYve-ahtDlPzNgQ',
                 'CgACAgIAAxkBAAID6Ge45hTsB5E7hndYyTzKHCdaBDChAAI7cwACklXISTW-WQuyyNCVNgQ',
                 'CgACAgIAAxkBAAID5Ge45WoOBRipgfeFeBZpbI1pZKTmAAIzcwACklXISWRlA5cYryoPNgQ',
                 'CgACAgIAAxkBAAID4me45V4hctDNUAY__7e44C5-B6IiAAIxcwACklXISfQHpAqfDTjUNgQ',
                 'CgACAgIAAxkBAAID4Ge45VRRRdIKxoFQ38vHl-Rda48OAAIwcwACklXISeXetXZ8ePN2NgQ',
                 'CgACAgIAAxkBAAID3me45UiTuzFHXBYkJrYPdgogwYDqAAIvcwACklXISdwVf6Quv--zNgQ',
                 'CgACAgIAAxkBAAID3Ge45T2Icg2Z9dtpsMAcRgOB0smFAAIscwACklXISZZYdbAvMr05NgQ',
                 'CgACAgIAAxkBAAID2We45RDwasMrlzben1YCoMZtBMXnAAIjcwACklXISTZW-MooxkyLNgQ',
                 'CgACAgIAAxkBAAID12e45QGLjFMJ8t-s482x2vIs2z8MAAIhcwACklXISb5Yt2rlKtPrNgQ',
                 'CgACAgIAAxkBAAID1We45Paboluo5HrN3pZYhdQ6-USmAAIgcwACklXISTM9muk0mHiGNgQ',
                 'CgACAgIAAxkBAAID02e45Oe_I_dwyq8cdhWucqBx-4idAAIfcwACklXISfx_bUYDI836NgQ',
                 'CgACAgIAAxkBAAID9Ge45m-XEGq_Dchtg10W6ZLk0Rq6AAJCcwACklXISbTPkuJ4WStvNgQ']

red_gif_ids = ['CgACAgIAAxkBAAIEDWe459PtSpb4hU1mZWPuzqe2EvdKAAJQcwACklXISZ-q6OVKL6rjNgQ', 
               'CgACAgIAAxkBAAIECWe457nbfaA1L9hIZKDCDYzr9ltXAAKOYwACxHPISXwkPWPPdK4bNgQ',
               'CgACAgIAAxkBAAIEB2e456wuL5X43sMLce-MvX9mvUISAAJNcwACklXISZGwTGqG0_OPNgQ',
               'CgACAgIAAxkBAAIEBWe455snL-scUUfzphLdBtkJvFg7AAJMcwACklXISR2mtzMH_R2LNgQ',
               'CgACAgIAAxkBAAIEA2e455G6QKJ9NjhA6xnOjgeXAqswAAJLcwACklXISfwBUsOZHXjvNgQ',
               'CgACAgIAAxkBAAIEAWe454aMlstjz15cKz0YbriRa2GEAAJKcwACklXISUZl3ALo_F5uNgQ',
               'CgACAgIAAxkBAAID_2e453zRxdgc15qBT51wEk8vnfBxAAJJcwACklXISU2RWqqvdZHYNgQ',
               'CgACAgIAAxkBAAID_We452H-Jl8753JAuE5rYprNRrcsAAJIcwACklXISZ_cz9YM3jmANgQ',
               'CgACAgIAAxkBAAID-2e450E-hyvRwN87HBT_VlmHucRZAAJHcwACklXISTdZUIbqW8gCNgQ',
               'CgACAgIAAxkBAAIED2e46G4WG0B8tDJWEw5mNBpjsVEyAAJVcwACklXISQodGtEAAfAxyTYE',
               'CgACAgIAAxkBAAIEEWe46Iblsha2xTOMQIaqxzvF7DBIAAJWcwACklXISbn9T1NjLJGwNgQ',
               'CgACAgIAAxkBAAIEE2e46JHNogcmeXXla_u7f_Gv-jt2AAJYcwACklXISZ55fWvtx_yCNgQ',
               'CgACAgIAAxkBAAIEFWe46JzwFWCMk4SkJ78S_j_NipJUAAJZcwACklXISfcMUzQleb6wNgQ',
               'CgACAgIAAxkBAAIEF2e46Kbx_TX95k8tdyB7Qygd1Y8gAAJbcwACklXISXLjMPF4fUkYNgQ',
               'CgACAgIAAxkBAAIEGWe46K9z7foe8Ok6xw_Y3v5Hm7gMAAJccwACklXIScUOj0yf8SS1NgQ',
               'CgACAgIAAxkBAAIEG2e46Lf0_x0JvgMrm1tW3a-1B8bQAAJfcwACklXISTUBRiIrV1dsNgQ',
               'CgACAgIAAxkBAAIEHWe46MDThj8c_fgwSa4XQMUAAZcChwACYHMAApJVyEnpFPiJ0AeJwTYE',
               'CgACAgIAAxkBAAIEC2e458Ury_0OvDKpZVoJQZwUigSNAAJOcwACklXISaHfIDGzaMVoNgQ']

zero_gif_ids = ['CgACAgIAAxkBAAID-Ge45tYeSXE6g-PtCba_36J80W3eAAJGcwACklXISX0sVKih37EuNgQ']

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

    if result == 'black':
        gif_id = random.choice(black_gif_ids)
    elif result == 'red':
        gif_id = random.choice(red_gif_ids)
    else:
        gif_id = random.choice(zero_gif_ids)

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
