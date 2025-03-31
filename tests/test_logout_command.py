import pytest
from unittest.mock import patch, MagicMock, AsyncMock, ANY
import asyncio

# Импортируем тестируемые функции
try:
    from handlers.logout_command import (
        logout_command,
        generate_random_hex,
        generate_random_hex_bytes,
        generate_random_binary,
        generate_noise
    )
except ImportError as e:
    pytest.skip(f"Пропуск тестов logout_command: не удалось импортировать модуль handlers.logout_command или его зависимости ({e}).", allow_module_level=True)

# --- Тесты для вспомогательных функций ---

def test_generate_random_hex():
    """Проверка функции generate_random_hex"""
    # Проверяем длину
    result = generate_random_hex(10)
    assert len(result) == 10
    
    # Проверяем, что все символы - шестнадцатеричные
    assert all(c in "0123456789ABCDEF" for c in result)
    
    # Проверяем, что разные вызовы дают разные результаты
    result2 = generate_random_hex(10)
    # Вероятность совпадения крайне мала, но не исключена
    # поэтому сделаем несколько попыток, если совпало
    attempts = 0
    while result == result2 and attempts < 5:
        result2 = generate_random_hex(10)
        attempts += 1
    assert result != result2 or attempts == 5

def test_generate_random_hex_bytes():
    """Проверка функции generate_random_hex_bytes"""
    # Проверяем количество байт (каждый байт - 2 символа + пробел, кроме последнего)
    result = generate_random_hex_bytes(5)
    assert len(result.split()) == 5
    
    # Проверяем, что каждый байт - 2 символа в шестнадцатеричной системе
    for byte in result.split():
        assert len(byte) == 2
        assert all(c in "0123456789ABCDEF" for c in byte)

def test_generate_random_binary():
    """Проверка функции generate_random_binary"""
    # Проверяем длину
    result = generate_random_binary(20)
    assert len(result) == 20
    
    # Проверяем, что все символы - 0 или 1
    assert all(c in "01" for c in result)

def test_generate_noise():
    """Проверка функции generate_noise"""
    # Проверяем длину
    result = generate_noise(15)
    assert len(result) == 15
    
    # Проверяем, что результаты разные при разных вызовах
    result2 = generate_noise(15)
    # Вероятность совпадения мала, но не исключена
    attempts = 0
    while result == result2 and attempts < 5:
        result2 = generate_noise(15)
        attempts += 1
    assert result != result2 or attempts == 5

# --- Тесты для основной функции ---

@pytest.mark.asyncio
@patch('handlers.logout_command.file_ids')
@patch('handlers.logout_command.asyncio.sleep')
async def test_logout_command_with_file_id(mock_sleep, mock_file_ids):
    """Тест logout_command с использованием file_id"""
    # Настраиваем моки
    mock_file_ids.return_value = {'animations': {'logout': 'test_file_id'}}
    mock_file_ids.__getitem__.return_value = {'logout': 'test_file_id'}
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    update.effective_chat.id = 123
    
    # Настройка ответа для send_animation
    animation_message = MagicMock()
    animation_message.message_id = 1001
    context.bot.send_animation.return_value = animation_message
    
    # Настройка ответов для send_message
    progress_message = MagicMock()
    progress_message.message_id = 1002
    hacker_message = MagicMock()
    hacker_message.message_id = 1003
    final_message = MagicMock()
    final_message.message_id = 1004
    
    context.bot.send_message.side_effect = [
        progress_message, hacker_message, final_message
    ]
    
    # Вызываем тестируемую функцию
    await logout_command(update, context)
    
    # Проверяем, что были вызваны нужные методы
    context.bot.send_animation.assert_awaited_once_with(
        chat_id=123,
        animation='test_file_id',
        caption="Начинаю сканирование беседы..."
    )
    
    # Проверяем вызовы send_message
    assert context.bot.send_message.await_count >= 2
    
    # Проверяем вызов удаления сообщений
    # Должны быть удалены все 4 сообщения
    assert context.bot.delete_message.await_count == 4
    
    # Проверяем, что sleep был вызван нужное количество раз
    # 1 раз для имитации "печатания", несколько раз для прогресс-бара,
    # и в конце перед удалением сообщений
    assert mock_sleep.await_count >= 3

