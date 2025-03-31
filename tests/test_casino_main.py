import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call

# Импортируем тестируемый модуль и его функции
try:
    import casino.casino_main as casino_main # Импортируем модуль с псевдонимом
    from casino.casino_main import (
        casino_command,
        casino_menu_without_balance,
        casino_callback_handler
    )
    # Импортируем зависимости для мокирования
    import balance
    import casino.slots as casino_slots
    import casino.roulette as casino_roulette
    from telegram import Update, InlineKeyboardMarkup, User, CallbackQuery, Message
except ImportError as e:
    pytest.skip(f"Пропуск тестов casino_main: не удалось импортировать модуль casino.casino_main или его зависимости ({e}).", allow_module_level=True)

# --- Тесты для casino_command ---

@pytest.mark.asyncio
@patch('casino.casino_main.get_balance', return_value=100) # Мок баланса
async def test_casino_command_from_message(mock_get_balance):
    """Тест вызова /casino из сообщения."""
    update = MagicMock(spec=Update)
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 123
    message.from_user.is_bot = False
    message.from_user.first_name = "Tester"
    message.chat_id = 987
    update.message = message
    update.callback_query = None
    update.effective_user = message.from_user # Устанавливаем effective_user
    
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    
    await casino_command(update, context)
    
    mock_get_balance.assert_called_once_with(123)
    
    # Проверяем отправленное сообщение
    context.bot.send_message.assert_awaited_once()
    args, kwargs = context.bot.send_message.call_args
    assert kwargs['chat_id'] == 987
    assert "Добро пожаловать в казино, Tester!" in kwargs['text']
    assert "Ваш текущий баланс: 100 монет" in kwargs['text']
    assert isinstance(kwargs['reply_markup'], InlineKeyboardMarkup)
    # Проверяем кнопки
    keyboard = kwargs['reply_markup'].inline_keyboard
    assert len(keyboard) == 2
    assert len(keyboard[0]) == 2
    assert keyboard[0][0].text == "🎰 Слоты"
    assert keyboard[0][0].callback_data == "casino:slots"
    assert keyboard[0][1].text == "🎲 Рулетка"
    assert keyboard[0][1].callback_data == "casino:roulette"
    assert keyboard[1][0].text == "🚪 Выйти"
    assert keyboard[1][0].callback_data == "casino:exit"

@pytest.mark.asyncio
@patch('casino.casino_main.get_balance', return_value=50)
async def test_casino_command_from_callback(mock_get_balance):
    """Тест вызова казино из callback (например, возврат в меню)."""
    update = MagicMock(spec=Update)
    callback_query = MagicMock(spec=CallbackQuery)
    callback_query.from_user = MagicMock(spec=User)
    callback_query.from_user.id = 456
    callback_query.from_user.is_bot = False
    callback_query.from_user.first_name = "Player"
    callback_query.message = MagicMock(spec=Message)
    callback_query.message.chat_id = 777
    callback_query.message.delete = AsyncMock() # Мок удаления сообщения
    update.callback_query = callback_query
    update.message = None
    update.effective_user = callback_query.from_user
    
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    
    await casino_command(update, context)
    
    mock_get_balance.assert_called_once_with(456)
    # Проверяем удаление предыдущего сообщения
    callback_query.message.delete.assert_awaited_once()
    # Проверяем отправку нового сообщения (аналогично предыдущему тесту)
    context.bot.send_message.assert_awaited_once()
    args, kwargs = context.bot.send_message.call_args
    assert kwargs['chat_id'] == 777
    assert "Ваш текущий баланс: 50 монет" in kwargs['text']
    assert isinstance(kwargs['reply_markup'], InlineKeyboardMarkup)

# --- Тесты для casino_menu_without_balance ---

@pytest.mark.asyncio
async def test_casino_menu_without_balance_from_callback():
    """Тест вызова упрощенного меню из callback."""
    update = MagicMock(spec=Update)
    callback_query = MagicMock(spec=CallbackQuery)
    callback_query.from_user = MagicMock(spec=User)
    callback_query.from_user.id = 789
    callback_query.from_user.is_bot = False
    callback_query.message = MagicMock(spec=Message)
    callback_query.message.chat_id = 555
    callback_query.message.delete = AsyncMock()
    update.callback_query = callback_query
    update.message = None
    
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    
    await casino_menu_without_balance(update, context)
    
    callback_query.message.delete.assert_awaited_once()
    context.bot.send_message.assert_awaited_once()
    args, kwargs = context.bot.send_message.call_args
    assert kwargs['chat_id'] == 555
    assert "Добро пожаловать в казино! Выберите игру для начала!" in kwargs['text']
    assert isinstance(kwargs['reply_markup'], InlineKeyboardMarkup)
    keyboard = kwargs['reply_markup'].inline_keyboard
    assert len(keyboard) == 2
    assert keyboard[1][0].text == "🏠 В меню казино" # Проверяем кнопку возврата
    assert keyboard[1][0].callback_data == "casino:menu"

