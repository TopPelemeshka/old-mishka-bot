import pytest
import json
import os
from unittest.mock import patch, mock_open, MagicMock, AsyncMock

# Мокаем модуль config
config_mock = MagicMock()
config_mock.POST_CHAT_ID = 12345
config_mock.MATERIALS_DIR = "post_materials"
sys_modules_patcher = patch.dict('sys.modules', {'config': config_mock})
sys_modules_patcher.start()

# Импортируем тестируемые функции и переменные из wisdom.py
try:
    import wisdom
    from wisdom import (
        load_wisdoms,
        save_wisdoms,
        get_random_wisdom,
        wisdom_post_callback,
        start_wisdom_command,
        stop_wisdom_command,
        WISDOM_FILE  # Используем настоящую константу для патчинга путей
    )
    # Импортируем state для мокирования его переменных/функций
    import state 
except ImportError as e:
    pytest.skip(f"Пропуск тестов wisdom: не удалось импортировать модуль wisdom или его зависимости ({e}).", allow_module_level=True)

# --- Тесты для load_wisdoms ---

@patch('os.path.exists', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data='["Wisdom 1", "Wisdom 2"]')
def test_load_wisdoms_success(mock_file_open, mock_exists):
    """Тестирует успешную загрузку мудростей из JSON-файла."""
    wisdoms = load_wisdoms()
    mock_exists.assert_called_once_with(WISDOM_FILE)
    mock_file_open.assert_called_once_with(WISDOM_FILE, "r", encoding="utf-8")
    assert wisdoms == ["Wisdom 1", "Wisdom 2"]

@patch('os.path.exists', return_value=False)
def test_load_wisdoms_file_not_exists(mock_exists):
    """Тестирует случай, когда файл мудростей не существует."""
    wisdoms = load_wisdoms()
    mock_exists.assert_called_once_with(WISDOM_FILE)
    assert wisdoms == []

@patch('os.path.exists', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data='invalid json')
def test_load_wisdoms_invalid_json(mock_file_open, mock_exists):
    """Тестирует случай с невалидным JSON в файле (должен вернуть [])."""
    wisdoms = load_wisdoms()
    mock_exists.assert_called_once_with(WISDOM_FILE)
    mock_file_open.assert_called_once_with(WISDOM_FILE, "r", encoding="utf-8")
    assert wisdoms == [] # Ожидаем пустой список при ошибке

@patch('os.path.exists', return_value=True)
@patch('builtins.open', side_effect=IOError("Test Read Error"))
def test_load_wisdoms_read_error(mock_file_open, mock_exists):
    """Тестирует случай ошибки чтения файла (должен вернуть [])."""
    wisdoms = load_wisdoms()
    mock_exists.assert_called_once_with(WISDOM_FILE)
    mock_file_open.assert_called_once_with(WISDOM_FILE, "r", encoding="utf-8")
    assert wisdoms == [] # Ожидаем пустой список при ошибке

# --- Тесты для save_wisdoms ---

@patch('builtins.open', new_callable=mock_open)
@patch('json.dump')
def test_save_wisdoms_success(mock_json_dump, mock_file_open):
    """Тестирует успешное сохранение мудростей."""
    wisdoms_to_save = ["New Wisdom 1", "New Wisdom 2"]
    save_wisdoms(wisdoms_to_save)
    mock_file_open.assert_called_once_with(WISDOM_FILE, "w", encoding="utf-8")
    handle = mock_file_open() # Получаем file handle
    mock_json_dump.assert_called_once_with(wisdoms_to_save, handle, ensure_ascii=False, indent=4)

@patch('builtins.open', side_effect=IOError("Test Write Error"))
def test_save_wisdoms_write_error(mock_file_open):
    """Тестирует ошибку записи файла при сохранении."""
    with pytest.raises(IOError): # Ожидаем ошибку ввода/вывода
        save_wisdoms(["Wisdom"])
    mock_file_open.assert_called_once_with(WISDOM_FILE, "w", encoding="utf-8")

# --- Тесты для get_random_wisdom ---

@patch('wisdom.load_wisdoms')
@patch('wisdom.save_wisdoms')
@patch('random.choice', return_value="Chosen Wisdom")
def test_get_random_wisdom_success(mock_random_choice, mock_save_wisdoms, mock_load_wisdoms):
    """Тестирует успешное получение и удаление мудрости."""
    initial_wisdoms = ["Wisdom 1", "Chosen Wisdom", "Wisdom 3"]
    mock_load_wisdoms.return_value = initial_wisdoms.copy() # Возвращаем копию, т.к. список изменяется
    
    chosen = get_random_wisdom()
    
    assert chosen == "Chosen Wisdom"
    mock_load_wisdoms.assert_called_once()
    # Получаем копию списка без "Chosen Wisdom"
    expected_list = initial_wisdoms.copy()
    expected_list.remove("Chosen Wisdom")
    # Проверяем, что сохраняется список без выбранной мудрости
    mock_save_wisdoms.assert_called_once_with(expected_list)

