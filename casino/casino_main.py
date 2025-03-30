"""
Основной модуль казино, содержащий главное меню и обработчики для управления играми.
Поддерживает игры: слоты и рулетка, с возможностью делать ставки и выигрывать монеты.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from balance import get_balance
from casino.slots import handle_slots_callback, handle_slots_bet_callback
from casino.roulette import handle_roulette_bet, handle_roulette_bet_callback, handle_change_bet

async def casino_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /casino - показывает главное меню казино с текущим балансом.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    # Проверяем, что запрос от пользователя, а не от бота
    if update.callback_query and not update.callback_query.from_user.is_bot:
        user_id = update.callback_query.from_user.id
    elif update.message and not update.message.from_user.is_bot:
        user_id = update.message.from_user.id
    else:
        return

    try:
        bal = get_balance(user_id)  # Получаем актуальный баланс для этого user_id
        logging.debug(f"Баланс пользователя {user_id}: {bal}")

        # Отправляем меню казино с актуальным балансом
        keyboard = [
            [
                InlineKeyboardButton("🎰 Слоты", callback_data="casino:slots"),
                InlineKeyboardButton("🎲 Рулетка", callback_data="casino:roulette"),
            ],
            [InlineKeyboardButton("🚪 Выйти", callback_data="casino:exit")]
        ]
        markup = InlineKeyboardMarkup(keyboard)

        text = (
            f"🎉 Добро пожаловать в казино, {update.effective_user.first_name}! 🎉\n\n"
            f"💰 Ваш текущий баланс: {bal} монет.\n"
            f"Выберите игру и испытайте удачу!"
        )

        # Если это колбэк-запрос, удаляем предыдущее сообщение
        if update.callback_query and update.callback_query.message:
            try:
                await update.callback_query.message.delete()
            except Exception as e:
                logging.error(f"Ошибка при удалении сообщения с меню казино: {e}")

        # Отправляем новое сообщение с меню
        if update.message:
            await context.bot.send_message(chat_id=update.message.chat_id, text=text, reply_markup=markup)
        elif update.callback_query:
            await context.bot.send_message(chat_id=update.callback_query.message.chat_id, text=text, reply_markup=markup)
    
    except Exception as e:
        logging.error(f"Ошибка при получении баланса или отправке сообщения: {e}")

async def casino_menu_without_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает упрощенное меню казино без отображения баланса.
    Используется для возврата из игр в меню без дополнительных запросов к базе.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    if update.callback_query and not update.callback_query.from_user.is_bot:
        user_id = update.callback_query.from_user.id
    elif update.message and not update.message.from_user.is_bot:
        user_id = update.message.from_user.id
    else:
        return

    try:
        # Удаляем предыдущее сообщение, если есть
        if update.callback_query.message:
            try:
                await update.callback_query.message.delete()
            except Exception as e:
                logging.error(f"Ошибка при удалении сообщения с меню казино: {e}")
        
        # Создаем меню с кнопками игр и возврата в основное меню
        keyboard = [
            [
                InlineKeyboardButton("🎰 Слоты", callback_data="casino:slots"),
                InlineKeyboardButton("🎲 Рулетка", callback_data="casino:roulette"),
            ],
            [InlineKeyboardButton("🏠 В меню казино", callback_data="casino:menu")]
        ]
        markup = InlineKeyboardMarkup(keyboard)

        text = "🎉 Добро пожаловать в казино! Выберите игру для начала!"

        # Отправляем сообщение
        if update.callback_query and update.callback_query.message:
            await context.bot.send_message(chat_id=update.callback_query.message.chat_id, text=text, reply_markup=markup)
        elif update.message:
            await context.bot.send_message(chat_id=update.message.chat_id, text=text, reply_markup=markup)
    
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения без баланса: {e}")

async def casino_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Центральный обработчик для всех callback-запросов в казино.
    Перенаправляет запросы к соответствующим обработчикам игр.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    query = update.callback_query
    data = query.data

    try:
        # Перенаправляем запрос в зависимости от типа игры и действия
        if data == "casino:slots":
            # Запуск игры в слоты
            await handle_slots_callback(query, context)
        elif data == "casino:roulette":
            # Запуск игры в рулетку
            await handle_roulette_bet(update, context)
        elif data.startswith("roulette_bet:"):
            # Обработка ставки в рулетке
            bet_type = data.split(":")[1]
            bet_amount = int(data.split(":")[2])
            context.user_data['bet_amount'] = bet_amount
            await handle_roulette_bet_callback(query, context, bet_type)
        elif data.startswith("slots_bet:"):
            # Обработка ставки для слотов
            await handle_slots_bet_callback(update, context)
        elif data == "casino:menu":
            # Возврат в главное меню казино
            await casino_command(update, context)
        elif data == "casino:exit":
            # Выход из казино
            await query.message.delete()
            await query.answer("Вы покинули казино. До встречи! 👋")
        else:
            # Обработка неизвестной команды
            await query.answer("❗ Неизвестная команда. Пожалуйста, попробуйте снова.", show_alert=True)
    
    except Exception as e:
        logging.error(f"Ошибка при обработке callback запроса: {e}")
        await query.answer("❌ Произошла ошибка. Пожалуйста, попробуйте позже.", show_alert=True)
