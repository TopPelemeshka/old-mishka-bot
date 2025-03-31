import pytest
import json
import os
from unittest.mock import patch, mock_open, MagicMock

# Импортируем тестируемые функции и переменные из state.py
try:
    # Импортируем модуль целиком, чтобы можно было патчить его глобальные переменные
    import state
    from state import (
        load_state,
        save_state,
        STATE_FILE
    )
except ImportError:
    pytest.skip("Пропуск тестов state: не удалось импортировать модуль state.", allow_module_level=True)

# --- Тесты для load_state ---

# Используем фикстуру для сброса глобальных переменных state перед каждым тестом
@pytest.fixture(autouse=True)
def reset_state_globals():
    state.autopost_enabled = True
    state.quiz_enabled = True
    state.wisdom_enabled = True
    yield # Тест выполняется здесь
    # Можно добавить код очистки после теста, если нужно, но для этих флагов достаточно сброса перед тестом

@patch('os.path.exists', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data='{"autopost_enabled": false, "quiz_enabled": false, "wisdom_enabled": true}')
@patch('logging.getLogger') # Мокаем логгер
def test_load_state_success(mock_logger, mock_file_open, mock_exists):
    """Тестирует успешную загрузку состояния из файла."""
    load_state()
    mock_exists.assert_called_once_with(STATE_FILE)
    mock_file_open.assert_called_once_with(STATE_FILE, "r", encoding="utf-8")
    assert state.autopost_enabled is False
    assert state.quiz_enabled is False
    assert state.wisdom_enabled is True
    # Проверяем, что логирование было вызвано (опционально)
    mock_logger().info.assert_called()

@patch('os.path.exists', return_value=False)
@patch('builtins.open') # Убедимся, что open не вызывается
@patch('logging.getLogger')
def test_load_state_file_not_exists(mock_logger, mock_file_open, mock_exists):
    """Тестирует случай, когда файл состояния не существует (используются значения по умолчанию)."""
    # Сохраняем начальные значения перед вызовом
    initial_autopost = state.autopost_enabled
    initial_quiz = state.quiz_enabled
    initial_wisdom = state.wisdom_enabled
    
    load_state()
    
    mock_exists.assert_called_once_with(STATE_FILE)
    mock_file_open.assert_not_called()
    # Проверяем, что значения не изменились (остались значения по умолчанию)
    assert state.autopost_enabled == initial_autopost
    assert state.quiz_enabled == initial_quiz
    assert state.wisdom_enabled == initial_wisdom
    mock_logger().info.assert_not_called() # Логирование загрузки не должно происходить

@patch('os.path.exists', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data='{"autopost_enabled": false}') # Неполные данные
@patch('logging.getLogger')
def test_load_state_missing_keys(mock_logger, mock_file_open, mock_exists):
    """Тестирует загрузку с отсутствующими ключами в JSON (используются значения по умолчанию)."""
    load_state()
    mock_exists.assert_called_once_with(STATE_FILE)
    mock_file_open.assert_called_once_with(STATE_FILE, "r", encoding="utf-8")
    assert state.autopost_enabled is False # Загруженное значение
    assert state.quiz_enabled is True      # Значение по умолчанию
    assert state.wisdom_enabled is True    # Значение по умолчанию
    mock_logger().info.assert_called()

@patch('os.path.exists', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data='invalid json')
@patch('logging.getLogger')
def test_load_state_invalid_json(mock_logger, mock_file_open, mock_exists):
    """Тестирует случай с невалидным JSON в файле."""
    with pytest.raises(json.JSONDecodeError): # Ожидаем ошибку декодирования JSON
        load_state()
    mock_exists.assert_called_once_with(STATE_FILE)
    mock_file_open.assert_called_once_with(STATE_FILE, "r", encoding="utf-8")
    # Глобальные переменные не должны измениться, так как произошла ошибка до их присвоения
    assert state.autopost_enabled is True
    assert state.quiz_enabled is True
    assert state.wisdom_enabled is True
    mock_logger().info.assert_not_called() # Логирования успешной загрузки не было

