import pytest
import json
import sys
from unittest.mock import patch, MagicMock, AsyncMock

# Предварительно добавляем патчи для state и других модулей
sys.modules['state'] = MagicMock(betting_enabled=True)
sys.modules['config'] = MagicMock(POST_CHAT_ID=123, ADMIN_GROUP_ID=456)

# Импортируем тестируемые функции
try:
    from handlers.betting_commands import (
        bet_command,
        bet_option_callback,
        bet_amount_callback,
        history_command,
        publish_betting_event,
        process_betting_results,
        close_betting_event,
        start_betting_command,
        stop_betting_command,
        load_betting_events,  # Добавляем явный импорт для патчирования
        save_betting_events,  # Добавляем явный импорт для патчирования
        get_next_active_event,  # Добавляем явный импорт для патчирования
        betting_callback_handler,  # Добавляем явный импорт для патчирования
        results_command,
        results_callback_handler,
        get_betting_event_by_id
    )
    from betting import process_event_results
except ImportError as e:
    pytest.skip(f"Пропуск тестов betting_commands: не удалось импортировать модуль handlers.betting_commands или его зависимости ({e}).", allow_module_level=True)

# --- Тесты для bet_command ---

@pytest.mark.asyncio
@patch('handlers.betting_commands.load_betting_events')
@patch('handlers.betting_commands.place_bet')
async def test_bet_command_with_active_event(mock_place_bet, mock_load_events):
    """Тест команды /bet при наличии активных событий ставок"""
    # Настраиваем моки
    active_event = {
        "id": 1,
        "description": "Тестовое событие",
        "is_active": True,
        "options": [
            {"id": 1, "text": "Опция 1"},
            {"id": 2, "text": "Опция 2"},
            {"id": 3, "text": "Опция 3"}
        ],
        "users_bets": {}
    }
    mock_load_events.return_value = {"events": [active_event]}
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()
    update.effective_user.id = 123
    update.effective_user.username = "test_user"
    update.effective_chat.id = 456
    update.callback_query = None  # Указываем что нет callback_query
    
    # Вызываем тестируемую функцию
    await bet_command(update, context)
    
    # Проверяем, что load_betting_events был вызван
    mock_load_events.assert_called_once()
    
    # Проверяем, что было отправлено сообщение с активными событиями и кнопками
    context.bot.send_message.assert_awaited_once()
    args, kwargs = context.bot.send_message.await_args
    assert kwargs["chat_id"] == 456
    assert "выберите событие" in kwargs["text"].lower() or "активные события" in kwargs["text"].lower() or "ставки, господа" in kwargs["text"].lower()
    assert kwargs.get("reply_markup") is not None  # Проверяем наличие кнопок

@pytest.mark.asyncio
@patch('handlers.betting_commands.load_betting_events')
async def test_bet_command_no_active_events(mock_load_events):
    """Тест команды /bet при отсутствии активных событий ставок"""
    # Настраиваем моки - нет активных событий
    mock_load_events.return_value = {"events": [
        {"id": 1, "description": "Тестовое событие", "is_active": False}
    ]}
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()
    update.effective_user.id = 123
    update.effective_chat.id = 456
    update.callback_query = None  # Явно указываем, что callback_query отсутствует
    
    # Вызываем тестируемую функцию
    await bet_command(update, context)
    
    # Проверяем, что load_betting_events был вызван
    mock_load_events.assert_called_once()
    
    # Проверяем, что было отправлено сообщение об отсутствии активных событий
    context.bot.send_message.assert_awaited_once()
    args, kwargs = context.bot.send_message.await_args
    assert kwargs["chat_id"] == 456
    assert "нет активных" in kwargs["text"].lower() or "отсутствуют" in kwargs["text"].lower()

