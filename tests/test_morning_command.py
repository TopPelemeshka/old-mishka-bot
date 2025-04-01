import pytest
import os
import json
from unittest.mock import patch, MagicMock, mock_open, AsyncMock, call

# Импортируем тестируемые функции
try:
    from handlers.morning_command import (
        morning_command,
        load_morning_wishes,
        load_morning_index,
        save_morning_index,
        MORNING_WISHES_FILE,
        MORNING_INDEX_FILE
    )
except ImportError as e:
    pytest.skip(f"Пропуск тестов morning_command: не удалось импортировать модуль handlers.morning_command или его зависимости ({e}).", allow_module_level=True)

# --- Тесты для вспомогательных функций ---

@patch('os.path.exists')
@patch('builtins.open', new_callable=mock_open, read_data="Пожелание 1\nПожелание 2\n\nПожелание 3")
def test_load_morning_wishes(mock_file, mock_exists):
    """Тест загрузки пожеланий из файла"""
    # Устанавливаем, что файл существует
    mock_exists.return_value = True
    
    # Вызываем функцию и проверяем результат
    wishes = load_morning_wishes()
    assert wishes == ["Пожелание 1", "Пожелание 2", "Пожелание 3"]
    
    # Проверяем, что файл был открыт с правильными параметрами
    mock_file.assert_called_once_with(MORNING_WISHES_FILE, "r", encoding="utf-8")


@patch('os.path.exists')
@patch('builtins.open', new_callable=mock_open, read_data='{"morning_index": 3}')
def test_load_morning_index(mock_file, mock_exists):
    """Тест загрузки индекса из файла"""
    # Устанавливаем, что файл существует
    mock_exists.return_value = True
    
    # Вызываем функцию и проверяем результат
    index = load_morning_index()
    assert index == 3
    
    # Проверяем, что файл был открыт с правильными параметрами
    mock_file.assert_called_once_with(MORNING_INDEX_FILE, "r", encoding="utf-8")


@patch('builtins.open', new_callable=mock_open)
def test_save_morning_index(mock_file):
    """Тест сохранения индекса в файл"""
    # Вызываем функцию
    save_morning_index(5)
    
    # Проверяем, что файл был открыт с правильными параметрами
    mock_file.assert_called_once_with(MORNING_INDEX_FILE, "w", encoding="utf-8")
    
    # Проверяем, что в файл были записаны данные
    # json.dump делает несколько вызовов write, поэтому нельзя использовать assert_called_once
    assert mock_file().write.called
    
    # Проверяем, что все записанные данные в совокупности содержат нужную информацию
    written_data = ''.join(call[0][0] for call in mock_file().write.call_args_list)
    data = json.loads(written_data)
    assert data == {"morning_index": 5}

# --- Тесты для основной функции ---

@pytest.mark.asyncio
@patch('handlers.morning_command.load_morning_wishes')
@patch('handlers.morning_command.load_morning_index')
@patch('handlers.morning_command.save_morning_index')
async def test_morning_command_empty_wishes(mock_save_index, mock_load_index, mock_load_wishes):
    """Тест команды /morning когда список пожеланий пуст"""
    # Настраиваем мок для пустого списка пожеланий
    mock_load_wishes.return_value = []
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    update.effective_chat.id = 123
    
    # Вызываем тестируемую функцию
    await morning_command(update, context)
    
    # Проверяем, что бот отправил сообщение об отсутствии пожеланий
    context.bot.send_message.assert_awaited_once_with(
        chat_id=123,
        text="Пока нет пожеланий доброго утра. Попробуйте позже."
    )
    
    # Индекс не должен был сохраняться
    mock_save_index.assert_not_called()

@pytest.mark.asyncio
@patch('handlers.morning_command.load_morning_wishes')
@patch('handlers.morning_command.load_morning_index')
@patch('handlers.morning_command.save_morning_index')
async def test_morning_command_with_wishes(mock_save_index, mock_load_index, mock_load_wishes):
    """Тест команды /morning с пожеланиями"""
    # Настраиваем моки
    mock_load_wishes.return_value = ["Пожелание 1", "Пожелание 2", "Пожелание 3"]
    mock_load_index.return_value = 1  # Текущий индекс - 1 (второе пожелание)
    
    # Создаем моки для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot = AsyncMock()  # Используем AsyncMock для асинхронных методов
    update.effective_chat.id = 123
    
    # Вызываем тестируемую функцию
    await morning_command(update, context)
    
    # Проверяем, что бот отправил правильное пожелание
    context.bot.send_message.assert_awaited_once_with(
        chat_id=123,
        text="Пожелание 2"  # Индекс 1 соответствует второму пожеланию
    )
    
    # Проверяем, что индекс был сохранен с правильным значением (следующий индекс)
    mock_save_index.assert_called_once_with(2) 