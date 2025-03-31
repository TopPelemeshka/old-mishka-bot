import pytest
import asyncio
import json
import random
from unittest.mock import patch, mock_open, MagicMock, AsyncMock, call, ANY

# Импортируем тестируемый модуль и его функции
try:
    import casino.roulette as casino_roulette
    from casino.roulette import (
        load_file_ids,
        safe_delete_message,
        handle_roulette_bet_callback,
        handle_roulette_bet,
        handle_change_bet
    )
    # Импортируем зависимости для мокирования
    import balance
    import casino.roulette_utils as roulette_utils
    from telegram import Update, InlineKeyboardMarkup, User, CallbackQuery, Message, Chat
    from telegram.error import TimedOut
except ImportError as e:
    pytest.skip(f"Пропуск тестов roulette: не удалось импортировать модуль casino.roulette или его зависимости ({e}).", allow_module_level=True)

# --- Тесты для load_file_ids ---

@patch('builtins.open', new_callable=mock_open, read_data='{"animations": {"roulette": {"red": ["id1"], "black": ["id2"], "zero": ["id3"]}}}')
@patch('os.path.join', return_value='config/file_ids.json') # Мок пути
def test_load_file_ids_success(mock_join, mock_file):
    ids = load_file_ids()
    assert ids == {'animations': {'roulette': {'red': ['id1'], 'black': ['id2'], 'zero': ['id3']}}}
    mock_join.assert_called_once_with('config', 'file_ids.json')
    mock_file.assert_called_once_with('config/file_ids.json', 'r', encoding='utf-8')

@patch('builtins.open', side_effect=FileNotFoundError)
@patch('os.path.join', return_value='config/file_ids.json')
def test_load_file_ids_not_found(mock_join, mock_file):
    with pytest.raises(FileNotFoundError):
        load_file_ids()

@patch('builtins.open', new_callable=mock_open, read_data='invalid json')
@patch('os.path.join', return_value='config/file_ids.json')
def test_load_file_ids_invalid_json(mock_join, mock_file):
    with pytest.raises(json.JSONDecodeError):
        load_file_ids()

# --- Тесты для safe_delete_message ---

@pytest.mark.asyncio
async def test_safe_delete_message_success_first_try():
    message = MagicMock()
    message.delete = AsyncMock()
    await safe_delete_message(message)
    message.delete.assert_awaited_once()

@pytest.mark.asyncio
@patch('asyncio.sleep', return_value=None) # Мокаем sleep
async def test_safe_delete_message_success_second_try(mock_sleep):
    message = MagicMock()
    # Ошибка при первой попытке, успех при второй
    message.delete = AsyncMock(side_effect=[TimedOut(), None])
    
    await safe_delete_message(message, retries=3, delay=0.1)
    
    assert message.delete.await_count == 2
    mock_sleep.assert_awaited_once_with(0.1)

@pytest.mark.asyncio
@patch('asyncio.sleep', return_value=None)
@patch('builtins.print') # Мокаем print, чтобы не засорять вывод тестов
async def test_safe_delete_message_failure_all_retries(mock_print, mock_sleep):
    message = MagicMock()
    # Всегда ошибка
    message.delete = AsyncMock(side_effect=TimedOut())
    retries = 2
    
    await safe_delete_message(message, retries=retries, delay=0.1)
    
    assert message.delete.await_count == retries
    assert mock_sleep.await_count == retries
    # Проверяем, что было напечатано сообщение об ошибке в конце
    mock_print.assert_any_call("Не удалось удалить сообщение после нескольких попыток.")

# --- Тесты для handle_roulette_bet --- (Меню ставок)