@pytest.mark.asyncio
@patch('handlers.betting_commands.load_betting_events')
async def test_bet_command_with_callback_query(mock_load_events):
    """Тест команды /bet через callback_query"""
    # Настраиваем моки
    mock_load_events.return_value = {"events": [
        {"id": 1, "is_active": True, "description": "Событие 1", 
         "question": "Вопрос 1", "options": [
             {"id": 1, "text": "Вариант 1"},
             {"id": 2, "text": "Вариант 2"}
         ]}
    ]}
    
    # Создаем моки для update и context с callback_query
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()
    update.effective_chat.id = 123
    
    # Настраиваем callback_query с AsyncMock
    query = AsyncMock()
    query.data = "bet_event_1"
    update.callback_query = query
    
    # Вызываем тестируемую функцию
    await bet_command(update, context)
    
    # Проверяем, что query.answer был вызван
    query.answer.assert_awaited_once()
    
    # Проверяем, что бот отправил сообщение с описанием события
    context.bot.send_message.assert_awaited_once()

# --- Тесты для bet_option_callback ---

@pytest.mark.asyncio
@patch('handlers.betting_commands.load_betting_events')
@patch('handlers.betting_commands.get_balance')
async def test_bet_option_callback(mock_get_balance, mock_load_events):
    """Тест колбэка выбора варианта ставки"""
    # Настраиваем моки
    mock_load_events.return_value = {"events": [
        {"id": 1, "is_active": True, "description": "Событие 1", 
         "options": [
             {"id": 1, "text": "Вариант 1"},
             {"id": 2, "text": "Вариант 2"}
         ]}
    ]}
    mock_get_balance.return_value = 100
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()
    context.user_data = {}
    update.effective_chat = MagicMock()
    update.effective_chat.id = 123
    
    # Настраиваем callback_query с AsyncMock
    query = AsyncMock()
    query.data = "bet_option_1_2"  # event_id=1, option_id=2
    query.message.message_id = 456
    query.edit_message_text = AsyncMock()
    update.callback_query = query
    update.effective_user.id = 123
    
    # Вызываем тестируемую функцию
    await bet_option_callback(update, context)
    
    # Проверяем, что query.answer был вызван
    query.answer.assert_awaited_once()
    
    # Проверяем, что контекст пользователя был обновлен
    assert context.user_data["bet_event_id"] == "1"
    assert context.user_data["bet_option_id"] == "2"
    assert context.user_data["event_message_id"] == 456
    
    # Проверяем, что была отправлена клавиатура с вариантами сумм ставок
    assert context.bot.send_message.called

@pytest.mark.asyncio
@patch('handlers.betting_commands.load_betting_events')
async def test_bet_option_callback_inactive_event(mock_load_events):
    """Тест колбэка выбора варианта для неактивного события"""
    # Настраиваем моки
    mock_load_events.return_value = {"events": [
        {"id": 1, "is_active": False, "description": "Событие 1", 
         "options": [
             {"id": 1, "text": "Вариант 1"},
             {"id": 2, "text": "Вариант 2"}
         ]}
    ]}
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    
    # Настраиваем callback_query с AsyncMock
    query = AsyncMock()
    query.data = "bet_option_1_2"  # event_id=1, option_id=2
    update.callback_query = query
    
    # Вызываем тестируемую функцию
    await bet_option_callback(update, context)
    
    # Проверяем, что query.answer был вызван с сообщением об ошибке
    assert query.answer.await_count >= 1
    args, kwargs = query.answer.await_args
    assert "не активно".lower() in kwargs["text"].lower()
    assert kwargs["show_alert"] is True

# --- Тесты для bet_amount_callback ---

@pytest.mark.asyncio
@patch('handlers.betting_commands.place_bet')
@patch('handlers.betting_commands.load_betting_events')
async def test_bet_amount_callback(mock_load_events, mock_place_bet):
    """Тест колбэка выбора суммы ставки"""
    # Настраиваем моки для функций
    mock_place_bet.return_value = True
    mock_load_events.return_value = {"events": [
        {"id": 1, "is_active": True, "description": "Событие 1"}
    ]}
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()
    context.user_data = {
        "bet_event_id": "1",
        "bet_option_id": "2",
        "event_message_id": 456
    }
    update.effective_chat = MagicMock()
    update.effective_chat.id = 123
    
    # Настраиваем callback_query с AsyncMock
    query = AsyncMock()
    query.data = "bet_amount_50"  # сумма=50
    query.message = MagicMock()
    query.message.message_id = 789
    update.callback_query = query
    update.effective_user.id = 123
    update.effective_user.username = "test_user"
    
    # Вызываем тестируемую функцию
    await bet_amount_callback(update, context)
    
    # Проверяем, что query.answer был вызван
    query.answer.assert_awaited_once()
    
    # Проверяем, что place_bet был вызван с корректными параметрами
    mock_place_bet.assert_called_once_with(123, "test_user", "1", "2", 50)
    
    # Проверяем, что было отправлено сообщение об успешной ставке
    context.bot.send_message.assert_awaited_once()
    args, kwargs = context.bot.send_message.await_args
    assert "ставка принята".lower() in kwargs["text"].lower() or "ставка" in kwargs["text"].lower()

