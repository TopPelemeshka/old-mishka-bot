import pytest
from unittest.mock import patch, MagicMock, AsyncMock, ANY

# Импортируем тестируемые функции
try:
    from handlers.start_help import start, help_command
    # Импортируем зависимость для мокирования
    import utils
except ImportError as e:
    pytest.skip(f"Пропуск тестов start_help: не удалось импортировать модуль handlers.start_help или его зависимости ({e}).", allow_module_level=True)

# --- Тесты для start ---

@pytest.mark.asyncio
@patch('handlers.start_help.check_chat_and_execute') # Мокаем обертку
async def test_start(mock_check_chat):
    update = MagicMock()
    context = MagicMock()
    
    await start(update, context)
    
    # Проверяем, что check_chat_and_execute был вызван с правильными аргументами
    # ANY используется для внутренней функции _start, т.к. её сложно получить напрямую
    mock_check_chat.assert_awaited_once_with(update, context, ANY)
    
    # Получаем внутреннюю функцию _start, которая была передана в check_chat_and_execute
    _, _, internal_func = mock_check_chat.call_args[0]
    
    # Теперь тестируем внутреннюю функцию _start
    bot_mock = AsyncMock()
    context.bot = bot_mock
    update.effective_chat.id = 123 # Пример ID чата
    
    await internal_func(update, context)
    
    # Проверяем, что бот отправил сообщение с правильным текстом и параметрами
    expected_text = (
        "👋 Привет, дружище!\n\n"
        "Я – Мишка, помогу добавить ярких красок в чат!\n"
        "Вызывай <b>/help</b> для полного списка команд.\n\n"
        "ГООООООООООООООООООООООООООООООООЛ! 😄"
    )
    bot_mock.send_message.assert_awaited_once_with(
        chat_id=123,
        text=expected_text,
        parse_mode="HTML"
    )

# --- Тесты для help_command ---

@pytest.mark.asyncio
@patch('handlers.start_help.check_chat_and_execute')
async def test_help_command(mock_check_chat):
    update = MagicMock()
    context = MagicMock()

    await help_command(update, context)

    # Проверяем вызов обертки
    mock_check_chat.assert_awaited_once_with(update, context, ANY)
    
    # Получаем внутреннюю функцию _help
    _, _, internal_func = mock_check_chat.call_args[0]
    
    # Тестируем внутреннюю функцию _help
    bot_mock = AsyncMock()
    context.bot = bot_mock
    update.effective_chat.id = 456
    
    await internal_func(update, context)
    
    # Проверяем, что бот отправил сообщение помощи
    # Точное содержимое текста сверять не будем, но проверим ключевые моменты
    bot_mock.send_message.assert_awaited_once()
    args, kwargs = bot_mock.send_message.call_args
    assert kwargs['chat_id'] == 456
    assert "<b>Справка по командам бота</b>" in kwargs['text']
    assert "/start" in kwargs['text']
    assert "/help" in kwargs['text']
    assert "/roll" in kwargs['text']
    # ... можно добавить больше проверок на наличие команд
    assert kwargs['parse_mode'] == "HTML" 