@pytest.mark.asyncio
@patch('casino.roulette.get_balance', return_value=100)
async def test_handle_roulette_bet_display(mock_get_balance):
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.message = MagicMock(spec=Message)
    query.message.edit_text = AsyncMock()
    query.answer = AsyncMock()
    update.callback_query = query
    user = MagicMock(spec=User)
    user.id = 111
    update.effective_user = user
    
    context = MagicMock()
    context.user_data = {'bet_amount': 10} # Текущая ставка
    
    await handle_roulette_bet(update, context)
    
    mock_get_balance.assert_called_once_with(111)
    query.answer.assert_awaited_once()
    query.message.edit_text.assert_awaited_once()
    
    args, kwargs = query.message.edit_text.call_args
    assert "🎰 **Рулетка**" in args[0]
    assert "💰 **Ставка**: 10 монет" in args[0]
    # Проверяем расчет выигрыша для отображения (100 * (10 / 50) = 20, 1800 * (10/50) = 360)
    assert "- **Чёрное / Красное**: 20 монет" in args[0]
    assert "- **Зеро**: 360 монет" in args[0]
    assert kwargs['parse_mode'] == 'Markdown'
    
    # Проверяем клавиатуру
    assert isinstance(kwargs['reply_markup'], InlineKeyboardMarkup)
    keyboard = kwargs['reply_markup'].inline_keyboard
    assert len(keyboard) == 3
    assert keyboard[0][0].text == "⚫ Чёрное"
    assert keyboard[0][0].callback_data == "roulette_bet:black:10"
    assert keyboard[0][1].text == "🔴 Красное"
    assert keyboard[0][1].callback_data == "roulette_bet:red:10"
    assert keyboard[0][2].text == "🟢 Зеро"
    assert keyboard[0][2].callback_data == "roulette_bet:zero:10"
    assert keyboard[1][0].text == "💰 Ставка +5"
    assert keyboard[1][0].callback_data == "change_bet:+5"
    assert keyboard[1][1].text == "💰 Ставка -5"
    assert keyboard[1][1].callback_data == "change_bet:-5"
    assert keyboard[2][0].text == "🏠 В меню казино"
    assert keyboard[2][0].callback_data == "casino:menu"

# --- Тесты для handle_change_bet ---

@pytest.mark.asyncio
@patch('casino.roulette.get_balance', return_value=100)
@patch('casino.roulette.handle_roulette_bet') # Мокаем функцию отображения меню
async def test_handle_change_bet_increase(mock_handle_bet_display, mock_get_balance):
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.data = "change_bet:+5"
    update.callback_query = query
    user = MagicMock(spec=User)
    user.id = 222
    update.effective_user = user
    
    context = MagicMock()
    context.user_data = {'bet_amount': 10}
    
    await handle_change_bet(update, context)
    
    mock_get_balance.assert_called_once_with(222)
    assert context.user_data['bet_amount'] == 15 # Ставка увеличилась
    # Проверяем, что была вызвана функция для обновления меню
    mock_handle_bet_display.assert_awaited_once_with(update, context)

@pytest.mark.asyncio
@patch('casino.roulette.get_balance', return_value=100)
@patch('casino.roulette.handle_roulette_bet')
async def test_handle_change_bet_decrease(mock_handle_bet_display, mock_get_balance):
    # ... (аналогично, но с "change_bet:-5") ...
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.data = "change_bet:-5"
    update.callback_query = query
    user = MagicMock(spec=User)
    user.id = 222
    update.effective_user = user
    context = MagicMock()
    context.user_data = {'bet_amount': 10}
    
    await handle_change_bet(update, context)
    
    assert context.user_data['bet_amount'] == 5 # Ставка уменьшилась до минимума
    mock_handle_bet_display.assert_awaited_once_with(update, context)

@pytest.mark.asyncio
@patch('casino.roulette.get_balance', return_value=100)
@patch('casino.roulette.handle_roulette_bet')
async def test_handle_change_bet_min_limit(mock_handle_bet_display, mock_get_balance):
    # ... (уменьшаем ставку, которая уже минимальна) ...
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.data = "change_bet:-5"
    update.callback_query = query
    user = MagicMock(spec=User)
    user.id = 222
    update.effective_user = user
    context = MagicMock()
    context.user_data = {'bet_amount': 5} # Уже минимальная ставка

    await handle_change_bet(update, context)
    
    assert context.user_data['bet_amount'] == 5 # Ставка не изменилась
    mock_handle_bet_display.assert_awaited_once_with(update, context)