@pytest.mark.asyncio
@patch('handlers.betting_commands.place_bet')
@patch('handlers.betting_commands.load_betting_events')
async def test_bet_amount_callback_failed(mock_load_events, mock_place_bet):
    """Тест колбэка выбора суммы ставки с ошибкой размещения"""
    # Настраиваем моки для функций
    mock_place_bet.return_value = False
    mock_load_events.return_value = {"events": [
        {"id": 1, "is_active": True, "description": "Событие 1"}
    ]}
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()
    context.user_data = {
        "bet_event_id": "1",
        "bet_option_id": "2",
        "event_message_id": 456
    }
    update.effective_chat = MagicMock()
    update.effective_chat.id = 123
    
    # Настраиваем callback_query с AsyncMock
    query = AsyncMock()
    query.data = "bet_amount_50"  # сумма=50
    query.message = MagicMock()
    query.message.message_id = 789
    update.callback_query = query
    update.effective_user.id = 123
    update.effective_user.username = "test_user"
    
    # Вызываем тестируемую функцию
    await bet_amount_callback(update, context)
    
    # Проверяем, что query.answer был вызван хотя бы один раз
    assert query.answer.await_count >= 1
    
    # Проверяем последний вызов, который должен содержать сообщение об ошибке
    # (поскольку place_bet вернул False)
    last_call = query.answer.await_args
    assert last_call is not None, "query.answer не был вызван"
    args, kwargs = last_call
    assert kwargs.get("show_alert", False) is True, "show_alert не установлен в True"
    assert "не удалось" in kwargs.get("text", "").lower() or "невозможно" in kwargs.get("text", "").lower() or "ошибка" in kwargs.get("text", "").lower(), f"Сообщение об ошибке не найдено в тексте: {kwargs.get('text', '')}"

# --- Тесты для history_command ---

@pytest.mark.asyncio
@patch('handlers.betting_commands.get_betting_history')
async def test_history_command_with_data(mock_get_history):
    """Тест команды /history с данными истории"""
    # Настраиваем моки
    mock_get_history.return_value = [
        {
            "event_id": 1,
            "description": "Событие 1",
            "question": "Вопрос 1",
            "winner_option": "Вариант 1",
            "total_bet": 100,
            "date": "2023-04-01",
            "winners": [
                {"user_id": 123, "user_name": "user1", "bet": 50, "win": 75}
            ],
            "losers": [
                {"user_id": 456, "user_name": "user2", "bet": 50}
            ]
        }
    ]
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()
    update.effective_chat.id = 123
    # Устанавливаем callback_query в None для прямого вызова команды
    update.callback_query = None
    
    # Вызываем тестируемую функцию
    await history_command(update, context)
    
    # Проверяем, что бот отправил сообщение с историей
    context.bot.send_message.assert_awaited_once()
    args, kwargs = context.bot.send_message.await_args
    assert kwargs["chat_id"] == 123
    assert "2023-04-01".lower() in kwargs["text"].lower()
    assert "событие 1".lower() in kwargs["text"].lower()

