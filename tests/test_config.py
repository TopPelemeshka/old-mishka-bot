import pytest
import json
import os
import time
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock, call

# Импортируем тестируемый модуль и его функции/переменные
try:
    import config
    from config import load_config, reload_all_configs
except ImportError as e:
    pytest.skip(f"Пропуск тестов config: не удалось импортировать модуль config ({e}).", allow_module_level=True)

# Вспомогательная функция для создания мок-статистики файла
def create_mock_stat(mtime):
    mock_stat = MagicMock()
    mock_stat.st_mtime = mtime
    return mock_stat

# --- Тесты для load_config ---

@pytest.fixture(autouse=True)
def clear_config_cache():
    """Очищает внутренний кэш config перед каждым тестом."""
    config._config_cache.clear()
    config._config_mtime.clear()
    yield

@patch('pathlib.Path.stat')
@patch('pathlib.Path.exists', return_value=True)
def test_load_config_no_cache_first_time(mock_exists, mock_stat):
    """Тест первой загрузки с включенным кэшем."""
    config_file = "test_config.json"
    config_path = Path('config') / config_file
    mock_stat.return_value = create_mock_stat(100.0)

    # Сбрасываем кэш
    config._config_cache.clear()
    config._config_mtime.clear()

    # Мокаем функцию open и json.load
    m = mock_open(read_data='{"key": "value"}')
    expected_data = {"key": "value"}
    
    with patch('builtins.open', m), \
         patch('json.load', return_value=expected_data):
        data = load_config(config_file, use_cache=True)
        
        assert data == expected_data
        mock_stat.assert_called_once()
        m.assert_called_once_with(config_path, 'r', encoding='utf-8')
        # Проверяем, что кэш обновился
        assert config_file in config._config_cache
        assert config._config_cache[config_file] == expected_data
        assert config._config_mtime.get(config_file) == 100.0

@patch('pathlib.Path.stat')
@patch('pathlib.Path.exists', return_value=True)
def test_load_config_cache_hit(mock_exists, mock_stat):
    """Тест попадания в кэш (файл не изменился)."""
    config_file = "test_config.json"
    config_path = Path('config') / config_file
    
    # Сбрасываем и заполняем кэш начальными данными
    config._config_cache.clear()
    config._config_mtime.clear()
    expected_data = {"key": "value_cached"}
    config._config_cache[config_file] = expected_data
    config._config_mtime[config_file] = 100.0
    
    mock_stat.return_value = create_mock_stat(100.0) # Время не изменилось

    # Проверяем, что open и json.load не вызываются
    m = mock_open()
    with patch('builtins.open', m), \
         patch('json.load', side_effect=Exception("Этот код не должен быть вызван")):
        data = load_config(config_file, use_cache=True)

        assert data == expected_data # Должны получить значение из кэша
        mock_stat.assert_called_once()
        m.assert_not_called() # Файл не должен был читаться

@patch('pathlib.Path.stat')
@patch('pathlib.Path.exists', return_value=True)
def test_load_config_cache_miss_modified(mock_exists, mock_stat):
    """Тест промаха кэша (файл изменился)."""
    config_file = "test_config.json"
    config_path = Path('config') / config_file
    
    # Сбрасываем и заполняем кэш старым значением
    config._config_cache.clear()
    config._config_mtime.clear()
    config._config_cache[config_file] = {"key": "value_cached"}
    config._config_mtime[config_file] = 100.0
    
    expected_data = {"key": "value_new"}
    mock_stat.return_value = create_mock_stat(200.0) # Новое время модификации

    # Патчим открытие файла и чтение JSON
    m = mock_open(read_data='{"key": "value_new"}')
    with patch('builtins.open', m), \
         patch('json.load', return_value=expected_data):
        data = load_config(config_file, use_cache=True)

        assert data == expected_data # Должны получить новое значение из файла
        mock_stat.assert_called_once()
        m.assert_called_once_with(config_path, 'r', encoding='utf-8')
        # Проверяем обновление кэша
        assert config._config_cache[config_file] == expected_data
        assert config._config_mtime.get(config_file) == 200.0

