import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Импортируем тестируемые функции
try:
    from handlers.chatid import chatid_command
except ImportError as e:
    pytest.skip(f"Пропуск тестов chatid: не удалось импортировать модуль handlers.chatid или его зависимости ({e}).", allow_module_level=True)

@pytest.mark.asyncio
@patch('handlers.chatid.check_chat_and_execute')
@patch('handlers.chatid.logger')
async def test_chatid_command(mock_logger, mock_check_chat):
    """Тест команды /chatid"""
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    
    # Вызываем тестируемую функцию
    await chatid_command(update, context)
    
    # Проверяем, что была вызвана функция check_chat_and_execute
    mock_check_chat.assert_awaited_once()
    
    # Получаем внутреннюю функцию _chatid_command
    _, _, internal_func = mock_check_chat.call_args[0]
    
    # Вызываем эту внутреннюю функцию для тестирования
    update.effective_chat.id = 123456
    await internal_func(update, context)
    
    # Проверяем, что бот отправил сообщение с правильным ID
    context.bot.send_message.assert_awaited_once_with(
        chat_id=123456,
        text="Chat ID: 123456"
    )
    
    # Проверяем, что был сделан вызов логгера с правильной информацией
    mock_logger.info.assert_called_once_with("Chat ID: 123456")

@pytest.mark.asyncio
@patch('handlers.chatid.check_chat_and_execute')
async def test_chatid_command_with_negative_id(mock_check_chat):
    """Тест команды /chatid с отрицательным ID чата (группа)"""
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    
    # Вызываем тестируемую функцию
    await chatid_command(update, context)
    
    # Получаем внутреннюю функцию _chatid_command
    _, _, internal_func = mock_check_chat.call_args[0]
    
    # Вызываем эту внутреннюю функцию для тестирования с отрицательным ID (характерно для групповых чатов)
    update.effective_chat.id = -1001234567890
    await internal_func(update, context)
    
    # Проверяем, что бот отправил сообщение с правильным ID
    context.bot.send_message.assert_awaited_once_with(
        chat_id=-1001234567890,
        text="Chat ID: -1001234567890"
    ) 