@pytest.mark.asyncio
@patch('handlers.betting_commands.get_betting_history')
async def test_history_command_empty(mock_get_history):
    """Тест команды /history с пустой историей"""
    # Настраиваем моки
    mock_get_history.return_value = []
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()
    update.effective_chat.id = 123
    # Устанавливаем callback_query в None для прямого вызова команды
    update.callback_query = None
    
    # Вызываем тестируемую функцию
    await history_command(update, context)
    
    # Проверяем, что бот отправил сообщение об отсутствии истории
    context.bot.send_message.assert_awaited_once()
    args, kwargs = context.bot.send_message.await_args
    assert kwargs["chat_id"] == 123
    assert ("пуста".lower() in kwargs["text"].lower() or "история".lower() in kwargs["text"].lower())

# --- Тесты для publish_betting_event ---

@pytest.mark.asyncio
async def test_publish_betting_event():
    """Тест публикации события ставок"""
    # Создаем мок для контекста
    context = MagicMock()
    context.bot = AsyncMock()
    context.job_queue = MagicMock()
    context.application = MagicMock()
    context.application.bot = context.bot
    
    # Патчим функции напрямую внутри теста для лучшего контроля
    with patch('betting.get_next_active_event') as mock_get_next, \
         patch.dict('sys.modules', {'state': MagicMock(betting_enabled=True)}), \
         patch('config.POST_CHAT_ID', 12345), \
         patch('config.schedule_config', {"betting": {}}):
        
        # Настраиваем моки
        mock_get_next.return_value = {
            "id": 1,
            "description": "Тестовое событие",
            "question": "Тестовый вопрос",
            "options": [
                {"id": 1, "text": "Вариант 1"},
                {"id": 2, "text": "Вариант 2"}
            ]
        }
        
        # Вызываем тестируемую функцию
        await publish_betting_event(context)
        
        # Проверяем, что get_next_active_event был вызван
        mock_get_next.assert_called_once()
        
        # Проверяем, что сообщение было отправлено
        context.application.bot.send_message.assert_called_once()
        assert context.application.bot.send_message.call_args[1]['chat_id'] == 12345

@pytest.mark.asyncio
async def test_publish_betting_event_no_events():
    """Тест публикации события ставок без активных событий"""
    # Создаем мок для контекста
    context = MagicMock()
    context.bot = AsyncMock()
    context.job_queue = MagicMock()
    context.application = MagicMock()
    context.application.bot = context.bot
    
    # Патчим функции напрямую внутри теста
    with patch('betting.get_next_active_event') as mock_get_next, \
         patch.dict('sys.modules', {'state': MagicMock(betting_enabled=True)}), \
         patch('config.schedule_config', {"betting": {}}):
        # Настраиваем моки
        mock_get_next.return_value = None
        
        # Вызываем тестируемую функцию
        await publish_betting_event(context)
        
        # Проверяем, что get_next_active_event был вызван
        mock_get_next.assert_called_once()
        
        # Проверяем, что сообщение НЕ было отправлено
        assert not context.application.bot.send_message.called

# --- Тесты для process_betting_results ---

@pytest.mark.asyncio
async def test_process_betting_results():
    """Тест обработки результатов ставки"""
    # Создаем мок для контекста
    context = MagicMock()
    context.bot = AsyncMock()
    context.job = MagicMock()
    context.job.data = {"event_id": 1}
    context.job_queue = MagicMock()
    context.application = MagicMock()
    context.application.bot = context.bot
    
    # Патчим функции напрямую внутри теста
    with patch('betting.load_betting_events') as mock_load_events, \
         patch('betting.process_event_results') as mock_process_results, \
         patch.dict('sys.modules', {'state': MagicMock(betting_enabled=True)}), \
         patch('config.POST_CHAT_ID', 123), \
         patch('config.ADMIN_GROUP_ID', 456):
        
        # Настраиваем моки
        event = {
            "id": 1,
            "description": "Тестовое событие",
            "question": "Вопрос?",
            "winner_option_id": 2,
            "is_active": False,  # Событие должно быть неактивным
            "options": [
                {"id": 1, "text": "Вариант 1"},
                {"id": 2, "text": "Вариант 2"}
            ],
            "result_description": "Победил вариант 2",
            "results_published": False
        }
        mock_load_events.return_value = {"events": [event]}
        
        # Настраиваем результат обработки ставок
        mock_process_results.return_value = {
            "status": "success",
            "winners": [
                {"user_id": 123, "user_name": "user1", "bet": 50, "win": 100}
            ],
            "losers": [
                {"user_id": 456, "user_name": "user2", "bet": 50}
            ],
            "total_bets": 100,
            "total_win": 100,
            "tote_coefficient": 2.0,
            "correct_option": {"text": "Вариант 2"}
        }
        
        # Вызываем тестируемую функцию
        await process_betting_results(context)
        
        # Проверяем, что load_betting_events был вызван
        mock_load_events.assert_called_once()
        
        # Проверяем, что process_event_results был вызван с правильными параметрами
        mock_process_results.assert_called_once_with(1, 2)
        
        # Проверяем, что сообщения были отправлены
        assert context.application.bot.send_message.called