@patch('os.path.exists', return_value=True)
@patch('builtins.open', side_effect=IOError("Test IO Error"))
@patch('logging.getLogger')
def test_load_state_read_error(mock_logger, mock_file_open, mock_exists):
    """Тестирует случай ошибки чтения файла."""
    with pytest.raises(IOError): # Ожидаем ошибку ввода/вывода
        load_state()
    mock_exists.assert_called_once_with(STATE_FILE)
    mock_file_open.assert_called_once_with(STATE_FILE, "r", encoding="utf-8")
    # Глобальные переменные не должны измениться
    assert state.autopost_enabled is True
    assert state.quiz_enabled is True
    assert state.wisdom_enabled is True
    mock_logger().info.assert_not_called()

# --- Тесты для save_state ---

@patch('builtins.open', new_callable=mock_open)
@patch('json.dump')
@patch('logging.getLogger') # Мокаем логгер
@patch('os.path.abspath', return_value='/fake/path/to/state_data/bot_state.json') # Мок для пути
def test_save_state_success(mock_abspath, mock_logger, mock_json_dump, mock_file_open):
    """Тестирует успешное сохранение состояния."""
    autopost_val = False
    quiz_val = True
    wisdom_val = False
    
    save_state(autopost_val, quiz_val, wisdom_val)
    
    # Проверяем вызов open
    mock_file_open.assert_called_once_with(STATE_FILE, "w", encoding="utf-8")
    handle = mock_file_open() # Получаем file handle
    
    # Проверяем данные, переданные в json.dump
    expected_data = {
        "autopost_enabled": autopost_val,
        "quiz_enabled": quiz_val,
        "wisdom_enabled": wisdom_val
    }
    mock_json_dump.assert_called_once_with(expected_data, handle, ensure_ascii=False, indent=4)
    
    # Проверяем логирование (опционально, но полезно)
    mock_logger().info.assert_any_call("save_state called: autopost_enabled=%s, quiz_enabled=%s, wisdom_enabled=%s", 
                                      autopost_val, quiz_val, wisdom_val)
    mock_logger().info.assert_any_call("Writing bot_state.json to: %s", mock_abspath.return_value)
    mock_abspath.assert_called_once_with(STATE_FILE)


@patch('builtins.open', side_effect=IOError("Test Write Error"))
@patch('logging.getLogger')
@patch('os.path.abspath', return_value='/fake/path/to/state_data/bot_state.json')
def test_save_state_write_error(mock_abspath, mock_logger, mock_file_open):
    """Тестирует ошибку записи файла при сохранении состояния."""
    with pytest.raises(IOError): # Ожидаем ошибку ввода/вывода
        save_state(True, True, True)
        
    mock_file_open.assert_called_once_with(STATE_FILE, "w", encoding="utf-8")
    # Логгирование попытки записи должно было произойти
    mock_logger().info.assert_any_call("save_state called: autopost_enabled=%s, quiz_enabled=%s, wisdom_enabled=%s", 
                                      True, True, True)
    mock_logger().info.assert_any_call("Writing bot_state.json to: %s", mock_abspath.return_value)


@patch('builtins.open', new_callable=mock_open) # Мок open успешен
@patch('json.dump', side_effect=TypeError("Test Serialization Error")) # Ошибка при сериализации
@patch('logging.getLogger')
@patch('os.path.abspath', return_value='/fake/path/to/state_data/bot_state.json')
def test_save_state_json_error(mock_abspath, mock_logger, mock_json_dump, mock_file_open):
    """Тестирует ошибку сериализации JSON при сохранении состояния."""
    with pytest.raises(TypeError): # Ожидаем ошибку TypeError от json.dump
        save_state(False, False, False)
        
    mock_file_open.assert_called_once_with(STATE_FILE, "w", encoding="utf-8")
    handle = mock_file_open()
    expected_data = {"autopost_enabled": False, "quiz_enabled": False, "wisdom_enabled": False}
    mock_json_dump.assert_called_once_with(expected_data, handle, ensure_ascii=False, indent=4)
    # Логгирование попытки записи должно было произойти
    mock_logger().info.assert_any_call("save_state called: autopost_enabled=%s, quiz_enabled=%s, wisdom_enabled=%s", 
                                      False, False, False)
    mock_logger().info.assert_any_call("Writing bot_state.json to: %s", mock_abspath.return_value) 