import pytest
import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from telegram import Update, Chat
from telegram.ext import ContextTypes

# Предполагаем, что функции находятся в корневом модуле utils
# Если они в другом месте, нужно скорректировать импорт
try:
    from utils import (
        is_allowed_chat,
        check_chat_and_execute,
        random_time_in_range,
        parse_time_from_string,
    )
except ImportError:
    # Если тесты запускаются не из корня проекта, может потребоваться другая структура импорта
    # Например, если tests/ находится на одном уровне с папкой вашего бота (например, 'src')
    # from ..src import utils # или как называется ваша папка
    pytest.skip("Пропуск тестов utils: не удалось импортировать модуль utils. Убедитесь, что тесты запускаются из корня проекта или настройте PYTHONPATH.", allow_module_level=True)


# --- Тесты для is_allowed_chat ---

@patch('utils.ALLOWED_CHAT_IDS', {123, 456}) # Мокаем разрешенные ID
def test_is_allowed_chat_allowed():
    """Тестирует случай, когда чат разрешен."""
    assert is_allowed_chat(123) is True

@patch('utils.ALLOWED_CHAT_IDS', {123, 456})
def test_is_allowed_chat_not_allowed():
    """Тестирует случай, когда чат не разрешен."""
    assert is_allowed_chat(789) is False

# --- Тесты для check_chat_and_execute ---

@pytest.mark.asyncio
@patch('utils.is_allowed_chat', return_value=True) # Мокаем проверку чата (разрешен)
async def test_check_chat_and_execute_allowed(mock_is_allowed):
    """Тестирует выполнение обработчика, когда чат разрешен."""
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 123
    
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = AsyncMock() # Мок для асинхронных вызовов бота
    
    handler_func = AsyncMock() # Асинхронный мок для обработчика

    await check_chat_and_execute(update, context, handler_func)

    mock_is_allowed.assert_called_once_with(123)
    handler_func.assert_awaited_once_with(update, context) # Проверяем, что обработчик был вызван (и await)
    context.bot.send_message.assert_not_called() # Убеждаемся, что сообщение не отправлялось
    context.bot.leave_chat.assert_not_called() # Убеждаемся, что бот не пытался выйти

@pytest.mark.asyncio
@patch('utils.is_allowed_chat', return_value=False) # Мокаем проверку чата (не разрешен)
async def test_check_chat_and_execute_not_allowed(mock_is_allowed):
    """Тестирует поведение, когда чат не разрешен."""
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 789
    
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    context.bot.leave_chat = AsyncMock()
    
    handler_func = AsyncMock()

    await check_chat_and_execute(update, context, handler_func)

    mock_is_allowed.assert_called_once_with(789)
    handler_func.assert_not_awaited() # Обработчик не должен был вызваться
    context.bot.send_message.assert_awaited_once_with(chat_id=789, text="Извините, я могу работать только в разрешённых группах.")
    context.bot.leave_chat.assert_awaited_once_with(789) # Бот должен был попытаться выйти

@pytest.mark.asyncio
@patch('utils.is_allowed_chat', return_value=False)
@patch('utils.logger') # Мокаем логгер
async def test_check_chat_and_execute_not_allowed_leave_fails(mock_logger, mock_is_allowed):
    """Тестирует случай, когда чат не разрешен и попытка выхода вызывает ошибку."""
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 789
    
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    context.bot.leave_chat = AsyncMock(side_effect=Exception("Test Leave Error")) # Мок выхода с ошибкой
    
    handler_func = AsyncMock()

    await check_chat_and_execute(update, context, handler_func)

    mock_is_allowed.assert_called_once_with(789)
    handler_func.assert_not_awaited()
    context.bot.send_message.assert_awaited_once()
    context.bot.leave_chat.assert_awaited_once_with(789)
    mock_logger.error.assert_called_once() # Проверяем, что ошибка была залогирована

# --- Тесты для random_time_in_range ---

@patch('random.randint') # Мокаем генератор случайных чисел
def test_random_time_in_range(mock_randint):
    """Тестирует генерацию случайного времени с моком random.randint."""
    start_time = datetime.time(10, 0, 0)
    end_time = datetime.time(11, 0, 0)
    
    # Ожидаемое значение секунд для 10:30:00
    expected_seconds = 10 * 3600 + 30 * 60 + 0 
    mock_randint.return_value = expected_seconds 

    result_time = random_time_in_range(start_time, end_time)

    # Проверяем, что randint был вызван с правильными границами в секундах
    start_s = 10 * 3600
    end_s = 11 * 3600
    mock_randint.assert_called_once_with(start_s, end_s)
    
    assert result_time == datetime.time(10, 30, 0)

def test_random_time_in_range_boundaries():
     """Тестирует, что результат находится в пределах заданных границ (без мока random)."""
     # Этот тест не полностью детерминирован, но полезен для проверки логики границ
     start_time = datetime.time(18, 15, 0)
     end_time = datetime.time(18, 45, 0)
     for _ in range(10): # Запустим несколько раз для большей уверенности
         result = random_time_in_range(start_time, end_time)
         assert start_time <= result <= end_time

# --- Тесты для parse_time_from_string ---

def test_parse_time_from_string_valid():
    """Тестирует парсинг валидной строки времени."""
    assert parse_time_from_string("14:25") == datetime.time(14, 25)
    assert parse_time_from_string("00:00") == datetime.time(0, 0)
    assert parse_time_from_string("23:59") == datetime.time(23, 59)

def test_parse_time_from_string_invalid_format():
    """Тестирует парсинг невалидной строки (неверный формат)."""
    with pytest.raises(ValueError):
        parse_time_from_string("14-25")
    with pytest.raises(ValueError):
        parse_time_from_string("abc")
    with pytest.raises(ValueError): # Ожидаем ValueError, а не IndexError
        parse_time_from_string("14:") 

def test_parse_time_from_string_invalid_values():
    """Тестирует парсинг строки с невалидными значениями времени."""
    with pytest.raises(ValueError):
        parse_time_from_string("24:00")
    with pytest.raises(ValueError):
        parse_time_from_string("10:60") 