import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call

# Импортируем тестируемый модуль и его функции
try:
    import casino.slots as casino_slots
    from casino.slots import handle_slots_callback, handle_slots_bet_callback, SLOT_SYMBOLS
    # Импортируем зависимости для мокирования
    import balance
    from telegram import Update, InlineKeyboardMarkup, User, CallbackQuery
except ImportError as e:
    pytest.skip(f"Пропуск тестов slots: не удалось импортировать модуль casino.slots или его зависимости ({e}).", allow_module_level=True)

# --- Тесты для handle_slots_callback ---

@pytest.mark.asyncio
@patch('casino.slots.get_balance')
async def test_handle_slots_callback(mock_get_balance):
    query = MagicMock(spec=CallbackQuery)
    query.answer = AsyncMock()
    query.from_user = MagicMock(spec=User)
    query.from_user.id = 123
    query.edit_message_text = AsyncMock()
    
    context = MagicMock()
    context.user_data = {}
    
    # Устанавливаем баланс
    mock_get_balance.return_value = 200
    
    await handle_slots_callback(query, context)
    
    query.answer.assert_awaited_once()
    mock_get_balance.assert_called_once_with(123)
    
    # Проверяем расчет ставок (1%, 5%, 10% от 200)
    expected_bet_1 = 2 # 1% от 200
    expected_bet_5 = 10 # 5% от 200
    expected_bet_10 = 20 # 10% от 200
    
    # Проверяем сохранение ставки по умолчанию
    assert context.user_data['slots_bet'] == expected_bet_1
    
    # Проверяем отправленное сообщение и клавиатуру
    query.edit_message_text.assert_awaited_once()
    args, kwargs = query.edit_message_text.call_args
    assert args[0] == "Выберите ставку для слотов:"
    assert isinstance(kwargs['reply_markup'], InlineKeyboardMarkup)
    keyboard = kwargs['reply_markup'].inline_keyboard
    assert len(keyboard) == 3
    assert keyboard[0][0].text == f"Ставка 1% ({expected_bet_1} монет)"
    assert keyboard[0][0].callback_data == f"slots_bet:{expected_bet_1}"
    assert keyboard[1][0].text == f"Ставка 5% ({expected_bet_5} монет)"
    assert keyboard[1][0].callback_data == f"slots_bet:{expected_bet_5}"
    assert keyboard[2][0].text == f"Ставка 10% ({expected_bet_10} монет)"
    assert keyboard[2][0].callback_data == f"slots_bet:{expected_bet_10}"

@pytest.mark.asyncio
@patch('casino.slots.get_balance')
async def test_handle_slots_callback_low_balance(mock_get_balance):
    """Тест, что минимальная ставка равна 1, даже если % от баланса меньше."""
    query = MagicMock(spec=CallbackQuery)
    query.answer = AsyncMock()
    query.from_user = MagicMock(spec=User)
    query.from_user.id = 456
    query.edit_message_text = AsyncMock()
    
    context = MagicMock()
    context.user_data = {}
    mock_get_balance.return_value = 50 # Баланс, при котором 1% меньше 1
    
    await handle_slots_callback(query, context)
    
    # Проверяем расчет ставок (минимум 1)
    expected_bet_1 = 1 # max(int(50*0.01), 1)
    expected_bet_5 = 2 # max(int(50*0.05), 1)
    expected_bet_10 = 5 # max(int(50*0.1), 1)
    
    assert context.user_data['slots_bet'] == expected_bet_1
    
    args, kwargs = query.edit_message_text.call_args
    keyboard = kwargs['reply_markup'].inline_keyboard
    assert keyboard[0][0].text == f"Ставка 1% ({expected_bet_1} монет)"
    assert keyboard[0][0].callback_data == f"slots_bet:{expected_bet_1}"
    assert keyboard[1][0].text == f"Ставка 5% ({expected_bet_5} монет)"
    assert keyboard[1][0].callback_data == f"slots_bet:{expected_bet_5}"
    assert keyboard[2][0].text == f"Ставка 10% ({expected_bet_10} монет)"
    assert keyboard[2][0].callback_data == f"slots_bet:{expected_bet_10}"

# --- Тесты для handle_slots_bet_callback ---

@pytest.mark.asyncio
@patch('casino.slots.get_balance')
@patch('casino.slots.update_balance')
@patch('random.choice')
async def test_handle_slots_bet_jackpot(mock_random_choice, mock_update_balance, mock_get_balance):
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.answer = AsyncMock()
    query.from_user = MagicMock(spec=User)
    query.from_user.id = 777
    query.edit_message_text = AsyncMock()
    bet = 10
    query.data = f"slots_bet:{bet}"
    update.callback_query = query
    
    context = MagicMock()
    context.user_data = {}
    
    # Баланс до ставки, баланс после выигрыша
    mock_get_balance.side_effect = [100, 100 - bet + (bet * 5)]
    # Результат игры - джекпот
    mock_random_choice.return_value = "💎"
    
    await handle_slots_bet_callback(update, context)
    
    query.answer.assert_awaited_once()
    assert context.user_data['slots_bet'] == bet
    
    # Проверяем списание ставки и начисление выигрыша
    mock_update_balance.assert_has_calls([
        call(777, -bet), # Списание ставки
        call(777, bet * 5)  # Начисление выигрыша x5
    ])
    
    # Проверяем результат в сообщении
    query.edit_message_text.assert_awaited_once()
    args, kwargs = query.edit_message_text.call_args
    result_text = "💎 | 💎 | 💎"
    assert f"🎰 {result_text} 🎰" in args[0]
    assert f"Джекпот! Вы выиграли {bet * 5} монет!" in args[0]
    assert f"Ваш баланс: {100 - bet + (bet * 5)} монет." in args[0]
    # Проверяем кнопки
    assert isinstance(kwargs['reply_markup'], InlineKeyboardMarkup)
    keyboard = kwargs['reply_markup'].inline_keyboard
    assert keyboard[0][0].text == "🔄 Сыграть ещё раз"
    assert keyboard[0][0].callback_data == f"slots_bet:{bet}"
    assert keyboard[1][0].text == "🏠 В меню казино"
    assert keyboard[1][0].callback_data == "casino:menu"