@patch('pathlib.Path.stat')
@patch('pathlib.Path.exists', return_value=True)
def test_load_config_use_cache_false(mock_exists, mock_stat):
    """Тест загрузки с use_cache=False."""
    config_file = "test_config.json"
    config_path = Path('config') / config_file
    
    # Сбрасываем и заполняем кэш начальными данными
    config._config_cache.clear()
    config._config_mtime.clear()
    config._config_cache[config_file] = {"key": "value_cached"}
    config._config_mtime[config_file] = 100.0

    expected_data = {"key": "value_no_cache"}
    
    # Патчим открытие файла и чтение JSON
    m = mock_open(read_data='{"key": "value_no_cache"}')
    with patch('builtins.open', m), \
         patch('json.load', return_value=expected_data):
        data = load_config(config_file, use_cache=False)

        assert data == expected_data
        mock_stat.assert_not_called() # stat не должен вызываться при use_cache=False
        m.assert_called_once_with(config_path, 'r', encoding='utf-8')
        # Кэш не должен был измениться
        assert config._config_cache[config_file] == {"key": "value_cached"}
        assert config._config_mtime.get(config_file) == 100.0

@patch('pathlib.Path.exists', return_value=True)
def test_load_config_file_not_found_no_cache(mock_exists):
    """Тест FileNotFoundError при первой загрузке (нет в кэше)."""
    config_file = "non_existent.json"
    
    # Сбрасываем кэш
    config._config_cache.clear()
    config._config_mtime.clear()
    
    # Подготавливаем моки для имитации FileNotFoundError
    mock_stat = MagicMock(side_effect=FileNotFoundError("Stat failed"))
    mock_file = mock_open()
    mock_file.side_effect = FileNotFoundError("File not found")
    
    # Обращаемся напрямую к функции с патчами
    with patch('pathlib.Path.stat', mock_stat), \
         patch('builtins.open', mock_file):
        with pytest.raises(FileNotFoundError): # Ожидаем, что ошибка будет проброшена
            load_config(config_file, use_cache=True)
    
        # Проверяем, что stat вызывается при use_cache=True
        mock_stat.assert_called_once()

@patch('pathlib.Path.exists', return_value=True)
def test_load_config_file_not_found_with_cache(mock_exists):
    """Тест FileNotFoundError при обновлении, когда есть старое значение в кэше."""
    config_file = "flaky_config.json"
    
    # Сбрасываем и заполняем кэш старым значением
    config._config_cache.clear()
    config._config_mtime.clear()
    cached_data = {"key": "value_cached"}
    config._config_cache[config_file] = cached_data
    config._config_mtime[config_file] = 100.0

    # Патчим функции, которые будут вызывать исключения
    mock_stat = MagicMock(side_effect=FileNotFoundError("Stat failed"))
    mock_file = mock_open()
    mock_file.side_effect = FileNotFoundError("Open failed too")
    
    # Ожидаем, что будет возвращено значение из кэша, несмотря на ошибку stat/open
    with patch('pathlib.Path.stat', mock_stat), \
         patch('builtins.open', mock_file):
        data = load_config(config_file, use_cache=True)
        
        assert data == cached_data # Должны получить значение из кэша
        mock_stat.assert_called_once()
        # Проверяем, что open не был вызван, так как мы получили данные из кэша
        assert not mock_file.called

@patch('pathlib.Path.stat')
@patch('pathlib.Path.exists', return_value=True)
def test_load_config_invalid_json_no_cache(mock_exists, mock_stat):
    """Тест ошибки декодирования JSON при первой загрузке."""
    config_file = "bad_json.json"
    config_path = Path('config') / config_file
    mock_stat.return_value = create_mock_stat(100.0)

    # Сбрасываем кэш
    config._config_cache.clear()
    config._config_mtime.clear()

    # Мокаем чтение файла для имитации невалидного JSON
    m = mock_open(read_data='invalid json')
    json_error = json.JSONDecodeError("Invalid JSON", "", 0)
    
    with patch('builtins.open', m), \
         patch('json.load', side_effect=json_error):
        with pytest.raises(json.JSONDecodeError): # Ожидаем ошибку JSON при парсинге
            load_config(config_file, use_cache=True)
    
        # Проверяем, что файл был открыт
        m.assert_called_with(config_path, 'r', encoding='utf-8')

# --- Тесты для reload_all_configs --- 

@patch('config.load_config')
def test_reload_all_configs(mock_load_config):
    """Тестирует принудительную перезагрузку всех конфигураций."""
    
    # Убираем пропуск теста
    # import pytest
    # pytest.skip("Из-за использования глобальных переменных в config.py этот тест сложно реализовать корректно.")
    
    # # В реальном проекте нужно переработать архитектуру config.py, 
    # # чтобы он не использовал глобальные переменные напрямую,
    # # а предоставлял их через функции/классы с явной инициализацией 