@patch('wisdom.load_wisdoms', return_value=[])
@patch('wisdom.save_wisdoms')
@patch('random.choice')
def test_get_random_wisdom_empty_list(mock_random_choice, mock_save_wisdoms, mock_load_wisdoms):
    """Тестирует случай, когда список мудростей пуст."""
    chosen = get_random_wisdom()
    
    assert chosen is None
    mock_load_wisdoms.assert_called_once()
    mock_random_choice.assert_not_called()
    mock_save_wisdoms.assert_not_called()

# --- Тесты для wisdom_post_callback ---

@pytest.mark.asyncio
@patch('wisdom.state.wisdom_enabled', True)
@patch('wisdom.get_random_wisdom', return_value="Today's Wisdom")
@patch('wisdom.POST_CHAT_ID', 12345)
async def test_wisdom_post_callback_enabled_with_wisdom(mock_get_wisdom):
    """Тестирует колбэк, когда функция включена и есть мудрость."""
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    
    await wisdom_post_callback(context)
    
    mock_get_wisdom.assert_called_once()
    context.bot.send_message.assert_awaited_once_with(
        chat_id=12345,
        text="🦉 Мудрость дня:\n\nToday's Wisdom"
    )

@pytest.mark.asyncio
@patch('wisdom.state.wisdom_enabled', True)
@patch('wisdom.get_random_wisdom', return_value=None) # Мудрости закончились
@patch('wisdom.POST_CHAT_ID', 12345)
async def test_wisdom_post_callback_enabled_no_wisdom(mock_get_wisdom):
    """Тестирует колбэк, когда функция включена, но мудрости закончились."""
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    
    await wisdom_post_callback(context)
    
    mock_get_wisdom.assert_called_once()
    context.bot.send_message.assert_awaited_once_with(
        chat_id=12345,
        text="Мудрости дня закончились 😢"
    )

@pytest.mark.asyncio
@patch('wisdom.state.wisdom_enabled', False) # Функция отключена
@patch('wisdom.get_random_wisdom')
async def test_wisdom_post_callback_disabled(mock_get_wisdom):
    """Тестирует колбэк, когда функция отключена."""
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    
    await wisdom_post_callback(context)
    
    mock_get_wisdom.assert_not_called()
    context.bot.send_message.assert_not_awaited()

# --- Тесты для start_wisdom_command ---

@pytest.mark.asyncio
@patch('wisdom.state.save_state') # Мокаем функцию сохранения состояния
@patch('wisdom.state.autopost_enabled', True) # Пример других состояний
@patch('wisdom.state.quiz_enabled', True)
async def test_start_wisdom_command(mock_save_state):
    """Тестирует команду включения мудрости дня."""
    update = MagicMock()
    update.effective_chat.id = 9876
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    
    # Устанавливаем начальное состояние wisdom_enabled в False
    wisdom.state.wisdom_enabled = False 
    
    await start_wisdom_command(update, context)
    
    # Проверяем, что флаг изменился на True
    assert wisdom.state.wisdom_enabled is True
    # Проверяем, что save_state была вызвана с правильными аргументами
    mock_save_state.assert_called_once_with(True, True, True) # autopost, quiz, wisdom
    # Проверяем отправку сообщения
    context.bot.send_message.assert_awaited_once_with(
        chat_id=9876,
        text="Мудрость дня включена!"
    )

# --- Тесты для stop_wisdom_command ---

@pytest.mark.asyncio
@patch('wisdom.state.save_state') # Мокаем функцию сохранения состояния
@patch('wisdom.state.autopost_enabled', True) # Пример других состояний
@patch('wisdom.state.quiz_enabled', False)
async def test_stop_wisdom_command(mock_save_state):
    """Тестирует команду отключения мудрости дня."""
    update = MagicMock()
    update.effective_chat.id = 9876
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    
    # Устанавливаем начальное состояние wisdom_enabled в True
    wisdom.state.wisdom_enabled = True
    
    await stop_wisdom_command(update, context)
    
    # Проверяем, что флаг изменился на False
    assert wisdom.state.wisdom_enabled is False
    # Проверяем, что save_state была вызвана с правильными аргументами
    mock_save_state.assert_called_once_with(True, False, False) # autopost, quiz, wisdom
    # Проверяем отправку сообщения
    context.bot.send_message.assert_awaited_once_with(
        chat_id=9876,
        text="Мудрость дня отключена!"
    ) 