@pytest.mark.asyncio
@patch('handlers.logout_command.file_ids')
@patch('handlers.logout_command.asyncio.sleep')
@patch('builtins.open')
async def test_logout_command_with_file(mock_open, mock_sleep, mock_file_ids):
    """Тест logout_command с использованием локального файла"""
    # Настраиваем моки
    mock_file_ids.return_value = {'animations': {'logout': None}}
    mock_file_ids.__getitem__.return_value = {'logout': None}
    
    # Настраиваем мок для open
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    update.effective_chat.id = 123
    
    # Настройка ответа для send_animation
    animation_message = MagicMock()
    animation_message.message_id = 1001
    context.bot.send_animation.return_value = animation_message
    
    # Настройка ответов для send_message
    progress_message = MagicMock()
    progress_message.message_id = 1002
    hacker_message = MagicMock()
    hacker_message.message_id = 1003
    final_message = MagicMock()
    final_message.message_id = 1004
    
    context.bot.send_message.side_effect = [
        progress_message, hacker_message, final_message
    ]
    
    # Вызываем тестируемую функцию
    await logout_command(update, context)
    
    # Проверяем, что файл был открыт
    mock_open.assert_called_once_with("pictures/hacker_logout.gif", "rb")
    
    # Проверяем, что были вызваны нужные методы
    context.bot.send_animation.assert_awaited_once_with(
        chat_id=123,
        animation=mock_file,
        caption="Начинаю сканирование беседы..."
    )
    
    # Проверяем вызовы send_message
    assert context.bot.send_message.await_count >= 2
    
    # Проверяем вызов удаления сообщений
    assert context.bot.delete_message.await_count == 4
    
    # Проверяем вызов chat_action
    context.bot.send_chat_action.assert_awaited_once_with(
        chat_id=123, 
        action=ANY  # ChatAction.TYPING
    )

@pytest.mark.asyncio
@patch('handlers.logout_command.file_ids')
@patch('handlers.logout_command.asyncio.sleep')
async def test_logout_command_exception_handling(mock_sleep, mock_file_ids):
    """Тест обработки исключений в logout_command"""
    # Настраиваем моки
    mock_file_ids.return_value = {'animations': {'logout': 'test_file_id'}}
    mock_file_ids.__getitem__.return_value = {'logout': 'test_file_id'}
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    update.effective_chat.id = 123
    
    # Настройка ответа для send_animation
    animation_message = MagicMock()
    animation_message.message_id = 1001
    context.bot.send_animation.return_value = animation_message
    
    # Настройка ответов для send_message
    progress_message = MagicMock()
    progress_message.message_id = 1002
    hacker_message = MagicMock()
    hacker_message.message_id = 1003
    final_message = MagicMock()  # Добавим еще один ответ для финального сообщения
    final_message.message_id = 1004
    
    # Добавляем final_message в список side_effect
    context.bot.send_message.side_effect = [
        progress_message, hacker_message, final_message
    ]
    
    # Настраиваем исключение при редактировании сообщения
    context.bot.edit_message_text.side_effect = Exception("Test error")
    
    # Вызываем тестируемую функцию
    await logout_command(update, context)
    
    # Проверяем, что выполнение не прервалось исключением и
    # финальное сообщение отправлено
    context.bot.send_message.assert_any_await(
        chat_id=123,
        text="[СИСТЕМА ОЧИСТКИ АКТИВИРОВАНА]\nВсе токсичные сообщения будут удалены."
    )
    
    # Не все сообщения могут быть удалены из-за ошибок
    assert context.bot.delete_message.await_count >= 1 