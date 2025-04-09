# handlers/betting_commands.py
"""
Модуль обработчиков команд для системы ставок.
Содержит функции для создания ставок, просмотра активных событий и истории ставок.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackContext
import logging
import json
import datetime
import time

from betting import (
    load_betting_events, 
    load_betting_data, 
    place_bet, 
    get_betting_history,
    get_user_streak,
    save_betting_events,
    get_next_active_event,
    publish_event,
    process_event_results
)
from balance import get_balance
from config import schedule_config, TIMEZONE_OFFSET

# Состояния для conversation handler
BET_AMOUNT = 0
BET_OPTION = 1

# Префиксы для callback данных
BET_CALLBACK_PREFIX = "bet_"
BET_OPTION_PREFIX = "bet_option_"
BET_AMOUNT_PREFIX = "bet_amount_"

async def bet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /bet.
    Показывает текущее активное событие и предлагает сделать ставку.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    # Логирование вызова функции
    logging.info("bet_command вызван")
    
    # Определяем, был ли вызов через callback или через команду
    query = update.callback_query
    event_id_from_callback = None
    
    if query:
        # Это callback от кнопки
        await query.answer()
        chat_id = update.effective_chat.id
        
        # Извлекаем ID события из callback data
        callback_data = query.data
        logging.info(f"bet_command вызван через callback с данными: {callback_data}")
        
        if callback_data.startswith("bet_event_"):
            event_id_str = callback_data.replace("bet_event_", "")
            # Проверяем специальный случай для "next"
            if event_id_str != "next":
                event_id_from_callback = event_id_str
                logging.info(f"ID события из callback: {event_id_from_callback}")
    else:
        # Это обычная команда
        chat_id = update.effective_chat.id
        logging.info("bet_command вызван через обычную команду")
        
    # Загружаем текущее активное событие
    betting_events = load_betting_events()
    active_event = None
    
    # Если у нас есть ID из callback, ищем конкретное событие
    if event_id_from_callback:
        for event in betting_events.get("events", []):
            if str(event.get("id")) == event_id_from_callback:
                active_event = event
                logging.info(f"Найдено событие по ID из callback: {event}")
                break
    
    # Если событие не найдено по ID или у нас нет ID (команда /bet),
    # ищем любое активное событие
    if not active_event:
        logging.info("Ищем первое активное событие")
        for event in betting_events.get("events", []):
            if event.get("is_active", True):
                active_event = event
                logging.info(f"Найдено активное событие: {event}")
                break
    
    if not active_event:
        message = "🎲 В данный момент нет активных событий для ставок."
        logging.warning("Не найдено активных событий для ставок")
        if query:
            # Просто информируем пользователя через callback
            await query.answer(text=message, show_alert=True)
        else:
            await context.bot.send_message(chat_id=chat_id, text=message)
        return
    
    # Проверяем, активно ли событие
    if not active_event.get("is_active", True) and not event_id_from_callback:
        message = "🎲 Выбранное событие больше не активно для ставок."
        logging.warning(f"Событие с ID {active_event.get('id')} не активно")
        if query:
            await query.answer(text=message, show_alert=True)
        else:
            await context.bot.send_message(chat_id=chat_id, text=message)
        return
    
    # Получаем время публикации результатов из конфига
    betting_config = schedule_config.get("betting", {})
    results_time = betting_config.get("results_time", "21:00")
    
    # Формируем сообщение с описанием события
    description = active_event.get("description", "")
    question = active_event.get("question", "")
    options = active_event.get("options", [])
    
    text = f"🎮 *СТАВКИ, ГОСПОДА!* 🎲\n\n"
    text += f"📌 *{description}*\n\n"
    text += f"❓ *{question}*\n\n"
    text += "🎯 *Варианты:*\n"
    
    for option in options:
        option_text = option.get("text", "")
        text += f"• {option_text}\n"
    
    text += f"\n💰 Выигрыш зависит от общей суммы ставок в тотализаторе!\n"
    text += f"⏰ Результаты в {results_time} (UTC+{TIMEZONE_OFFSET}). Удачи! 🍀\n\n"
    text += "👇 Сделайте ваш выбор:"
    
    # Создаем клавиатуру с вариантами
    keyboard = []
    for option in options:
        option_id = option.get("id")
        option_text = option.get("text")
        
        callback_data = f"{BET_OPTION_PREFIX}{active_event.get('id')}_{option_id}"
        logging.info(f"Создаем кнопку с callback_data: {callback_data}")
        
        button = InlineKeyboardButton(
            f"{option_text}", 
            callback_data=callback_data
        )
        keyboard.append([button])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Всегда отправляем новое сообщение
    message = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    logging.info(f"Отправлено сообщение с вариантами ставок: message_id={message.message_id}")

async def bet_option_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик нажатия на кнопку выбора варианта ставки.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    query = update.callback_query
    await query.answer()
    
    # Логирование для отладки
    logging.info(f"bet_option_callback вызван с данными: {query.data}")
    
    # Извлекаем данные из callback_data
    callback_data = query.data
    if not callback_data.startswith(BET_OPTION_PREFIX):
        logging.warning(f"Неверный префикс callback_data: {callback_data}")
        return
    
    data_parts = callback_data[len(BET_OPTION_PREFIX):].split('_')
    if len(data_parts) != 2:
        logging.warning(f"Неверный формат data_parts: {data_parts}")
        return
    
    event_id = data_parts[0]  # Не преобразуем в int, оставляем как строку
    option_id = data_parts[1]  # Не преобразуем в int, оставляем как строку
    
    logging.info(f"Обработка ставки: event_id={event_id}, option_id={option_id}")
    
    # Загружаем информацию о событии и выбранном варианте
    betting_events = load_betting_events()
    event = None
    option_text = "неизвестный вариант"
    
    for e in betting_events.get("events", []):
        if str(e.get("id")) == str(event_id):
            event = e
            for opt in e.get("options", []):
                if str(opt.get("id")) == str(option_id):
                    option_text = opt.get("text")
                    break
            break
    
    if not event:
        logging.error(f"Событие с ID {event_id} не найдено")
        await query.answer(text="Произошла ошибка. Событие не найдено.", show_alert=True)
        return
    
    # Проверяем, активно ли событие
    if not event.get("is_active", True):
        logging.warning(f"Событие с ID {event_id} не активно")
        await query.answer(text="Это событие больше не активно для ставок.", show_alert=True)
        return
    
    # Сохраняем выбранный вариант и ID события в контекст пользователя
    context.user_data["bet_event_id"] = event_id
    context.user_data["bet_option_id"] = option_id
    # Сохраняем ID исходного сообщения с событием для последующего удаления
    context.user_data["event_message_id"] = query.message.message_id
    
    logging.info(f"Контекст пользователя обновлен: event_id={event_id}, option_id={option_id}")
    
    # Получаем баланс пользователя
    user_id = update.effective_user.id
    user_balance = get_balance(user_id)
    
    text = f"🎯 Выбрано: *{option_text}*\n\n"
    text += f"💰 Баланс: *{user_balance}* 💵\n\n"
    text += "💸 Сколько ставим?"
    
    # Создаем клавиатуру с вариантами сумм ставок
    keyboard = []
    
    # Предлагаем стандартные суммы в зависимости от баланса
    bet_amounts = [10, 25, 50, 100, 200, 500]
    row = []
    
    for i, amount in enumerate(bet_amounts):
        if amount <= user_balance:
            button = InlineKeyboardButton(
                f"{amount} 💵", 
                callback_data=f"{BET_AMOUNT_PREFIX}{amount}"
            )
            row.append(button)
            
            if len(row) == 3:
                keyboard.append(row)
                row = []
    
    if row:
        keyboard.append(row)
    
    # Добавляем кнопку "Назад"
    keyboard.append([
        InlineKeyboardButton("Назад", callback_data="bet_back")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем новое сообщение вместо редактирования
    message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    logging.info(f"Отправлено сообщение с вариантами ставок: message_id={message.message_id}")

async def bet_amount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик нажатия на кнопку выбора суммы ставки.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    query = update.callback_query
    await query.answer()
    
    # Логирование для отладки
    logging.info(f"bet_amount_callback вызван с данными: {query.data}")
    
    # Извлекаем данные из callback_data
    callback_data = query.data
    
    if callback_data == "bet_back":
        # Пользователь нажал "Назад", возвращаемся к выбору варианта
        logging.info("Пользователь нажал 'Назад', возвращаемся к выбору варианта")
        await bet_command(update, context)
        return
    
    if not callback_data.startswith(BET_AMOUNT_PREFIX):
        logging.warning(f"Неверный префикс callback_data: {callback_data}")
        return
    
    try:
        amount = int(callback_data[len(BET_AMOUNT_PREFIX):])
        logging.info(f"Выбрана сумма ставки: {amount}")
    except ValueError:
        logging.error(f"Не удалось преобразовать сумму ставки: {callback_data[len(BET_AMOUNT_PREFIX):]}")
        return
    
    # Получаем данные из контекста пользователя
    event_id = context.user_data.get("bet_event_id")
    option_id = context.user_data.get("bet_option_id")
    event_message_id = context.user_data.get("event_message_id")
    
    logging.info(f"Данные из контекста пользователя: event_id={event_id}, option_id={option_id}, event_message_id={event_message_id}")
    
    if not event_id or not option_id:
        logging.error("Отсутствуют необходимые данные в контексте пользователя")
        await query.answer(
            text="Произошла ошибка. Пожалуйста, начните заново с команды /bet.",
            show_alert=True
        )
        return
    
    # Проверяем, что событие все еще активно
    betting_events = load_betting_events()
    event_is_active = False
    
    for e in betting_events.get("events", []):
        if str(e.get("id")) == str(event_id) and e.get("is_active", True):
            event_is_active = True
            logging.info(f"Событие с ID {event_id} активно")
            break
    
    if not event_is_active:
        logging.warning(f"Событие с ID {event_id} не активно")
        # Вместо простого уведомления, отправляем полноценное сообщение
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ Это событие больше не активно для ставок. Время ставок истекло.",
            parse_mode="Markdown"
        )
        # Удаляем сообщение с выбором суммы ставки
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=query.message.message_id
            )
        except Exception as e:
            logging.error(f"Ошибка при удалении сообщения: {e}")
        return
    
    # Размещаем ставку
    user_id = update.effective_user.id
    # Используем username без @
    username = update.effective_user.username
    user_name = username if username else update.effective_user.full_name or "Unknown"
    
    logging.info(f"Размещаем ставку: user_id={user_id}, user_name={user_name}, event_id={event_id}, option_id={option_id}, amount={amount}")
    
    success = place_bet(user_id, user_name, event_id, option_id, amount)
    
    if not success:
        logging.error("Не удалось разместить ставку")
        await query.answer(
            text="Не удалось разместить ставку. Возможно, у вас недостаточно средств или событие устарело.",
            show_alert=True
        )
        return
    
    logging.info("Ставка успешно размещена")
    
    # Загружаем информацию о событии и выбранном варианте
    event = None
    option_text = "неизвестный вариант"
    
    for e in betting_events.get("events", []):
        if str(e.get("id")) == str(event_id):
            event = e
            for opt in e.get("options", []):
                if str(opt.get("id")) == str(option_id):
                    option_text = opt.get("text")
                    break
            break
    
    # Получаем обновленный баланс
    new_balance = get_balance(user_id)
    
    # Упрощенный текст сообщения о ставке
    text = f"✅ Ставка {user_name} принята!\n\n"
    text += f"🎯 *{option_text}*\n"
    text += f"💸 Сумма: *{amount}* 💵\n\n"
    
    # Отправляем новое сообщение вместо редактирования
    message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode="Markdown"
    )
    
    logging.info(f"Отправлено сообщение о размещении ставки: message_id={message.message_id}")
    
    # Сохраняем сообщения для удаления
    messages_to_delete = [query.message.message_id]
    
    # Добавляем сообщение с вариантами ставок для удаления, если оно есть
    if event_message_id:
        messages_to_delete.append(event_message_id)
    
    # Удаляем временные сообщения сразу
    for msg_id in messages_to_delete:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=msg_id
            )
            logging.info(f"Удалено сообщение: message_id={msg_id}")
        except Exception as e:
            logging.error(f"Ошибка при удалении сообщения: {e}")

async def delete_temp_messages(context: CallbackContext, message_ids: list, chat_id: int):
    """
    Удаляет временные сообщения.
    Функция может использоваться в других местах кода для удаления временных сообщений.
    
    Args:
        context: Контекст от JobQueue
        message_ids: Список ID сообщений для удаления
        chat_id: ID чата
    """
    for message_id in message_ids:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            logging.error(f"Ошибка при удалении временного сообщения: {e}")

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /history.
    Показывает историю последних результатов ставок.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    # Определяем, был ли вызов через callback или через команду
    query = update.callback_query
    
    if query:
        # Это callback от кнопки
        await query.answer()
        chat_id = update.effective_chat.id
    else:
        # Это обычная команда
        chat_id = update.effective_chat.id
    
    history = get_betting_history(limit=5)
    
    if not history:
        message = "📜 История ставок пуста. Делайте ставки! 🎲"
        if query:
            await query.edit_message_text(text=message)
        else:
            await context.bot.send_message(chat_id=chat_id, text=message)
        return
    
    text = "📜 *ИСТОРИЯ СТАВОК* 📊\n\n"
    
    for i, entry in enumerate(history):
        event_date = entry.get("date", "Неизвестно")
        description = entry.get("description", "Неизвестное событие")
        question = entry.get("question", "")
        result_description = entry.get("result_description", "")
        
        text += f"📅 *{event_date}*\n"
        text += f"🎮 {description}\n"
        
        if question:
            text += f"❓ {question}\n"
        
        # Показываем варианты ставок с отметкой победителя
        options = entry.get("options", [])
        if options:
            text += "\n*Варианты:*\n"
            for option in options:
                option_text = option.get("text", "")
                is_winner = str(option.get("id")) == str(entry.get("winner_option_id"))
                winner_mark = " ✅" if is_winner else ""
                text += f"• {option_text}{winner_mark}\n"
        
        if result_description:
            text += f"\n📝 {result_description}\n"
        
        # Добавляем информацию о тотализаторе в сокращенном виде
        tote_coefficient = entry.get("tote_coefficient", 0)
        total_bets = entry.get("total_bets", 0)
        
        if tote_coefficient > 0:
            text += f"\n💰 Банк: {total_bets} 💵 | Коэфф: x{tote_coefficient:.2f}\n"
        
        # Добавляем информацию о победителях и проигравших более компактно
        winners = entry.get("winners", [])
        losers = entry.get("losers", [])
        
        if winners:
            text += "\n🏆 *Счастливчики:*\n"
            for winner in winners:
                user_name = winner.get("user_name", "Unknown")
                win_amount = winner.get("win_amount", 0)
                bet_amount = winner.get("bet_amount", 0) if "bet_amount" in winner else 0
                streak = winner.get("streak", 0)
                
                streak_emoji = " 🔥" if streak >= 3 else ""
                text += f"• {user_name}: +{win_amount} 💵{streak_emoji}\n"
        
        if losers:
            text += "\n💸 *Не повезло:*\n"
            max_losers = 3  # Ограничим количество проигравших
            for idx, loser in enumerate(losers[:max_losers]):
                user_name = loser.get("user_name", "Unknown")
                loss_amount = loser.get("loss_amount", 0)
                
                text += f"• {user_name}: -{loss_amount} 💵\n"
            
            if len(losers) > max_losers:
                text += f"• и еще {len(losers) - max_losers} участников...\n"
        
        # Добавляем разделитель только если это не последняя запись
        if i < len(history) - 1:
            text += "\n" + "🎲" * 5 + "\n\n"
    
    # Отправляем сообщение в зависимости от типа запроса
    if query:
        try:
            await query.edit_message_text(
                text=text, 
                parse_mode="Markdown"
            )
        except Exception as e:
            # Если сообщение слишком большое для редактирования,
            # отправляем новое сообщение
            logging.error(f"Ошибка при редактировании сообщения: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown"
            )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown"
        )

async def publish_betting_event(context: CallbackContext):
    """
    Публикует событие для ставок.
    Вызывается автоматически по расписанию.
    
    Args:
        context: Контекст от JobQueue
    """
    app = context.application # Получаем app из контекста
    from betting import get_next_active_event
    from config import POST_CHAT_ID
    from config import schedule_config, TIMEZONE_OFFSET
    import state
    
    # Проверяем, включена ли система ставок
    if not state.betting_enabled:
        logging.info("Система ставок отключена. Пропускаем публикацию события.")
        return
    
    # Получаем времена из конфига
    betting_config = schedule_config.get("betting", {})
    results_time = betting_config.get("results_time", "21:00")
    close_time = betting_config.get("close_time", "20:00")
    
    # Получаем следующее активное событие
    next_event = get_next_active_event()
    
    if not next_event:
        logging.info("Нет доступных событий для публикации.")
        return
    
    # Проверка, что событие активно
    if not next_event.get("is_active", True):
        logging.warning(f"Событие с ID {next_event.get('id')} не активно. Пропускаем публикацию.")
        return
    
    # Публикуем событие
    event_id = next_event.get("id")
    
    # Формируем текст сообщения
    description = next_event.get("description", "")
    question = next_event.get("question", "")
    options = next_event.get("options", [])
    
    text = "📊 *НОВОЕ СОБЫТИЕ ДЛЯ СТАВОК!* 🎲\n\n"
    text += f"📌 *{description}*\n\n"
    text += f"❓ *{question}*\n\n"
    text += "🎯 *Варианты:*\n"
    
    for option in options:
        option_text = option.get("text", "")
        text += f"• {option_text}\n"
    
    text += f"\n💰 Сделайте ваши ставки!\n"
    text += f"⏰ Прием ставок до {close_time} (UTC+{TIMEZONE_OFFSET})\n"
    text += f"🏆 Результаты в {results_time} (UTC+{TIMEZONE_OFFSET})\n\n"
    text += "Чтобы сделать ставку, используйте команду /bet"
    
    # Создаем inline-клавиатуру с кнопкой для ставки
    keyboard = [
        [InlineKeyboardButton("💸 Сделать ставку 🎲", callback_data=f"bet_event_{event_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение в POST_CHAT_ID с кнопкой
    await app.bot.send_message(
        chat_id=POST_CHAT_ID,
        text=text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    
    # НЕ помечаем событие как неактивное при публикации!
    # Событие должно оставаться активным, чтобы пользователи могли делать ставки
    # Ставки будут закрыты по расписанию в close_time
    
    logging.info(f"Опубликовано событие для ставок (ID: {event_id}) в чат {POST_CHAT_ID}")

async def process_betting_results(context: CallbackContext):
    """
    Обрабатывает результаты ставок и публикует их в чате.
    Вызывается автоматически по расписанию.
    
    Args:
        context: Контекст от JobQueue
    """
    app = context.application # Получаем app из контекста
    from betting import load_betting_events, process_event_results
    from config import POST_CHAT_ID, ADMIN_GROUP_ID
    import state
    
    # Проверяем, включена ли система ставок
    if not state.betting_enabled:
        logging.info("Система ставок отключена. Пропускаем обработку результатов.")
        return
    
    # Получаем все события, готовые для обработки результатов:
    # - неактивные
    # - с определенным winner_option_id
    # - без опубликованных результатов
    events_data = load_betting_events()
    events_for_results = []
    
    for event in events_data.get("events", []):
        if (not event.get("is_active", True) and 
            event.get("winner_option_id") is not None and 
            not event.get("results_published", False)):
            events_for_results.append(event)
    
    if not events_for_results:
        # Если нет событий для обработки результатов, отправляем сообщение администраторам
        logging.warning("Нет событий для обработки результатов ставок")
        await app.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text="⚠️ Предупреждение: нет событий для обработки результатов ставок."
        )
        return
    
    # Обрабатываем результаты для каждого события
    logging.info(f"Найдено {len(events_for_results)} событий для публикации результатов")
    
    for event_for_results in events_for_results:
        # Получаем предопределенный победный вариант из данных события
        winner_option_id = event_for_results.get("winner_option_id")
        event_id = event_for_results.get("id")
        
        logging.info(f"Обработка результатов для события ID: {event_id}")
        
        # Обрабатываем результаты
        results = process_event_results(event_id, winner_option_id)
        
        if results.get("status") != "success":
            logging.error(f"Ошибка при обработке результатов события {event_id}: {results.get('message')}")
            continue
        
        # Формируем сообщение с результатами
        description = event_for_results.get("description", "")
        question = event_for_results.get("question", "")
        correct_option = results.get("correct_option", {})
        correct_option_text = correct_option.get("text", "")
        result_description = event_for_results.get("result_description", "")
        
        text = "🏁 *РЕЗУЛЬТАТЫ СТАВОК!* 🎲\n\n"
        text += f"📌 *{description}*\n\n"
        text += f"❓ *{question}*\n"
        
        # Объединяем информацию о правильном ответе и описании результата
        text += f"✅ *{correct_option_text}*\n"
        
        if result_description:
            text += f"📝 {result_description}\n"
        
        # Получаем коэффициент тотализатора более компактно
        tote_coefficient = results.get("tote_coefficient", 1.0)
        total_bets = results.get("total_bets", 0)
        
        text += f"\n💰 Банк: {total_bets} 💵 | Коэфф: x{tote_coefficient:.2f}\n"
        
        # Добавляем информацию о победителях в более веселом стиле
        winners = results.get("winners", [])
        if winners:
            text += "\n🏆 *ПОЗДРАВЛЯЕМ!*\n"
            for winner in winners:
                user_name = winner.get("user_name", "Unknown")
                win_amount = winner.get("win_amount", 0)
                bet_amount = winner.get("bet_amount", 0)
                streak = winner.get("streak", 0)
                
                streak_emoji = " 🔥" if streak >= 3 else ""
                text += f"• {user_name}: +{win_amount} 💵{streak_emoji}\n"
        else:
            text += "\n😢 *В этот раз никто не угадал!* 🤷‍♂️\n"
        
        # Добавляем информацию о проигравших в более компактном виде
        losers = results.get("losers", [])
        if losers:  # Показываем проигравших всегда, когда они есть
            text += "\n💸 *Повезет в следующий раз:*\n"
            max_losers = 3  # Ограничиваем для компактности
            for idx, loser in enumerate(losers[:max_losers]):
                user_name = loser.get("user_name", "Unknown")
                loss_amount = loser.get("loss_amount", 0)
                
                text += f"• {user_name}: -{loss_amount} 💵\n"
            
            if len(losers) > max_losers:
                text += f"• и еще {len(losers) - max_losers} участников...\n"
        
        # Отправляем результаты в POST_CHAT_ID без кнопки для новой ставки
        await app.bot.send_message(
            chat_id=POST_CHAT_ID,
            text=text,
            parse_mode="Markdown"
        )
        
        logging.info(f"Опубликованы результаты ставок (ID события: {event_id}) в чат {POST_CHAT_ID}")
    
    # Общий лог о завершении публикации всех результатов
    logging.info(f"Завершена публикация результатов для всех {len(events_for_results)} событий")

async def close_betting_event(context: CallbackContext):
    """
    Закрывает текущее активное событие для ставок.
    Вызывается по расписанию перед публикацией результатов.
    """
    app = context.application # Получаем app из контекста
    from betting import load_betting_events, save_betting_events
    from config import ADMIN_GROUP_ID
    import state
    
    # Проверяем, включена ли система ставок
    if not state.betting_enabled:
        logging.info("Система ставок отключена. Пропускаем закрытие события.")
        return
    
    # Загружаем все события
    events_data = load_betting_events()
    active_event = None
    
    # Найдем активное событие, которое нужно закрыть
    for event in events_data.get("events", []):
        if event.get("is_active", True):
            active_event = event
            break
    
    if not active_event:
        logging.info("Нет активных событий для закрытия.")
        return
    
    # Закрываем событие
    event_id = active_event.get("id")
    success = publish_event(event_id)
    
    if success:
        # Записываем в лог об успешном закрытии события
        logging.info(f"Закрыто событие для ставок (ID: {event_id})")
    else:
        logging.error(f"Не удалось закрыть событие для ставок (ID: {event_id})")

async def start_betting_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды для включения системы ставок.
    Включает публикацию событий для ставок по расписанию.
    """
    import state
    state.betting_enabled = True
    state.save_state(state.autopost_enabled, state.quiz_enabled, state.wisdom_enabled, state.betting_enabled)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Система ставок включена!")

