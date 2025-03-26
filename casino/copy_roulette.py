from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import asyncio
import random
from balance import get_balance, update_balance
from casino.roulette_utils import get_roulette_result

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

async def handle_roulette_bet_callback(query, context: ContextTypes.DEFAULT_TYPE, bet_type: str):
    # Извлекаем bet_amount из callback_data
    bet_amount = int(query.data.split(":")[-1])  # Получаем ставку из callback_data

    user_id = query.from_user.id  # Используем правильный user_id из callback_query
    bal = get_balance(user_id)  # Получаем актуальный баланс

    # Проверяем, есть ли у игрока достаточно средств для ставки
    if bal < bet_amount:
        await query.answer("💸 У вас недостаточно средств для ставки. Пополните баланс и попробуйте снова!", show_alert=True)
        return

    # Отнимаем ставку с баланса
    update_balance(user_id, -bet_amount)  # Вычитаем ставку с баланса

    # Генерируем результат рулетки
    result = get_roulette_result()

    # Выбираем случайную гифку в соответствии с результатом
    if result == 'black':
        gif_id = random.choice(black_gif_ids)
    elif result == 'red':
        gif_id = random.choice(red_gif_ids)
    else:  # zero
        gif_id = random.choice(zero_gif_ids)

    # Удаляем старое сообщение с результатом игры
    try:
        await query.message.delete()
    except Exception as e:
        print(f"Ошибка при удалении сообщения с результатом игры: {e}")

    # Отправляем гифку напрямую в чат с использованием chat_id
    try:
        gif_message = await query.message.chat.send_animation(gif_id)
    except Exception as e:
        print(f"Ошибка при отправке гифки: {e}")
        return

    # Ожидаем 4 секунды (длительность гифки)
    await asyncio.sleep(5.5)

    # Удаляем гифку
    await gif_message.delete()

    # Проверяем, выиграл ли пользователь
    win = result == bet_type

    # Пропорционально увеличиваем выигрыш в зависимости от ставки
    if win:
        base_winnings = 100 if bet_type != 'zero' else 175  # Базовый выигрыш
        winnings = int(base_winnings * (bet_amount / 50))  # Увеличиваем выигрыш в зависимости от ставки
        if bet_type == 'zero':
            winnings = int(winnings * 1.75)  # Больший выигрыш для зеро
        update_balance(user_id, winnings)
        message = f"🎉 *Поздравляем!* Вы выиграли {winnings} монет! 🎉"
    else:
        result_emoji = "⚫" if result == "black" else "🔴" if result == "red" else "🟢"
        message = f"😔 *Вы проиграли.* Выпало: {result_emoji}"

    new_balance = get_balance(user_id)
    message += f"\n\n💰 *Ваш текущий баланс*: {new_balance} монет."

    # Кнопка "Сыграть ещё"
    keyboard = [
        [InlineKeyboardButton("🎰 Сыграть ещё", callback_data=f"casino:roulette")],  # Просто передаем команду для возврата в меню ставок
        [InlineKeyboardButton("🏠 В меню казино", callback_data="casino:menu")]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    # Отправляем новое сообщение с результатом без привязки к старому
    try:
        await query.message.chat.send_message(message, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        print(f"Ошибка при отправке сообщения о результате: {e}")

    await query.answer()

async def handle_roulette_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню ставок"""
    user_id = update.effective_user.id
    bal = get_balance(user_id)

    # Минимальная ставка 5 монет
    min_bet = 5
    max_bet = bal  # Максимальная ставка — это текущий баланс

    # Извлекаем текущую ставку из данных
    bet_amount = context.user_data.get('bet_amount', min_bet)

    # Проверяем, чтобы ставка не была ниже минимальной и не превышала максимальный баланс
    bet_amount = max(min_bet, min(bet_amount, max_bet))

    # Кнопки для изменения ставки
    keyboard = [
        [
            InlineKeyboardButton(f"⚫ Чёрное", callback_data=f"roulette_bet:black:{bet_amount}"),
            InlineKeyboardButton(f"🔴 Красное", callback_data=f"roulette_bet:red:{bet_amount}"),
            InlineKeyboardButton(f"🟢 Зеро", callback_data=f"roulette_bet:zero:{bet_amount}"),
        ],
        [
            InlineKeyboardButton(f"💰 Ставка +5", callback_data=f"change_bet:+5"),
            InlineKeyboardButton(f"💰 Ставка -5", callback_data=f"change_bet:-5")
        ]
    ]

    markup = InlineKeyboardMarkup(keyboard)

    # Обновленный текст с информацией о ставке
    text = (
        "🎰 **Рулетка**\n\n"
        f"💰 **Ставка**: {bet_amount} монет\n"
        "🎁 **Выгрыш**:\n"
        f"- **Чёрное / Красное**: {int(100 * (bet_amount / 50))} монет\n"
        f"- **Зеро**: {int(175 * (bet_amount / 50))} монет\n\n"
        "Выберите ставку или измените сумму ставки:"
    )

    # Получаем сообщение из callback_query
    if update.callback_query:
        message = update.callback_query.message
    else:
        return

    # Удаляем старое сообщение с меню ставок
    try:
        await message.delete()
    except Exception as e:
        print(f"Ошибка при удалении сообщения с меню ставок: {e}")

    # Отправляем новое сообщение без привязки к старому
    await message.chat.send_message(text, reply_markup=markup, parse_mode='Markdown')

    # Сохраняем текущую ставку в контексте
    context.user_data['bet_amount'] = bet_amount
    await update.callback_query.answer()

async def handle_change_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик изменения ставки"""
    user_id = update.effective_user.id
    bal = get_balance(user_id)

    # Минимальная ставка 5 монет
    min_bet = 5
    max_bet = bal  # Максимальная ставка — это текущий баланс

    # Извлекаем текущую ставку из данных
    bet_amount = context.user_data.get('bet_amount', min_bet)

    # Проверяем кнопку, чтобы изменить ставку
    if update.callback_query.data == "change_bet:+5":
        bet_amount += 5
    elif update.callback_query.data == "change_bet:-5":
        bet_amount -= 5

    # Ограничиваем ставку в пределах минимальной и максимальной
    bet_amount = max(min_bet, min(bet_amount, max_bet))

    # Сохраняем текущую ставку в контексте
    context.user_data['bet_amount'] = bet_amount

    # Обновляем меню с новой ставкой
    await handle_roulette_bet(update, context)
