import pytest
import time
from unittest.mock import patch, MagicMock, mock_open, AsyncMock

# Импортируем тестируемые функции
try:
    from handlers.coffee_mishka import (
        coffee_command,
        mishka_command,
        durka_command
    )
    # Импортируем модуль, чтобы иметь доступ к coffee_invocations
    import handlers.coffee_mishka
except ImportError as e:
    pytest.skip(f"Пропуск тестов coffee_mishka: не удалось импортировать модуль handlers.coffee_mishka или его зависимости ({e}).", allow_module_level=True)

# --- Тесты для coffee_command ---

@pytest.mark.asyncio
@patch('handlers.coffee_mishka.check_chat_and_execute')
@patch('builtins.open', new_callable=mock_open)
@patch('handlers.coffee_mishka.time.time')
async def test_coffee_command_normal(mock_time, mock_file, mock_check_chat):
    """Тест обычного вызова команды /coffee"""
    # Устанавливаем время
    mock_time.return_value = 100.0
    
    # Сбрасываем глобальный список вызовов
    handlers.coffee_mishka.coffee_invocations = []
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    
    # Вызываем тестируемую функцию
    await coffee_command(update, context)
    
    # Проверяем, что была вызвана функция check_chat_and_execute
    mock_check_chat.assert_awaited_once()
    
    # Получаем внутреннюю функцию _coffee_command, которая была передана
    # в check_chat_and_execute
    _, _, internal_func = mock_check_chat.call_args[0]
    
    # Вызываем эту функцию для тестирования
    await internal_func(update, context)
    
    # Проверяем, что файл был открыт с правильными параметрами
    mock_file.assert_called_once_with("pictures/coffee.jpg", "rb")
    
    # Проверяем, что была вызвана функция отправки фото
    context.bot.send_photo.assert_awaited_once()

@pytest.mark.asyncio
@patch('builtins.open', new_callable=mock_open)
@patch('handlers.coffee_mishka.time.time')
async def test_coffee_command_easter_egg(mock_time, mock_file):
    """Тест пасхалки при частом вызове команды /coffee"""
    # Устанавливаем время
    mock_time.return_value = 100.0
    
    # Имитируем частый вызов команды, добавляя записи в глобальный список
    # Важно - создаем новый список, чтобы не влиять на другие тесты
    handlers.coffee_mishka.coffee_invocations = [99.0, 99.5]  # Два вызова за последние 10 секунд
    
    # Создаем моки для update и context
    update = MagicMock()
    update.effective_chat = MagicMock()
    update.effective_chat.id = 123
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    
    # Вызываем тестируемую функцию, что должно привести к срабатыванию пасхалки
    await coffee_command(update, context)
    
    # Проверяем, что был открыт файл с "пасхальной" картинкой
    mock_file.assert_called_once_with("pictures/alcgaimer.jpg", "rb")
    
    # Проверяем, что была вызвана функция отправки фото с правильными параметрами
    context.bot.send_photo.assert_awaited_once_with(
        chat_id=123,
        photo=mock_file.return_value.__enter__.return_value
    )

@pytest.mark.asyncio
@patch('handlers.coffee_mishka.check_chat_and_execute')
@patch('handlers.coffee_mishka.time.time')
async def test_coffee_command_time_filter(mock_time, mock_check_chat):
    """Тест фильтрации устаревших записей о вызове команды /coffee"""
    # Устанавливаем текущее время
    mock_time.return_value = 100.0
    
    # Имитируем список с одним устаревшим вызовом и одним недавним
    # Важно: создаем новый список отдельно для этого теста
    handlers.coffee_mishka.coffee_invocations = [85.0, 99.0]  # Первый вызов более 10 сек назад, второй - недавно
    
    # Создаем моки для update и context
    update = MagicMock()
    update.effective_chat = MagicMock()
    update.effective_chat.id = 123
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    
    # Патчим вызов check_chat_and_execute, чтобы он просто возвращал None
    # Это предотвратит вызов внутренней функции с картинками
    mock_check_chat.return_value = None
    
    # Вызываем тестируемую функцию
    await coffee_command(update, context)
    
    # Проверяем, что старый вызов был отфильтрован
    assert 85.0 not in handlers.coffee_mishka.coffee_invocations  # старый вызов был отфильтрован

# --- Тесты для mishka_command ---

@pytest.mark.asyncio
@patch('handlers.coffee_mishka.check_chat_and_execute')
async def test_mishka_command(mock_check_chat):
    """Тест команды /mishka"""
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    
    # Вызываем тестируемую функцию
    await mishka_command(update, context)
    
    # Проверяем, что была вызвана функция check_chat_and_execute
    mock_check_chat.assert_awaited_once()
    
    # Получаем внутреннюю функцию _mishka_command
    _, _, internal_func = mock_check_chat.call_args[0]
    
    # Вызываем эту функцию для тестирования
    with patch('builtins.open', mock_open()) as mock_file:
        update.effective_chat.id = 456
        await internal_func(update, context)
        
        # Проверяем, что файл был открыт с правильными параметрами
        mock_file.assert_called_once_with("pictures/mishka.jpg", "rb")
        
        # Проверяем, что была вызвана функция отправки фото с правильными параметрами
        context.bot.send_photo.assert_awaited_once_with(
            chat_id=456,
            photo=mock_file.return_value.__enter__.return_value,
            caption="Это я! 🐻"
        )

# --- Тесты для durka_command ---

@pytest.mark.asyncio
@patch('handlers.coffee_mishka.check_chat_and_execute')
async def test_durka_command(mock_check_chat):
    """Тест команды /durka"""
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    
    # Вызываем тестируемую функцию
    await durka_command(update, context)
    
    # Проверяем, что была вызвана функция check_chat_and_execute
    mock_check_chat.assert_awaited_once()
    
    # Получаем внутреннюю функцию _durka_command
    _, _, internal_func = mock_check_chat.call_args[0]
    
    # Вызываем эту функцию для тестирования
    with patch('builtins.open', mock_open()) as mock_file:
        update.effective_chat.id = 789
        await internal_func(update, context)
        
        # Проверяем, что файл был открыт с правильными параметрами
        mock_file.assert_called_once_with("pictures/durka.jpg", "rb")
        
        # Проверяем, что была вызвана функция отправки фото с правильными параметрами
        context.bot.send_photo.assert_awaited_once_with(
            chat_id=789,
            photo=mock_file.return_value.__enter__.return_value
        ) 