# --- Тесты для casino_callback_handler ---

@pytest.mark.asyncio
@patch('casino.casino_main.handle_slots_callback')
async def test_casino_callback_handler_slots(mock_handle_slots):
    """Тест перенаправления на обработчик слотов."""
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.data = "casino:slots"
    update.callback_query = query
    context = MagicMock()
    
    await casino_callback_handler(update, context)
    
    mock_handle_slots.assert_awaited_once_with(query, context)
    query.answer.assert_not_called() # answer не вызывается при успешном перенаправлении

@pytest.mark.asyncio
@patch('casino.casino_main.handle_roulette_bet')
async def test_casino_callback_handler_roulette(mock_handle_roulette):
    """Тест перенаправления на обработчик рулетки."""
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.data = "casino:roulette"
    update.callback_query = query
    context = MagicMock()
    
    await casino_callback_handler(update, context)
    
    mock_handle_roulette.assert_awaited_once_with(update, context)
    query.answer.assert_not_called()

@pytest.mark.asyncio
@patch('casino.casino_main.casino_command')
async def test_casino_callback_handler_menu(mock_casino_cmd):
    """Тест перенаправления на команду главного меню."""
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.data = "casino:menu"
    update.callback_query = query
    context = MagicMock()
    
    await casino_callback_handler(update, context)
    
    mock_casino_cmd.assert_awaited_once_with(update, context)
    query.answer.assert_not_called()

@pytest.mark.asyncio
async def test_casino_callback_handler_exit():
    """Тест обработки выхода из казино."""
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.data = "casino:exit"
    query.message = MagicMock(spec=Message)
    query.message.delete = AsyncMock()
    query.answer = AsyncMock()
    update.callback_query = query
    context = MagicMock()
    
    await casino_callback_handler(update, context)
    
    query.message.delete.assert_awaited_once()
    query.answer.assert_awaited_once_with("Вы покинули казино. До встречи! 👋")

@pytest.mark.asyncio
@patch('casino.casino_main.handle_slots_bet_callback')
async def test_casino_callback_handler_slots_bet(mock_handle_slots_bet):
    """Тест перенаправления на обработчик ставки слотов."""
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.data = "slots_bet:10"
    update.callback_query = query
    context = MagicMock()

    await casino_callback_handler(update, context)

    mock_handle_slots_bet.assert_awaited_once_with(update, context)
    query.answer.assert_not_called()

@pytest.mark.asyncio
@patch('casino.casino_main.handle_roulette_bet_callback')
async def test_casino_callback_handler_roulette_bet(mock_handle_roulette_bet):
    """Тест перенаправления на обработчик ставки рулетки."""
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.data = "roulette_bet:red:5"
    update.callback_query = query
    context = MagicMock()
    context.user_data = {} # Инициализируем user_data

    await casino_callback_handler(update, context)

    assert context.user_data['bet_amount'] == 5 # Проверяем сохранение ставки
    mock_handle_roulette_bet.assert_awaited_once_with(query, context, "red")
    query.answer.assert_not_called()

@pytest.mark.asyncio
async def test_casino_callback_handler_unknown():
    """Тест обработки неизвестного callback_data."""
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.data = "casino:unknown_action"
    query.answer = AsyncMock()
    update.callback_query = query
    context = MagicMock()
    
    await casino_callback_handler(update, context)
    
    query.answer.assert_awaited_once_with("❗ Неизвестная команда. Пожалуйста, попробуйте снова.", show_alert=True)

@pytest.mark.asyncio
@patch('casino.casino_main.handle_slots_callback', side_effect=Exception("Test Error"))
@patch('casino.casino_main.logging')
async def test_casino_callback_handler_exception(mock_logging, mock_handle_slots):
    """Тест обработки исключения внутри обработчика."""
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.data = "casino:slots"
    query.answer = AsyncMock()
    update.callback_query = query
    context = MagicMock()

    await casino_callback_handler(update, context)

    mock_handle_slots.assert_awaited_once() # Обработчик был вызван
    mock_logging.error.assert_called_once() # Ошибка залогирована
    query.answer.assert_awaited_once_with("❌ Произошла ошибка. Пожалуйста, попробуйте позже.", show_alert=True) 