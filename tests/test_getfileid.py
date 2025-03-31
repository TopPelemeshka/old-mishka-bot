import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Импортируем тестируемые функции
try:
    from handlers.getfileid import getfileid_command, catch_animation_fileid
except ImportError as e:
    pytest.skip(f"Пропуск тестов getfileid: не удалось импортировать модуль handlers.getfileid или его зависимости ({e}).", allow_module_level=True)

@pytest.mark.asyncio
@patch('handlers.getfileid.check_chat_and_execute')
async def test_getfileid_command(mock_check_chat):
    """Тест команды /getfileid"""
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    
    # Вызываем тестируемую функцию
    await getfileid_command(update, context)
    
    # Проверяем, что была вызвана функция check_chat_and_execute
    mock_check_chat.assert_awaited_once()
    
    # Получаем внутреннюю функцию _getfileid_command
    _, _, internal_func = mock_check_chat.call_args[0]
    
    # Вызываем эту внутреннюю функцию для тестирования
    update.effective_chat.id = 123456
    await internal_func(update, context)
    
    # Проверяем, что бот отправил правильное сообщение
    context.bot.send_message.assert_awaited_once_with(
        chat_id=123456,
        text=(
            "Отправьте, пожалуйста, файл (например, GIF, фото или видео), "
            "для которого я должен получить его file_id."
        )
    )

@pytest.mark.asyncio
@patch('handlers.getfileid.logger')
async def test_catch_animation_fileid(mock_logger):
    """Тест обработчика catch_animation_fileid"""
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    
    # Настраиваем мок для анимации
    animation = MagicMock()
    animation.file_id = "test_animation_file_id"
    update.message.animation = animation
    update.effective_chat.id = 123456
    
    # Вызываем тестируемую функцию
    await catch_animation_fileid(update, context)
    
    # Проверяем, что бот отправил сообщение с правильным file_id
    context.bot.send_message.assert_awaited_once_with(
        chat_id=123456,
        text="Поймал file_id:\n<code>test_animation_file_id</code>\n\n",
        parse_mode="HTML"
    )
    
    # Проверяем, что был сделан вызов логгера с правильной информацией
    mock_logger.info.assert_called_once_with("Поймали file_id: test_animation_file_id")

@pytest.mark.asyncio
async def test_catch_animation_fileid_no_animation():
    """Тест обработчика catch_animation_fileid когда анимации нет"""
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    
    # Устанавливаем, что анимации нет
    update.message.animation = None
    
    # Вызываем тестируемую функцию
    await catch_animation_fileid(update, context)
    
    # Проверяем, что бот не отправлял сообщений
    context.bot.send_message.assert_not_awaited() 