async def stop_betting_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды для отключения системы ставок.
    Отключает публикацию событий для ставок по расписанию.
    """
    import state
    state.betting_enabled = False
    state.save_state(state.autopost_enabled, state.quiz_enabled, state.wisdom_enabled, state.betting_enabled)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Система ставок отключена!")

async def results_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /results для администраторов.
    Показывает текущее активное событие и предлагает выбрать результат.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    # Получаем следующее активное событие
    next_event = get_next_active_event()
    
    if not next_event:
        await context.bot.send_message(
            chat_id=update.message.chat_id,
            text="Нет активных событий для обработки результатов."
        )
        return
    
    # Формируем сообщение с описанием события
    description = next_event.get("description", "")
    question = next_event.get("question", "")
    options = next_event.get("options", [])
    
    text = f"📊 *ВЫБОР РЕЗУЛЬТАТА СОБЫТИЯ* 🎲\n\n"
    text += f"📌 *{description}*\n\n"
    text += f"❓ *{question}*\n\n"
    text += "🎯 *Варианты:*\n"
    
    # Создаем клавиатуру с вариантами
    keyboard = []
    for option in options:
        option_id = option.get("id")
        option_text = option.get("text")
        
        callback_data = f"result_{next_event.get('id')}_option_{option_id}"
        
        button = InlineKeyboardButton(
            f"{option_text}", 
            callback_data=callback_data
        )
        keyboard.append([button])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=update.message.chat_id,
        text=text + "\nВыберите результат события:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def results_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик колбэка для выбора результата события.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    query = update.callback_query
    
    # Извлекаем данные из callback_data
    callback_data = query.data
    
    # Проверяем формат данных
    if not callback_data.startswith("result_"):
        await query.answer("Ошибка: некорректный формат данных", show_alert=True)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Произошла ошибка. Некорректный формат данных."
        )
        return
    
    try:
        # Парсим данные из формата "result_EVENT_ID_option_OPTION_ID"
        parts = callback_data.split("_")
        event_id = parts[1]
        option_id = parts[3]
        
        # Получаем событие по ID
        event = get_betting_event_by_id(event_id)
        
        if not event:
            await query.answer("Ошибка: событие не найдено", show_alert=True)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Событие не найдено или устарело."
            )
            return
        
        # Обрабатываем результаты события
        results = process_event_results(event_id, option_id)
        
        await query.answer("Результаты события обработаны")
        
        # Отправляем сообщение об успешной обработке
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"✅ Результаты события успешно обработаны!\n\nСобытие: {event.get('description')}\nПобедивший вариант: {option_id}"
        )
        
    except Exception as e:
        logging.error(f"Ошибка при обработке результатов события: {e}")
        await query.answer("Произошла ошибка при обработке результатов", show_alert=True)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"Произошла ошибка при обработке результатов: {e}"
        )

def get_betting_event_by_id(event_id):
    """
    Получает событие по его ID.
    
    Args:
        event_id (str или int): ID события
    
    Returns:
        dict: Данные события или None, если событие не найдено
    """
    events_data = load_betting_events()
    
    for event in events_data.get("events", []):
        if str(event.get("id")) == str(event_id):
            return event
    
    return None

async def betting_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик колбэка для быстрого размещения ставок.
    Формат данных: "event_EVENT_ID_option_OPTION_ID"
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    query = update.callback_query
    
    # Извлекаем данные из callback_data
    callback_data = query.data
    
    try:
        # Парсим данные из формата "event_EVENT_ID_option_OPTION_ID"
        parts = callback_data.split("_")
        
        if len(parts) != 4 or parts[0] != "event" or parts[2] != "option":
            raise ValueError("Некорректный формат данных")
        
        event_id = int(parts[1])
        option_id = int(parts[3])
        
        # Получаем данные пользователя
        user_id = query.from_user.id
        username = query.from_user.username
        
        # Размещаем ставку стандартного размера (например, 50)
        bet_amount = 50
        success = place_bet(user_id, username, event_id, option_id, bet_amount)
        
        if success:
            await query.answer("Ставка принята!")
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"✅ Ваша ставка на сумму {bet_amount} 💵 принята!"
            )
        else:
            await query.answer("Не удалось разместить ставку. Проверьте баланс.", show_alert=True)
    
    except Exception as e:
        logging.error(f"Ошибка при обработке ставки: {e}")
        await query.answer(f"Ошибка: {e}", show_alert=True) 