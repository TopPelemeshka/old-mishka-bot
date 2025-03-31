import pytest
import json
import os
from unittest.mock import patch, mock_open, MagicMock

# Импортируем тестируемые функции из balance.py
# Предполагаем, что тесты запускаются из корня проекта
try:
    from balance import (
        load_balances,
        save_balances,
        get_balance,
        update_balance,
        BALANCE_FILE # Импортируем константу, чтобы использовать в моках
    )
except ImportError:
    pytest.skip("Пропуск тестов balance: не удалось импортировать модуль balance.", allow_module_level=True)

# --- Тесты для load_balances ---

@patch('os.path.exists', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data='{"123": {"balance": 100, "name": "User1"}, "456": {"balance": 50, "name": "User2"}}')
def test_load_balances_success(mock_file_open, mock_exists):
    """Тестирует успешную загрузку балансов из существующего файла."""
    balances = load_balances()
    mock_exists.assert_called_once_with(BALANCE_FILE)
    mock_file_open.assert_called_once_with(BALANCE_FILE, "r", encoding="utf-8")
    assert balances == {"123": {"balance": 100, "name": "User1"}, "456": {"balance": 50, "name": "User2"}}

@patch('os.path.exists', return_value=False)
def test_load_balances_file_not_exists(mock_exists):
    """Тестирует случай, когда файл балансов не существует."""
    balances = load_balances()
    mock_exists.assert_called_once_with(BALANCE_FILE)
    assert balances == {}

@patch('os.path.exists', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data='invalid json')
@patch('logging.error') # Мокаем логгер ошибок
def test_load_balances_invalid_json(mock_log_error, mock_file_open, mock_exists):
    """Тестирует случай с невалидным JSON в файле."""
    balances = load_balances()
    mock_exists.assert_called_once_with(BALANCE_FILE)
    mock_file_open.assert_called_once_with(BALANCE_FILE, "r", encoding="utf-8")
    assert balances == {}
    mock_log_error.assert_called_once() # Проверяем, что ошибка была залогирована

@patch('os.path.exists', return_value=True)
@patch('builtins.open', side_effect=IOError("Test IO Error"))
@patch('logging.error')
def test_load_balances_read_error(mock_log_error, mock_file_open, mock_exists):
    """Тестирует случай ошибки чтения файла."""
    balances = load_balances()
    mock_exists.assert_called_once_with(BALANCE_FILE)
    mock_file_open.assert_called_once_with(BALANCE_FILE, "r", encoding="utf-8")
    assert balances == {}
    mock_log_error.assert_called_once() # Проверяем логирование ошибки

# --- Тесты для save_balances ---

@patch('builtins.open', new_callable=mock_open)
@patch('json.dump')
def test_save_balances_success(mock_json_dump, mock_file_open):
    """Тестирует успешное сохранение балансов."""
    balances_to_save = {"789": {"balance": 200, "name": "User3"}}
    save_balances(balances_to_save)
    mock_file_open.assert_called_once_with(BALANCE_FILE, "w", encoding="utf-8")
    # Получаем file handle, который был передан в json.dump
    handle = mock_file_open()
    mock_json_dump.assert_called_once_with(balances_to_save, handle, ensure_ascii=False, indent=4)

@patch('builtins.open', side_effect=IOError("Test IO Error"))
@patch('logging.error')
def test_save_balances_write_error(mock_log_error, mock_file_open):
    """Тестирует ошибку записи файла."""
    balances_to_save = {"111": {"balance": 10, "name": "User4"}}
    save_balances(balances_to_save)
    mock_file_open.assert_called_once_with(BALANCE_FILE, "w", encoding="utf-8")
    mock_log_error.assert_called_once() # Проверяем логирование ошибки

@patch('builtins.open', new_callable=mock_open) # Мок open успешен
@patch('json.dump', side_effect=TypeError("Test Type Error")) # Ошибка при сериализации
@patch('logging.error')
def test_save_balances_json_error(mock_log_error, mock_json_dump, mock_file_open):
    """Тестирует ошибку при сериализации в JSON."""
    balances_to_save = {"222": {"balance": 20, "name": "User5"}}
    save_balances(balances_to_save)
    mock_file_open.assert_called_once_with(BALANCE_FILE, "w", encoding="utf-8")
    handle = mock_file_open()
    mock_json_dump.assert_called_once_with(balances_to_save, handle, ensure_ascii=False, indent=4)
    mock_log_error.assert_called_once() # Проверяем логирование ошибки