@pytest.mark.asyncio
@patch('casino.roulette.get_balance', return_value=20) # Низкий баланс
@patch('casino.roulette.handle_roulette_bet')
async def test_handle_change_bet_max_limit(mock_handle_bet_display, mock_get_balance):
    # ... (увеличиваем ставку, когда она почти равна балансу) ...
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.data = "change_bet:+5"
    update.callback_query = query
    user = MagicMock(spec=User)
    user.id = 222
    update.effective_user = user
    context = MagicMock()
    context.user_data = {'bet_amount': 18} # Близко к балансу

    await handle_change_bet(update, context)
    
    assert context.user_data['bet_amount'] == 20 # Ставка увеличилась до баланса
    mock_handle_bet_display.assert_awaited_once_with(update, context)

# --- Тесты для handle_roulette_bet_callback --- (Обработка результата)

@pytest.mark.asyncio
@patch('casino.roulette.get_balance')
@patch('casino.roulette.update_balance')
@patch('casino.roulette.get_roulette_result', return_value='red') # Результат - красное
@patch('casino.roulette.load_file_ids', return_value={'animations': {'roulette': {'red': ['gif_red']}}})
@patch('random.choice', return_value='gif_red')
@patch('casino.roulette.safe_delete_message', return_value=None)
@patch('asyncio.sleep', return_value=None)
async def test_handle_roulette_bet_callback_win_red(
    mock_sleep, mock_safe_delete, mock_random_choice, mock_load_ids, 
    mock_get_result, mock_update_balance, mock_get_balance
):
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.answer = AsyncMock()
    query.from_user = MagicMock(spec=User)
    query.from_user.id = 333
    query.message = MagicMock(spec=Message)
    query.message.chat = MagicMock(spec=Chat)
    query.message.chat.send_animation = AsyncMock(return_value=MagicMock()) # Мок отправки гифки
    query.message.edit_text = AsyncMock()
    bet = 50
    query.data = f"roulette_bet:red:{bet}" # Ставка на красное
    update.callback_query = query
    context = MagicMock()
    
    mock_get_balance.side_effect = [1000, 1000 - bet + (100 * (bet / 50))] # Баланс до, баланс после
    
    await handle_roulette_bet_callback(query, context, 'red')
    
    mock_get_balance.assert_called()
    mock_get_result.assert_called_once()
    mock_load_ids.assert_called_once()
    mock_random_choice.assert_called_once_with(['gif_red']) # Выбор гифки
    query.message.chat.send_animation.assert_awaited_once_with('gif_red')
    mock_sleep.assert_awaited_once_with(5.5)
    mock_safe_delete.assert_awaited_once() # Проверка удаления гифки
    
    # Проверка обновления баланса (списание + выигрыш)
    expected_winnings = int(100 * (bet / 50))
    mock_update_balance.assert_has_calls([call(333, -bet), call(333, expected_winnings)])
    
    # Проверка сообщения
    query.message.edit_text.assert_awaited_once()
    args, kwargs = query.message.edit_text.call_args
    assert f"Вы выиграли {expected_winnings} монет!" in args[0]
    assert f"Ваш текущий баланс*: {1000 - bet + expected_winnings}" in args[0]
    assert isinstance(kwargs['reply_markup'], InlineKeyboardMarkup)
    assert kwargs['parse_mode'] == 'Markdown'
    # ... (проверка кнопок) ...
    query.answer.assert_awaited_once()

# ... (Аналогичные тесты для выигрыша zero, проигрыша, недостатка баланса) ...

@pytest.mark.asyncio
@patch('casino.roulette.get_balance', return_value=10) # Недостаточно средств
async def test_handle_roulette_bet_callback_insufficient_funds(mock_get_balance):
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.answer = AsyncMock()
    query.from_user = MagicMock(spec=User)
    query.from_user.id = 444
    bet = 50
    query.data = f"roulette_bet:black:{bet}"
    update.callback_query = query
    context = MagicMock()

    await handle_roulette_bet_callback(query, context, 'black')
    
    mock_get_balance.assert_called_once_with(444)
    query.answer.assert_awaited_once_with("💸 У вас недостаточно средств для ставки.", show_alert=True)
    # Другие действия (отправка гифки, редактирование) не должны выполняться
    query.message.chat.send_animation.assert_not_called() 
    query.message.edit_text.assert_not_called() 