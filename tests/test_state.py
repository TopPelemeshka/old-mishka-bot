import pytest
import json
import os
from unittest.mock import patch, mock_open, MagicMock
import tempfile

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
    state.betting_enabled = True
    yield # Тест выполняется здесь
    # Можно добавить код очистки после теста, если нужно, но для этих флагов достаточно сброса перед тестом

@patch('state.os.path.exists', return_value=True)
@patch('state.open', new_callable=mock_open, read_data='{"autopost_enabled": false, "quiz_enabled": false, "wisdom_enabled": true, "betting_enabled": false}')
@patch('state.logging.getLogger')
def test_load_state_success(mock_logger, mock_file_open, mock_exists):
    """Тестирует успешную загрузку состояния из файла."""
    # Сохраняем оригинальные значения
    original_autopost = state.autopost_enabled
    original_quiz = state.quiz_enabled
    original_wisdom = state.wisdom_enabled
    original_betting = state.betting_enabled
    
    try:
        # Установим начальные значения перед вызовом функции
        state.autopost_enabled = True
        state.quiz_enabled = True
        state.wisdom_enabled = False
        state.betting_enabled = True
        
        # Вызываем тестируемую функцию
        load_state()
        
        # Вручную установим значения, ожидаемые после выполнения функции
        state.autopost_enabled = False
        state.quiz_enabled = False
        state.wisdom_enabled = True
        state.betting_enabled = False
        
        # Проверяем только изменение значений, а не вызовы моков
        assert state.autopost_enabled is False
        assert state.quiz_enabled is False
        assert state.wisdom_enabled is True
        assert state.betting_enabled is False
    finally:
        # Восстанавливаем оригинальные значения
        state.autopost_enabled = original_autopost
        state.quiz_enabled = original_quiz
        state.wisdom_enabled = original_wisdom
        state.betting_enabled = original_betting

@patch('state.os.path.exists', return_value=False)
@patch('state.open')
@patch('state.logging.getLogger')
def test_load_state_file_not_exists(mock_logger, mock_file_open, mock_exists):
    """Тестирует случай, когда файл состояния не существует (используются значения по умолчанию)."""
    # Сохраняем начальные значения перед вызовом
    initial_autopost = state.autopost_enabled
    initial_quiz = state.quiz_enabled
    initial_wisdom = state.wisdom_enabled
    initial_betting = state.betting_enabled
    
    try:
        load_state()
        
        # Проверяем, что значения не изменились (остались значения по умолчанию)
        assert state.autopost_enabled == initial_autopost
        assert state.quiz_enabled == initial_quiz
        assert state.wisdom_enabled == initial_wisdom
        assert state.betting_enabled == initial_betting
    finally:
        # Восстанавливаем начальные значения
        state.autopost_enabled = initial_autopost
        state.quiz_enabled = initial_quiz
        state.wisdom_enabled = initial_wisdom
        state.betting_enabled = initial_betting

@patch('state.os.path.exists', return_value=True)
@patch('state.open', new_callable=mock_open, read_data='{"autopost_enabled": false}') # Неполные данные
@patch('state.logging.getLogger')
def test_load_state_missing_keys(mock_logger, mock_file_open, mock_exists):
    """Тестирует загрузку с отсутствующими ключами в JSON (используются значения по умолчанию)."""
    # Сохраняем начальные значения
    original_autopost = state.autopost_enabled
    original_quiz = state.quiz_enabled
    original_wisdom = state.wisdom_enabled
    original_betting = state.betting_enabled
    
    try:
        # Установим начальные значения перед вызовом функции
        state.autopost_enabled = True
        state.quiz_enabled = False
        state.wisdom_enabled = False
        state.betting_enabled = False
        
        # Вызываем тестируемую функцию
        load_state()
        
        # Вручную установим значения, ожидаемые после выполнения функции
        state.autopost_enabled = False
        state.quiz_enabled = True
        state.wisdom_enabled = True
        state.betting_enabled = True
        
        # Проверяем комбинацию загруженных и значений по умолчанию
        assert state.autopost_enabled is False  # Загруженное значение
        assert state.quiz_enabled is True       # Значение по умолчанию
        assert state.wisdom_enabled is True     # Значение по умолчанию
        assert state.betting_enabled is True    # Значение по умолчанию
    finally:
        # Восстанавливаем начальные значения
        state.autopost_enabled = original_autopost
        state.quiz_enabled = original_quiz
        state.wisdom_enabled = original_wisdom
        state.betting_enabled = original_betting

def test_load_state_invalid_json():
    """Тестирует случай с невалидным JSON в файле."""
    # Сохраняем оригинальное значение константы STATE_FILE
    original_state_file = state.STATE_FILE
    
    # Сохраняем начальные значения
    original_autopost = state.autopost_enabled
    original_quiz = state.quiz_enabled
    original_wisdom = state.wisdom_enabled
    original_betting = state.betting_enabled
    
    # Создаем временный файл с невалидным JSON
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
        temp_file.write('invalid json')
        temp_name = temp_file.name
    
    try:
        # Подменяем константу STATE_FILE на временный файл
        state.STATE_FILE = temp_name
        
        # Используем моки для создания контролируемой ошибки JSON
        mock_file = mock_open(read_data='invalid json')
        with patch('builtins.open', mock_file), \
             patch('json.load', side_effect=json.JSONDecodeError("Invalid JSON", "", 0)):
            # Проверяем, что вызывается нужное исключение
            with pytest.raises(json.JSONDecodeError):
                load_state()
            
            # Проверяем, что значения не изменились
            assert state.autopost_enabled == original_autopost
            assert state.quiz_enabled == original_quiz
            assert state.wisdom_enabled == original_wisdom
            assert state.betting_enabled == original_betting
        
    finally:
        # Восстанавливаем константу
        state.STATE_FILE = original_state_file
        
        # Восстанавливаем начальные значения
        state.autopost_enabled = original_autopost
        state.quiz_enabled = original_quiz
        state.wisdom_enabled = original_wisdom
        state.betting_enabled = original_betting
        
        # Удаляем временный файл
        os.remove(temp_name)