@pytest.mark.asyncio
async def test_process_betting_results_event_not_found():
    """Тест обработки результатов с несуществующим событием"""
    # Создаем мок для контекста
    context = MagicMock()
    context.bot = AsyncMock()
    context.job = MagicMock()
    context.job.data = {"event_id": 1}
    context.application = MagicMock()
    context.application.bot = context.bot
    
    # Патчим функции напрямую внутри теста
    with patch('betting.load_betting_events') as mock_load_events, \
         patch.dict('sys.modules', {'state': MagicMock(betting_enabled=True)}), \
         patch('config.ADMIN_GROUP_ID', 456):
         
        # Настраиваем моки
        mock_load_events.return_value = {"events": []}
        
        # Вызываем тестируемую функцию
        await process_betting_results(context)
        
        # Проверяем, что load_betting_events был вызван
        mock_load_events.assert_called_once()
        
        # Проверяем, что было отправлено предупреждение администраторам
        assert context.application.bot.send_message.called

# --- Тесты для close_betting_event ---

@pytest.mark.asyncio
async def test_close_betting_event():
    """Тест закрытия события ставок"""
    # Создаем мок для контекста
    context = MagicMock()
    context.job = MagicMock()
    context.job.data = {"event_id": 1}
    context.application = MagicMock()
    
    # Используем патч внутри теста
    with patch('betting.load_betting_events') as mock_load_events, \
         patch('betting.save_betting_events') as mock_save_events, \
         patch('betting.publish_event') as mock_publish_event, \
         patch('handlers.betting_commands.publish_event', mock_publish_event), \
         patch.dict('sys.modules', {'state': MagicMock(betting_enabled=True)}):
         
        # Настраиваем моки
        event = {
            "id": 1,
            "description": "Тестовое событие",
            "is_active": True,  # Событие должно быть активным
            "results_published": False
        }
        mock_load_events.return_value = {"events": [event]}
        mock_publish_event.return_value = True
        
        # Вызываем тестируемую функцию
        await close_betting_event(context)
        
        # Проверяем, что load_betting_events был вызван
        assert mock_load_events.called
        
        # Проверяем, что publish_event был вызван с правильным ID
        mock_publish_event.assert_called_once_with(1)

@pytest.mark.asyncio
async def test_close_betting_event_not_found():
    """Тест закрытия несуществующего события"""
    # Создаем мок для контекста
    context = MagicMock()
    context.job = MagicMock()
    context.job.data = {"event_id": 1}
    context.application = MagicMock()
    
    # Используем патч внутри теста
    with patch('betting.load_betting_events') as mock_load_events, \
         patch.dict('sys.modules', {'state': MagicMock(betting_enabled=True)}):
        # Настраиваем моки
        mock_load_events.return_value = {"events": []}
        
        # Вызываем тестируемую функцию
        await close_betting_event(context)
        
        # Проверяем, что load_betting_events был вызван
        mock_load_events.assert_called_once()

# --- Тесты для start_betting_command ---

