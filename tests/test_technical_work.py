import pytest
from unittest.mock import patch, MagicMock, mock_open, AsyncMock

# Импортируем тестируемые функции
try:
    from handlers.technical_work import technical_work_command, POST_CHAT_ID
except ImportError as e:
    pytest.skip(f"Пропуск тестов technical_work: не удалось импортировать модуль handlers.technical_work или его зависимости ({e}).", allow_module_level=True)

@pytest.mark.asyncio
@patch('builtins.open', new_callable=mock_open)
async def test_technical_work_command_success(mock_file):
    """Тест успешного выполнения команды /technical_work"""
    # Настраиваем мок для файла
    mock_file_handle = MagicMock()
    mock_file.return_value.__enter__.return_value = mock_file_handle
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    
    # Вызываем тестируемую функцию
    await technical_work_command(update, context)
    
    # Проверяем, что файл был открыт с правильными параметрами
    mock_file.assert_called_once_with("pictures/technical_work.jpg", "rb")
    
    # Проверяем, что была вызвана функция отправки фото с правильными параметрами
    context.bot.send_photo.assert_awaited_once_with(
        chat_id=POST_CHAT_ID,
        photo=mock_file_handle,
        caption="⚙️ Ведутся технические работы, бот будет недоступен.\n\nГотовьтесь к обновлениям, отдыхайте, пока можете! 😄"
    )

@pytest.mark.asyncio
@patch('builtins.open')
@patch('logging.error')
async def test_technical_work_command_error(mock_logging, mock_open):
    """Тест обработки ошибки при выполнении команды /technical_work"""
    # Настраиваем мок для файла, чтобы он вызвал исключение
    mock_open.side_effect = Exception("Test error")
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    
    # Вызываем тестируемую функцию
    await technical_work_command(update, context)
    
    # Проверяем, что была вызвана функция логирования ошибки
    mock_logging.assert_called_once()
    args, _ = mock_logging.call_args
    assert "Test error" in args[0]
    
    # Проверяем, что была вызвана функция отправки сообщения об ошибке
    context.bot.send_message.assert_awaited_once_with(
        chat_id=POST_CHAT_ID,
        text="Ошибка: не удалось отправить сообщение о технических работах."
    ) 