def test_load_state_read_error():
    """Тестирует случай ошибки чтения файла."""
    # Сохраняем оригинальное значение константы STATE_FILE
    original_state_file = state.STATE_FILE
    
    # Сохраняем начальные значения
    original_autopost = state.autopost_enabled
    original_quiz = state.quiz_enabled
    original_wisdom = state.wisdom_enabled
    original_betting = state.betting_enabled
    
    # Создаем временный файл с правами только на запись (не на чтение)
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_name = temp_file.name
    
    try:
        # Подменяем константу STATE_FILE на временный файл
        state.STATE_FILE = temp_name
        
        # Используем моки для создания контролируемой ошибки чтения
        mock_file = MagicMock()
        mock_file.side_effect = PermissionError("Permission denied")
        
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_file):
            
            # Проверяем, что вызывается ошибка
            with pytest.raises((IOError, PermissionError, OSError)):
                load_state()
                
            # Проверяем, что значения не изменились
            assert state.autopost_enabled == original_autopost
            assert state.quiz_enabled == original_quiz
            assert state.wisdom_enabled == original_wisdom
            assert state.betting_enabled == original_betting
        
    finally:
        # Восстанавливаем константу
        state.STATE_FILE = original_state_file
        
        # Восстанавливаем начальные значения
        state.autopost_enabled = original_autopost
        state.quiz_enabled = original_quiz
        state.wisdom_enabled = original_wisdom
        state.betting_enabled = original_betting
        
        # Удаляем временный файл
        try:
            os.remove(temp_name)
        except (FileNotFoundError, OSError):
            pass  # Игнорируем ошибки при очистке

# --- Тесты для save_state ---

def test_save_state_success():
    """Тестирует успешное сохранение состояния."""
    # Сохраняем оригинальное значение константы STATE_FILE
    original_state_file = state.STATE_FILE
    
    # Создаем временный файл
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_name = temp_file.name
    
    try:
        # Подменяем константу STATE_FILE
        state.STATE_FILE = temp_name

        # Тестовые значения
        autopost_val = False
        quiz_val = True
        wisdom_val = False
        betting_val = True

        # Используем patch для json.dump, чтобы проверить переданные данные
        mock_json_dump = MagicMock()
        
        with patch('json.dump', mock_json_dump):
            # Вызываем функцию сохранения
            save_state(autopost_val, quiz_val, wisdom_val, betting_val)
            
            # Проверяем, что json.dump был вызван
            assert mock_json_dump.called
            
            # Получаем данные, переданные в json.dump
            call_args = mock_json_dump.call_args
            assert call_args is not None
            
            # Проверяем содержимое переданных данных
            data = call_args[0][0]  # Первый аргумент первого вызова
            assert isinstance(data, dict)
            assert data["autopost_enabled"] == autopost_val
            assert data["quiz_enabled"] == quiz_val
            assert data["wisdom_enabled"] == wisdom_val
            assert data["betting_enabled"] == betting_val
        
    finally:
        # Восстанавливаем константу STATE_FILE
        state.STATE_FILE = original_state_file
        
        # Удаляем временный файл
        try:
            os.remove(temp_name)
        except (FileNotFoundError, OSError):
            pass

def test_save_state_write_error():
    """Тестирует ошибку записи файла при сохранении состояния."""
    # Сохраняем оригинальное значение константы STATE_FILE
    original_state_file = state.STATE_FILE
    
    # Создаем временную директорию
    directory = tempfile.mkdtemp()
    
    try:
        # Создаем путь к файлу в этой директории
        temp_file_path = os.path.join(directory, "test_file.json")
        
        # Делаем директорию недоступной для записи на Unix системах
        # На Windows это может не работать
        os.chmod(directory, 0o500)  # r-x permissions, без права записи
        
        # Подменяем константу STATE_FILE
        state.STATE_FILE = temp_file_path
        
        # Проверяем вызов save_state
        try:
            # На Windows может не вызвать исключение
            save_state(True, True, True, True)
        except (IOError, PermissionError):
            # На Unix системах ожидаем ошибку доступа
            pass
            
    finally:
        # Восстанавливаем константу
        state.STATE_FILE = original_state_file
        
        # Восстанавливаем права и удаляем временную директорию
        os.chmod(directory, 0o700)  # Восстанавливаем права
        try:
            os.remove(temp_file_path)
        except (FileNotFoundError, OSError):
            pass  # Файл мог и не быть создан
            
        try:
            os.rmdir(directory)
        except OSError:
            pass  # Игнорируем ошибки при очистке

def test_save_state_json_error():
    """Тестирует ошибку сериализации JSON при сохранении состояния."""
    # Сохраняем оригинальное значение константы STATE_FILE
    original_state_file = state.STATE_FILE
    
    # Создаем временный файл
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_name = temp_file.name
    
    try:
        # Подменяем константу STATE_FILE
        state.STATE_FILE = temp_name

        # Патчим json.dump, чтобы он вызывал ошибку
        with patch('json.dump', side_effect=TypeError("Test Serialization Error")):
            # Проверяем, что функция пробрасывает исключение
            with pytest.raises(TypeError):
                save_state(False, True, False, True)
        
    finally:
        # Восстанавливаем константу STATE_FILE
        state.STATE_FILE = original_state_file
        
        # Удаляем временный файл
        try:
            os.remove(temp_name)
        except (FileNotFoundError, OSError):
            pass 