@pytest.mark.asyncio
async def test_start_betting_command():
    """Тест команды /startbetting для запуска событий ставок"""
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()
    update.effective_chat.id = 123
    
    # Патчим state с MagicMock
    with patch.dict('sys.modules', {'state': MagicMock(
                                                betting_enabled=False, 
                                                autopost_enabled=True, 
                                                quiz_enabled=True, 
                                                wisdom_enabled=True,
                                                save_state=MagicMock()
                                                )}):
        # Импортируем state внутри патча
        import state
        
        # Вызываем тестируемую функцию
        await start_betting_command(update, context)
        
        # Проверяем, что state.betting_enabled был изменен на True
        assert state.betting_enabled is True
        
        # Проверяем, что state.save_state был вызван
        assert state.save_state.called
        
        # Проверяем, что было отправлено сообщение об успешной активации
        context.bot.send_message.assert_awaited_once()
        args, kwargs = context.bot.send_message.await_args
        assert kwargs["chat_id"] == 123
        assert "включена" in kwargs["text"].lower()

# --- Тесты для stop_betting_command ---

@pytest.mark.asyncio
async def test_stop_betting_command():
    """Тест команды /stopbetting для остановки всех событий ставок"""
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()
    update.effective_chat.id = 123
    
    # Патчим state с MagicMock
    with patch.dict('sys.modules', {'state': MagicMock(
                                                betting_enabled=True, 
                                                autopost_enabled=True, 
                                                quiz_enabled=True, 
                                                wisdom_enabled=True,
                                                save_state=MagicMock()
                                                )}):
        # Импортируем state внутри патча
        import state
        
        # Вызываем тестируемую функцию
        await stop_betting_command(update, context)
        
        # Проверяем, что state.betting_enabled был изменен на False
        assert state.betting_enabled is False
        
        # Проверяем, что state.save_state был вызван
        assert state.save_state.called
        
        # Проверяем, что было отправлено сообщение об успешной деактивации
        context.bot.send_message.assert_awaited_once()
        args, kwargs = context.bot.send_message.await_args
        assert kwargs["chat_id"] == 123
        assert "отключена" in kwargs["text"].lower()

@pytest.mark.asyncio
@patch('handlers.betting_commands.load_betting_events')
@patch('handlers.betting_commands.place_bet')
async def test_betting_callback_handler(mock_place_bet, mock_load_events):
    """Тест обработчика callback для размещения ставок"""
    # Настраиваем моки
    active_event = {
        "id": 1,
        "description": "Тестовое событие",
        "is_active": True,
        "options": [
            {"id": 1, "text": "Опция 1"},
            {"id": 2, "text": "Опция 2"},
            {"id": 3, "text": "Опция 3"}
        ],
        "users_bets": {}
    }
    mock_load_events.return_value = {"events": [active_event]}
    
    # Подготавливаем данные колбэка в формате "event_1_option_2"
    # где 1 - ID события, 2 - индекс опции
    callback_data = "event_1_option_2"
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()
    
    # Используем AsyncMock для callback_query
    update.callback_query = AsyncMock()
    update.callback_query.data = callback_data
    update.callback_query.from_user.id = 123
    update.callback_query.from_user.username = "test_user"
    update.callback_query.message = MagicMock()
    update.callback_query.message.chat_id = 456
    
    # Настраиваем mock_place_bet
    mock_place_bet.return_value = True
    
    # Вызываем тестируемую функцию
    await betting_callback_handler(update, context)
    
    # Проверяем, что был вызван метод place_bet с правильными параметрами
    mock_place_bet.assert_called_once()
    args = mock_place_bet.call_args[0]
    assert args[0] == 123  # ID пользователя
    assert args[1] == "test_user"  # Имя пользователя
    
    # Проверяем, что callback_query был отвечен
    update.callback_query.answer.assert_awaited_once()
    
    # Проверяем, что было отправлено сообщение о принятии ставки
    context.bot.send_message.assert_awaited_once()
    args, kwargs = context.bot.send_message.await_args
    assert kwargs["chat_id"] == 456
    assert "ставка принята" in kwargs["text"].lower() or "ваша ставка" in kwargs["text"].lower()

