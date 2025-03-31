import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import logging

# Импортируем тестируемые функции
try:
    from handlers.all import all_command
    from config import MANUAL_USERNAMES
except ImportError as e:
    pytest.skip(f"Пропуск тестов all: не удалось импортировать модуль all ({e}).", allow_module_level=True)

# Тест для функции all_command (успешный случай)
@pytest.mark.asyncio
@patch('handlers.all.check_chat_and_execute')
async def test_all_command_execution(mock_check_chat):
    """Тест вызова check_chat_and_execute с корректной функцией"""
    # Создаем моки
    mock_update = MagicMock()
    mock_context = MagicMock()
    
    # Вызываем тестируемую функцию
    await all_command(mock_update, mock_context)
    
    # Проверяем, что check_chat_and_execute был вызван с правильными аргументами
    mock_check_chat.assert_called_once()
    # Первые два аргумента должны быть update и context
    assert mock_check_chat.call_args[0][0] == mock_update
    assert mock_check_chat.call_args[0][1] == mock_context
    # Третий аргумент должен быть функцией
    assert callable(mock_check_chat.call_args[0][2])

# Тест для вложенной функции _all_command с успешным получением администраторов
@pytest.mark.asyncio
async def test_all_command_with_admins():
    """Тест успешного получения списка администраторов и отправки сообщения"""
    # Создаем моки
    mock_update = MagicMock()
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    mock_update.effective_chat.id = 123456
    
    # Создаем список администраторов чата для возврата из getChatAdministrators
    admin1 = MagicMock()
    admin1.user.username = "admin1"
    admin1.user.first_name = "Admin First"
    admin1.user.id = 11111
    
    admin2 = MagicMock()
    admin2.user.username = None  # У этого админа нет username
    admin2.user.first_name = "No Username Admin"
    admin2.user.id = 22222
    
    mock_context.bot.getChatAdministrators.return_value = [admin1, admin2]
    
    # Получаем вложенную функцию _all_command
    from handlers.all import all_command
    # Мы не можем напрямую получить _all_command, поэтому мокаем check_chat_and_execute
    # чтобы извлечь её
    with patch('handlers.all.check_chat_and_execute') as mock_check:
        await all_command(mock_update, mock_context)
        _all_command = mock_check.call_args[0][2]
    
    # Теперь вызываем _all_command напрямую
    await _all_command(mock_update, mock_context)
    
    # Проверяем, что getChatAdministrators был вызван с правильным chat_id
    mock_context.bot.getChatAdministrators.assert_called_once_with(123456)
    
    # Проверяем, что send_message был вызван с правильными аргументами
    mock_context.bot.send_message.assert_called_once()
    call_args = mock_context.bot.send_message.call_args[1]
    assert call_args['chat_id'] == 123456
    assert '@admin1' in call_args['text']
    assert '<a href="tg://user?id=22222">No Username Admin</a>' in call_args['text']
    assert call_args['parse_mode'] == "HTML"
    assert call_args['disable_web_page_preview'] is True

# Тест для вложенной функции _all_command с ошибкой при получении администраторов
@pytest.mark.asyncio
async def test_all_command_error_getting_admins():
    """Тест обработки ошибки при получении списка администраторов"""
    # Создаем моки
    mock_update = MagicMock()
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    mock_update.effective_chat.id = 123456
    
    # Настраиваем getChatAdministrators, чтобы он вызывал исключение
    mock_context.bot.getChatAdministrators.side_effect = Exception("Не удалось получить админов")
    
    # Получаем вложенную функцию _all_command
    from handlers.all import all_command
    with patch('handlers.all.check_chat_and_execute') as mock_check:
        await all_command(mock_update, mock_context)
        _all_command = mock_check.call_args[0][2]
    
    # Вызываем _all_command напрямую
    await _all_command(mock_update, mock_context)
    
    # Проверяем, что была попытка получить администраторов
    mock_context.bot.getChatAdministrators.assert_called_once_with(123456)
    
    # Проверяем, что send_message был вызван с MANUAL_USERNAMES
    mock_context.bot.send_message.assert_called_once()
    call_args = mock_context.bot.send_message.call_args[1]
    assert call_args['chat_id'] == 123456
    # Проверяем, что в тексте сообщения используются MANUAL_USERNAMES
    for username in MANUAL_USERNAMES:
        assert username in call_args['text']

# Тест для вложенной функции _all_command с пустым списком администраторов
@pytest.mark.asyncio
async def test_all_command_empty_admins_list():
    """Тест обработки пустого списка администраторов"""
    # Создаем моки
    mock_update = MagicMock()
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    mock_update.effective_chat.id = 123456
    
    # Возвращаем пустой список администраторов
    mock_context.bot.getChatAdministrators.return_value = []
    
    # Получаем вложенную функцию _all_command
    from handlers.all import all_command
    with patch('handlers.all.check_chat_and_execute') as mock_check:
        await all_command(mock_update, mock_context)
        _all_command = mock_check.call_args[0][2]
    
    # Вызываем _all_command напрямую
    await _all_command(mock_update, mock_context)
    
    # Проверяем, что getChatAdministrators был вызван
    mock_context.bot.getChatAdministrators.assert_called_once_with(123456)
    
    # Проверяем, что send_message был вызван с MANUAL_USERNAMES
    mock_context.bot.send_message.assert_called_once()
    call_args = mock_context.bot.send_message.call_args[1]
    assert call_args['chat_id'] == 123456
    # Проверяем, что в тексте сообщения используются MANUAL_USERNAMES
    for username in MANUAL_USERNAMES:
        assert username in call_args['text'] 