@pytest.mark.asyncio
@patch('casino.slots.get_balance')
@patch('casino.slots.update_balance')
@patch('random.choice')
async def test_handle_slots_bet_two_match(mock_random_choice, mock_update_balance, mock_get_balance):
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    # ... (аналогичная настройка update/query/context) ...
    query.answer = AsyncMock()
    query.from_user = MagicMock(spec=User)
    query.from_user.id = 888
    query.edit_message_text = AsyncMock()
    bet = 5
    query.data = f"slots_bet:{bet}"
    update.callback_query = query
    context = MagicMock()
    context.user_data = {}

    mock_get_balance.side_effect = [50, 50 - bet + (bet * 2)]
    # Результат - два совпадения
    mock_random_choice.side_effect = ["🍒", "🍒", "🍋"]
    
    await handle_slots_bet_callback(update, context)
    
    mock_update_balance.assert_has_calls([
        call(888, -bet), 
        call(888, bet * 2)  # Выигрыш x2
    ])
    
    # Проверяем результат в сообщении
    args, kwargs = query.edit_message_text.call_args
    result_text = "🍒 | 🍒 | 🍋"
    assert f"🎰 {result_text} 🎰" in args[0]
    assert f"Две одинаковые! Вы выиграли {bet * 2} монет!" in args[0]
    assert f"Ваш баланс: {50 - bet + (bet * 2)} монет." in args[0]
    # ... (проверка кнопок) ...

@pytest.mark.asyncio
@patch('casino.slots.get_balance')
@patch('casino.slots.update_balance')
@patch('random.choice')
async def test_handle_slots_bet_no_match(mock_random_choice, mock_update_balance, mock_get_balance):
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    # ... (аналогичная настройка update/query/context) ...
    query.answer = AsyncMock()
    query.from_user = MagicMock(spec=User)
    query.from_user.id = 999
    query.edit_message_text = AsyncMock()
    bet = 20
    query.data = f"slots_bet:{bet}"
    update.callback_query = query
    context = MagicMock()
    context.user_data = {}

    mock_get_balance.side_effect = [200, 200 - bet]
    # Результат - нет совпадений
    mock_random_choice.side_effect = ["🔔", "🍀", "7️⃣"]
    
    await handle_slots_bet_callback(update, context)
    
    # Проверяем только списание ставки
    mock_update_balance.assert_called_once_with(999, -bet)
    
    # Проверяем результат в сообщении
    args, kwargs = query.edit_message_text.call_args
    result_text = "🔔 | 🍀 | 7️⃣"
    assert f"🎰 {result_text} 🎰" in args[0]
    assert f"Ничего не совпало. Вы проиграли {bet} монет." in args[0]
    assert f"Ваш баланс: {200 - bet} монет." in args[0]
    # ... (проверка кнопок) ...

@pytest.mark.asyncio
@patch('casino.slots.get_balance', return_value=5) # Баланс меньше ставки
@patch('casino.slots.update_balance')
async def test_handle_slots_bet_insufficient_balance(mock_update_balance, mock_get_balance):
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    # ... (настройка update/query/context) ...
    query.answer = AsyncMock()
    query.from_user = MagicMock(spec=User)
    query.from_user.id = 111
    query.edit_message_text = AsyncMock()
    bet = 10
    query.data = f"slots_bet:{bet}"
    update.callback_query = query
    context = MagicMock()
    context.user_data = {}
    
    await handle_slots_bet_callback(update, context)
    
    query.answer.assert_awaited_once()
    mock_get_balance.assert_called_once_with(111)
    mock_update_balance.assert_not_called() # Баланс не должен меняться
    # Проверяем сообщение об ошибке
    query.edit_message_text.assert_awaited_once_with("Недостаточно монет для этой ставки!")

@pytest.mark.asyncio
async def test_handle_slots_bet_invalid_data():
    """Тест на случай неверного формата callback_data."""
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.answer = AsyncMock()
    query.from_user = MagicMock(spec=User)
    query.from_user.id = 222
    query.edit_message_text = AsyncMock()
    query.data = "slots_bet:invalid" # Неверный формат ставки
    update.callback_query = query
    context = MagicMock()
    context.user_data = {}
    
    # Мокаем логгер, чтобы проверить запись об ошибке
    with patch('casino.slots.logging') as mock_logging:
        await handle_slots_bet_callback(update, context)
        
        query.answer.assert_awaited_once()
        query.edit_message_text.assert_not_called() # Сообщение не должно редактироваться
        mock_logging.error.assert_called_once() # Должна быть ошибка в логе 