@pytest.mark.asyncio
@patch('handlers.betting_commands.load_betting_events')
@patch('handlers.betting_commands.place_bet')
async def test_betting_callback_handler_invalid_data(mock_place_bet, mock_load_events):
    """Тест обработчика callback с некорректными данными"""
    # Настраиваем моки
    mock_load_events.return_value = {"events": []}
    
    # Подготавливаем некорректные данные колбэка
    callback_data = "invalid_format"
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()
    
    # Используем AsyncMock для callback_query
    update.callback_query = AsyncMock()
    update.callback_query.data = callback_data
    update.callback_query.from_user.id = 123
    update.callback_query.message = MagicMock()
    update.callback_query.message.chat_id = 456
    
    # Вызываем тестируемую функцию
    await betting_callback_handler(update, context)
    
    # Проверяем, что place_bet не был вызван
    mock_place_bet.assert_not_called()
    
    # Проверяем, что был отправлен ответ на callback с ошибкой
    update.callback_query.answer.assert_awaited_once()
    args, kwargs = update.callback_query.answer.await_args
    assert "ошибка" in args[0].lower() or "некорректный" in args[0].lower()

@pytest.mark.asyncio
@patch('handlers.betting_commands.get_next_active_event')
@patch('handlers.betting_commands.get_betting_event_by_id')
@patch('handlers.betting_commands.process_event_results')
async def test_results_command_with_active_event(mock_process_results, mock_get_betting_event, mock_get_next_event):
    """Тест команды /results с активным событием, ожидающим результатов"""
    # Настраиваем моки
    active_event = {
        "id": 1,
        "description": "Тестовое событие",
        "is_active": True,
        "options": [
            {"id": 1, "text": "Опция 1"},
            {"id": 2, "text": "Опция 2"},
            {"id": 3, "text": "Опция 3"}
        ],
        "users_bets": {"123": {"option": 1, "username": "test_user"}}
    }
    mock_get_next_event.return_value = active_event
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()
    update.message = MagicMock()
    update.message.chat_id = 456  # ID административного чата
    
    # Вызываем тестируемую функцию
    await results_command(update, context)
    
    # Проверяем, что был запрошен следующий активный ивент
    mock_get_next_event.assert_called_once()
    
    # Проверяем, что было отправлено сообщение с кнопками для выбора результата
    context.bot.send_message.assert_awaited_once()
    args, kwargs = context.bot.send_message.await_args
    assert kwargs["chat_id"] == 456
    assert "выберите результат" in kwargs["text"].lower() or "укажите результат" in kwargs["text"].lower()
    assert "reply_markup" in kwargs

@pytest.mark.asyncio
@patch('handlers.betting_commands.get_next_active_event')
async def test_results_command_no_active_events(mock_get_next_event):
    """Тест команды /results без активных событий"""
    # Настраиваем моки
    mock_get_next_event.return_value = None
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()
    update.message = MagicMock()
    update.message.chat_id = 456  # ID административного чата
    
    # Вызываем тестируемую функцию
    await results_command(update, context)
    
    # Проверяем, что был запрошен следующий активный ивент
    mock_get_next_event.assert_called_once()
    
    # Проверяем, что было отправлено сообщение об отсутствии активных событий
    context.bot.send_message.assert_awaited_once()
    args, kwargs = context.bot.send_message.await_args
    assert kwargs["chat_id"] == 456
    assert "нет активных событий" in kwargs["text"].lower()

