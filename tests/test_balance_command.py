import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Импортируем тестируемые функции
try:
    from handlers.balance_command import balance_command
    import balance  # для мокирования
except ImportError as e:
    pytest.skip(f"Пропуск тестов balance_command: не удалось импортировать модуль handlers.balance_command или его зависимости ({e}).", allow_module_level=True)

@pytest.mark.asyncio
@patch('handlers.balance_command.load_balances')
async def test_balance_command_empty(mock_load_balances):
    """Тест команды /balance когда баланс пуст"""
    # Настраиваем мок
    mock_load_balances.return_value = {}
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    update.effective_chat.id = 123
    
    # Вызываем тестируемую функцию
    await balance_command(update, context)
    
    # Проверяем, что бот отправил сообщение об отсутствии баланса
    context.bot.send_message.assert_awaited_once_with(
        chat_id=123,
        text="Баланс пока пуст."
    )

@pytest.mark.asyncio
@patch('handlers.balance_command.load_balances')
async def test_balance_command_with_users(mock_load_balances):
    """Тест команды /balance с несколькими пользователями"""
    # Настраиваем мок с данными о пользователях
    mock_balances = {
        "123456": {"name": "Пользователь1", "balance": 100},
        "789012": {"name": "Пользователь2", "balance": 200},
        "345678": {"name": "Пользователь3", "balance": 50}
    }
    mock_load_balances.return_value = mock_balances
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    update.effective_chat.id = 123
    
    # Вызываем тестируемую функцию
    await balance_command(update, context)
    
    # Проверяем, что бот отправил сообщение с правильным форматированием
    expected_text = "💰 Баланс участников:\n\n"
    expected_text += "Пользователь1: 100 💵\n"
    expected_text += "Пользователь2: 200 💵\n"
    expected_text += "Пользователь3: 50 💵\n"
    
    context.bot.send_message.assert_awaited_once_with(
        chat_id=123,
        text=expected_text
    )

@pytest.mark.asyncio
@patch('handlers.balance_command.load_balances')
async def test_balance_command_with_one_user(mock_load_balances):
    """Тест команды /balance с одним пользователем"""
    # Настраиваем мок с данными об одном пользователе
    mock_balances = {
        "123456": {"name": "Пользователь1", "balance": 100}
    }
    mock_load_balances.return_value = mock_balances
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    update.effective_chat.id = 123
    
    # Вызываем тестируемую функцию
    await balance_command(update, context)
    
    # Проверяем, что бот отправил сообщение с правильным форматированием
    expected_text = "💰 Баланс участников:\n\n"
    expected_text += "Пользователь1: 100 💵\n"
    
    context.bot.send_message.assert_awaited_once_with(
        chat_id=123,
        text=expected_text
    )

@pytest.mark.asyncio
@patch('handlers.balance_command.load_balances')
async def test_balance_command_with_zero_balance(mock_load_balances):
    """Тест команды /balance с нулевым балансом у пользователя"""
    # Настраиваем мок с данными о пользователе с нулевым балансом
    mock_balances = {
        "123456": {"name": "Пользователь1", "balance": 0}
    }
    mock_load_balances.return_value = mock_balances
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    update.effective_chat.id = 123
    
    # Вызываем тестируемую функцию
    await balance_command(update, context)
    
    # Проверяем, что бот отправил сообщение с правильным форматированием
    expected_text = "💰 Баланс участников:\n\n"
    expected_text += "Пользователь1: 0 💵\n"
    
    context.bot.send_message.assert_awaited_once_with(
        chat_id=123,
        text=expected_text
    ) 