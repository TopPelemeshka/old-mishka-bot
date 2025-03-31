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

@patch('builtins.open', new_callable=mock_open, read_data='{"key": "value"}')
@patch('pathlib.Path.stat')
@patch('pathlib.Path.exists', return_value=True) # Предполагаем, что Path существует
def test_load_config_no_cache_first_time(mock_exists, mock_stat, mock_file):
    """Тест первой загрузки с включенным кэшем."""
    config_file = "test_config.json"
    config_path = Path('config') / config_file
    mock_stat.return_value = create_mock_stat(100.0)

    data = load_config(config_file, use_cache=True)

    assert data == {"key": "value"}
    mock_stat.assert_called_once()
    mock_file.assert_called_once_with(config_path, 'r', encoding='utf-8')
    # Проверяем, что кэш обновился
    assert config_file in config._config_cache
    assert config._config_cache[config_file] == {"key": "value"}
    assert config._config_mtime.get(config_file) == 100.0

@patch('builtins.open', new_callable=mock_open, read_data='{"key": "value_new"}')
@patch('pathlib.Path.stat')
@patch('pathlib.Path.exists', return_value=True)
def test_load_config_cache_hit(mock_exists, mock_stat, mock_file):
    """Тест попадания в кэш (файл не изменился)."""
    config_file = "test_config.json"
    config_path = Path('config') / config_file
    # Сначала загружаем, чтобы заполнить кэш
    config._config_cache[config_file] = {"key": "value_cached"}
    config._config_mtime[config_file] = 100.0
    mock_stat.return_value = create_mock_stat(100.0) # Время не изменилось

    data = load_config(config_file, use_cache=True)

    assert data == {"key": "value_cached"} # Должны получить значение из кэша
    mock_stat.assert_called_once()
    mock_file.assert_not_called() # Файл не должен был читаться

@patch('builtins.open', new_callable=mock_open, read_data='{"key": "value_new"}')
@patch('pathlib.Path.stat')
@patch('pathlib.Path.exists', return_value=True)
def test_load_config_cache_miss_modified(mock_exists, mock_stat, mock_file):
    """Тест промаха кэша (файл изменился)."""
    config_file = "test_config.json"
    config_path = Path('config') / config_file
    # Заполняем кэш старым значением
    config._config_cache[config_file] = {"key": "value_cached"}
    config._config_mtime[config_file] = 100.0
    mock_stat.return_value = create_mock_stat(200.0) # Новое время модификации

    data = load_config(config_file, use_cache=True)

    assert data == {"key": "value_new"} # Должны получить новое значение из файла
    mock_stat.assert_called_once()
    mock_file.assert_called_once_with(config_path, 'r', encoding='utf-8')
    # Проверяем обновление кэша
    assert config._config_cache[config_file] == {"key": "value_new"}
    assert config._config_mtime.get(config_file) == 200.0

@patch('builtins.open', new_callable=mock_open, read_data='{"key": "value_no_cache"}')
@patch('pathlib.Path.stat')
@patch('pathlib.Path.exists', return_value=True)
def test_load_config_use_cache_false(mock_exists, mock_stat, mock_file):
    """Тест загрузки с use_cache=False."""
    config_file = "test_config.json"
    config_path = Path('config') / config_file
    # Заполняем кэш чем-то другим, чтобы убедиться, что он не используется
    config._config_cache[config_file] = {"key": "value_cached"}
    config._config_mtime[config_file] = 100.0

    data = load_config(config_file, use_cache=False)

    assert data == {"key": "value_no_cache"}
    mock_stat.assert_not_called() # stat не должен вызываться при use_cache=False
    mock_file.assert_called_once_with(config_path, 'r', encoding='utf-8')
    # Кэш не должен был измениться
    assert config._config_cache[config_file] == {"key": "value_cached"}
    assert config._config_mtime.get(config_file) == 100.0

@patch('builtins.open', side_effect=FileNotFoundError("File not found"))
@patch('pathlib.Path.stat', side_effect=FileNotFoundError("Stat failed"))
@patch('pathlib.Path.exists', return_value=True) # Допустим, exists вернул True, но потом ошибка
def test_load_config_file_not_found_no_cache(mock_exists, mock_stat, mock_file):
    """Тест FileNotFoundError при первой загрузке (нет в кэше)."""
    config_file = "non_existent.json"
    config_path = Path('config') / config_file
    
    with pytest.raises(FileNotFoundError): # Ожидаем, что ошибка будет проброшена
        load_config(config_file, use_cache=True)
        
    mock_stat.assert_called_once()
    # В текущей реализации open может быть вызван дважды при ошибке stat
    # Первый раз внутри try, второй раз в except Exception
    assert mock_file.call_count == 1 or mock_file.call_count == 2 
    assert config_file not in config._config_cache

@patch('builtins.open')
@patch('pathlib.Path.stat', side_effect=FileNotFoundError("Stat failed"))
@patch('pathlib.Path.exists', return_value=True)
def test_load_config_file_not_found_with_cache(mock_exists, mock_stat, mock_file):
    """Тест FileNotFoundError при обновлении, когда есть старое значение в кэше."""
    config_file = "flaky_config.json"
    config_path = Path('config') / config_file
    # Заполняем кэш старым значением
    cached_data = {"key": "value_cached"}
    config._config_cache[config_file] = cached_data
    config._config_mtime[config_file] = 100.0

    # Мокаем open, чтобы он тоже вызывал ошибку при второй попытке чтения в except
    mock_file.side_effect = FileNotFoundError("Open failed too")

    # Ожидаем, что будет возвращено значение из кэша, несмотря на ошибку stat/open
    data = load_config(config_file, use_cache=True)
    
    assert data == cached_data # Должны получить значение из кэша
    mock_stat.assert_called_once()
    # В текущей реализации может не вызываться open, так как функция возвращает из кэша при ошибке

@patch('builtins.open', new_callable=mock_open, read_data='invalid json')
@patch('pathlib.Path.stat')
@patch('pathlib.Path.exists', return_value=True)
def test_load_config_invalid_json_no_cache(mock_exists, mock_stat, mock_file):
    """Тест ошибки декодирования JSON при первой загрузке."""
    config_file = "bad_json.json"
    config_path = Path('config') / config_file
    mock_stat.return_value = create_mock_stat(100.0)

    with pytest.raises(json.JSONDecodeError): # Ожидаем ошибку JSON
        load_config(config_file, use_cache=True)
    
    mock_stat.assert_called_once()
    # Проверяем, что была хотя бы одна попытка открытия файла
    mock_file.assert_any_call(config_path, 'r', encoding='utf-8')

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