@pytest.mark.asyncio
@patch('handlers.betting_commands.get_next_active_event')
@patch('handlers.betting_commands.get_betting_event_by_id')
@patch('handlers.betting_commands.process_event_results')
async def test_results_callback_handler(mock_process_results, mock_get_betting_event, mock_get_next_event):
    """Тест обработчика callback для результатов событий"""
    # Настраиваем моки
    active_event = {
        "id": 1,
        "description": "Тестовое событие",
        "is_active": True,
        "options": [
            {"id": 1, "text": "Опция 1"},
            {"id": 2, "text": "Опция 2"},
            {"id": 3, "text": "Опция 3"}
        ],
        "users_bets": {"123": {"option": 1, "username": "test_user"}}
    }
    mock_get_next_event.return_value = active_event
    mock_get_betting_event.return_value = active_event
    
    # Подготавливаем данные колбэка в формате "result_1_option_2"
    # где 1 - ID события, 2 - индекс опции-победителя
    callback_data = "result_1_option_2"
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()
    
    # Используем AsyncMock для callback_query
    update.callback_query = AsyncMock()
    update.callback_query.data = callback_data
    update.callback_query.message = MagicMock()
    update.callback_query.message.chat_id = 456
    
    # Вызываем тестируемую функцию
    await results_callback_handler(update, context)
    
    # Проверяем, что был вызван метод process_event_results с правильными параметрами
    mock_process_results.assert_called_once()
    args = mock_process_results.call_args[0]
    assert args[0] == "1"  # ID события в виде строки
    assert args[1] == "2"  # Индекс опции-победителя в виде строки
    
    # Проверяем, что callback_query был отвечен
    update.callback_query.answer.assert_awaited_once()
    
    # Проверяем, что было отправлено сообщение о обработке результатов
    assert context.bot.send_message.await_count >= 1

@pytest.mark.asyncio
@patch('handlers.betting_commands.get_next_active_event')
@patch('handlers.betting_commands.get_betting_event_by_id')
@patch('handlers.betting_commands.process_event_results')
async def test_results_callback_handler_invalid_data(mock_process_results, mock_get_betting_event, mock_get_next_event):
    """Тест обработчика callback для результатов с некорректными данными"""
    # Настраиваем неверный формат данных колбэка
    invalid_callback_data = "invalid_data_format"
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()
    
    # Используем AsyncMock для callback_query
    update.callback_query = AsyncMock()
    update.callback_query.data = invalid_callback_data
    update.callback_query.message = MagicMock()
    update.callback_query.message.chat_id = 456
    
    # Вызываем тестируемую функцию
    await results_callback_handler(update, context)
    
    # Проверяем, что process_event_results не вызывался
    mock_process_results.assert_not_called()
    
    # Проверяем, что callback_query был отвечен с сообщением об ошибке
    update.callback_query.answer.assert_awaited_once()
    args, kwargs = update.callback_query.answer.await_args
    assert "ошибка" in args[0].lower() or "некорректный" in args[0].lower()
    
    # Проверяем, что сообщение об ошибке было отправлено
    context.bot.send_message.assert_awaited_once()
    args, kwargs = context.bot.send_message.await_args
    assert kwargs["chat_id"] == 456
    assert "некорректный формат" in kwargs["text"].lower() or "ошибка" in kwargs["text"].lower()

@pytest.mark.asyncio
@patch('handlers.betting_commands.get_next_active_event')
@patch('handlers.betting_commands.get_betting_event_by_id')
@patch('handlers.betting_commands.process_event_results')
async def test_results_callback_handler_event_not_found(mock_process_results, mock_get_betting_event, mock_get_next_event):
    """Тест обработчика callback для результатов, когда событие не найдено"""
    # Настраиваем mock для get_betting_event_by_id, чтобы он возвращал None
    mock_get_betting_event.return_value = None
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()
    
    # Используем AsyncMock для callback_query
    update.callback_query = AsyncMock()
    update.callback_query.data = "result_123_option_1"  # Валидный формат, но несуществующий ID
    update.callback_query.message = MagicMock()
    update.callback_query.message.chat_id = 456
    
    # Вызываем тестируемую функцию
    await results_callback_handler(update, context)
    
    # Проверяем, что был вызван get_betting_event_by_id с правильным ID
    mock_get_betting_event.assert_called_once_with("123")
    
    # Проверяем, что process_event_results не вызывался
    mock_process_results.assert_not_called()
    
    # Проверяем, что callback_query был отвечен с сообщением об ошибке
    update.callback_query.answer.assert_awaited_once()
    args, kwargs = update.callback_query.answer.await_args
    assert "не найдено" in args[0].lower() or "не существует" in args[0].lower()
    
    # Проверяем, что сообщение об ошибке было отправлено
    context.bot.send_message.assert_awaited_once()
    args, kwargs = context.bot.send_message.await_args
    assert kwargs["chat_id"] == 456
    assert "не найдено" in kwargs["text"].lower() or "не существует" in kwargs["text"].lower() 