# --- Тесты для get_balance ---

@patch('balance.load_balances', return_value={"123": {"balance": 150, "name": "Test"}, "456": {}})
def test_get_balance_user_exists(mock_load):
    """Тестирует получение баланса существующего пользователя."""
    assert get_balance(123) == 150

@patch('balance.load_balances', return_value={"123": {"balance": 150, "name": "Test"}, "456": {}})
def test_get_balance_user_exists_no_balance_key(mock_load):
    """Тестирует получение баланса пользователя без ключа 'balance'."""
    assert get_balance(456) == 0 # Должен вернуть 0 по умолчанию

@patch('balance.load_balances', return_value={"123": {"balance": 150, "name": "Test"}})
def test_get_balance_user_not_exists(mock_load):
    """Тестирует получение баланса несуществующего пользователя."""
    assert get_balance(789) == 0

@patch('balance.load_balances', return_value={})
def test_get_balance_empty_data(mock_load):
    """Тестирует получение баланса, когда файл пуст."""
    assert get_balance(123) == 0

# --- Тесты для update_balance ---

@patch('balance.load_balances')
@patch('balance.save_balances')
def test_update_balance_existing_user_add(mock_save, mock_load):
    """Тестирует добавление средств существующему пользователю."""
    mock_load.return_value = {"123": {"balance": 100, "name": "User1"}}
    update_balance(123, 50)
    mock_load.assert_called_once()
    expected_data = {"123": {"balance": 150, "name": "User1"}}
    mock_save.assert_called_once_with(expected_data)

@patch('balance.load_balances')
@patch('balance.save_balances')
def test_update_balance_existing_user_subtract(mock_save, mock_load):
    """Тестирует снятие средств у существующего пользователя."""
    mock_load.return_value = {"123": {"balance": 100, "name": "User1"}}
    update_balance(123, -30)
    mock_load.assert_called_once()
    expected_data = {"123": {"balance": 70, "name": "User1"}}
    mock_save.assert_called_once_with(expected_data)

@patch('balance.load_balances')
@patch('balance.save_balances')
def test_update_balance_existing_user_subtract_below_zero(mock_save, mock_load):
    """Тестирует снятие средств, приводящее к балансу ниже нуля."""
    mock_load.return_value = {"123": {"balance": 20, "name": "User1"}}
    update_balance(123, -50)
    mock_load.assert_called_once()
    expected_data = {"123": {"balance": 0, "name": "User1"}} # Баланс не должен быть отрицательным
    mock_save.assert_called_once_with(expected_data)

@patch('balance.load_balances')
@patch('balance.save_balances')
def test_update_balance_new_user_add(mock_save, mock_load):
    """Тестирует добавление нового пользователя с положительным балансом."""
    mock_load.return_value = {"123": {"balance": 100, "name": "User1"}} # Начальные данные
    update_balance(789, 75) # Добавляем нового пользователя
    mock_load.assert_called_once()
    expected_data = {
        "123": {"balance": 100, "name": "User1"},
        "789": {"balance": 75, "name": "Unknown"} # Новый пользователь
    }
    mock_save.assert_called_once_with(expected_data)

@patch('balance.load_balances')
@patch('balance.save_balances')
def test_update_balance_new_user_add_zero(mock_save, mock_load):
    """Тестирует добавление нового пользователя с нулевым балансом."""
    mock_load.return_value = {} # Пустые начальные данные
    update_balance(789, 0)
    mock_load.assert_called_once()
    expected_data = {"789": {"balance": 0, "name": "Unknown"}}
    mock_save.assert_called_once_with(expected_data)

@patch('balance.load_balances')
@patch('balance.save_balances')
def test_update_balance_new_user_add_negative(mock_save, mock_load):
    """Тестирует добавление нового пользователя с отрицательным начальным значением (должен стать 0)."""
    mock_load.return_value = {}
    update_balance(789, -50)
    mock_load.assert_called_once()
    expected_data = {"789": {"balance": 0, "name": "Unknown"}} # Баланс не должен быть отрицательным
    mock_save.assert_called_once_with(expected_data) 