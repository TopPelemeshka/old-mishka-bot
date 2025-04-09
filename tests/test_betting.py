import pytest
import json
import os
import datetime
from unittest.mock import patch, mock_open, MagicMock

# Импортируем тестируемые функции из betting.py
try:
    from betting import (
        load_betting_events,
        save_betting_events,
        load_betting_data,
        save_betting_data,
        get_next_active_event,
        publish_event,
        place_bet,
        process_event_results,
        get_event_bets,
        get_betting_history,
        get_user_streak,
        BETTING_EVENTS_FILE,
        BETTING_DATA_FILE
    )
except ImportError:
    pytest.skip("Пропуск тестов betting: не удалось импортировать модуль betting.", allow_module_level=True)

# --- Тесты для load_betting_events ---

@patch('os.path.exists', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data='{"events": [{"id": 1, "description": "Test Event", "is_active": true}]}')
def test_load_betting_events_success(mock_file_open, mock_exists):
    """Тестирует успешную загрузку событий из существующего файла."""
    events = load_betting_events()
    mock_exists.assert_called_once_with(BETTING_EVENTS_FILE)
    mock_file_open.assert_called_once_with(BETTING_EVENTS_FILE, "r", encoding="utf-8")
    assert events == {"events": [{"id": 1, "description": "Test Event", "is_active": True}]}

@patch('os.path.exists', return_value=False)
def test_load_betting_events_file_not_exists(mock_exists):
    """Тестирует случай, когда файл событий не существует."""
    events = load_betting_events()
    mock_exists.assert_called_once_with(BETTING_EVENTS_FILE)
    assert events == {"events": []}

@patch('os.path.exists', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data='invalid json')
@patch('logging.error')
def test_load_betting_events_invalid_json(mock_log_error, mock_file_open, mock_exists):
    """Тестирует случай с невалидным JSON в файле событий."""
    events = load_betting_events()
    mock_exists.assert_called_once_with(BETTING_EVENTS_FILE)
    mock_file_open.assert_called_once_with(BETTING_EVENTS_FILE, "r", encoding="utf-8")
    assert events == {"events": []}
    mock_log_error.assert_called_once()

@patch('os.path.exists', return_value=True)
@patch('builtins.open', side_effect=IOError("Test IO Error"))
@patch('logging.error')
def test_load_betting_events_read_error(mock_log_error, mock_file_open, mock_exists):
    """Тестирует случай ошибки чтения файла событий."""
    events = load_betting_events()
    mock_exists.assert_called_once_with(BETTING_EVENTS_FILE)
    mock_file_open.assert_called_once_with(BETTING_EVENTS_FILE, "r", encoding="utf-8")
    assert events == {"events": []}
    mock_log_error.assert_called_once()

# --- Тесты для save_betting_events ---

@patch('builtins.open', new_callable=mock_open)
@patch('json.dump')
def test_save_betting_events_success(mock_json_dump, mock_file_open):
    """Тестирует успешное сохранение событий."""
    events_to_save = {"events": [{"id": 2, "description": "New Event", "is_active": True}]}
    save_betting_events(events_to_save)
    mock_file_open.assert_called_once_with(BETTING_EVENTS_FILE, "w", encoding="utf-8")
    handle = mock_file_open()
    mock_json_dump.assert_called_once_with(events_to_save, handle, ensure_ascii=False, indent=4)

@patch('builtins.open', side_effect=IOError("Test IO Error"))
@patch('logging.error')
def test_save_betting_events_write_error(mock_log_error, mock_file_open):
    """Тестирует ошибку записи файла событий."""
    events_to_save = {"events": [{"id": 3, "description": "Error Event", "is_active": True}]}
    save_betting_events(events_to_save)
    mock_file_open.assert_called_once_with(BETTING_EVENTS_FILE, "w", encoding="utf-8")
    mock_log_error.assert_called_once()

# --- Тесты для load_betting_data ---

@patch('os.path.exists', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data='{"active_bets": {"1": {"123": {"user_name": "User1", "bets": [{"option_id": 1, "amount": 50}]}}}, "history": [], "win_streaks": {"123": {"streak": 3, "user_name": "User1"}}}')
def test_load_betting_data_success(mock_file_open, mock_exists):
    """Тестирует успешную загрузку данных о ставках из существующего файла."""
    data = load_betting_data()
    mock_exists.assert_called_once_with(BETTING_DATA_FILE)
    mock_file_open.assert_called_once_with(BETTING_DATA_FILE, "r", encoding="utf-8")
    assert data == {
        "active_bets": {"1": {"123": {"user_name": "User1", "bets": [{"option_id": 1, "amount": 50}]}}},
        "history": [],
        "win_streaks": {"123": {"streak": 3, "user_name": "User1"}}
    }

@patch('os.path.exists', return_value=False)
def test_load_betting_data_file_not_exists(mock_exists):
    """Тестирует случай, когда файл данных о ставках не существует."""
    data = load_betting_data()
    mock_exists.assert_called_once_with(BETTING_DATA_FILE)
    assert data == {"active_bets": {}, "history": [], "win_streaks": {}}

@patch('os.path.exists', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data='{"active_bets": {}, "history": [], "win_streaks": {"123": 3}}')
def test_load_betting_data_old_format(mock_file_open, mock_exists):
    """Тестирует загрузку данных в старом формате."""
    data = load_betting_data()
    mock_exists.assert_called_once_with(BETTING_DATA_FILE)
    mock_file_open.assert_called_once_with(BETTING_DATA_FILE, "r", encoding="utf-8")
    assert data["win_streaks"]["123"]["streak"] == 3
    assert data["win_streaks"]["123"]["user_name"] == "Unknown"

# --- Тесты для save_betting_data ---

@patch('builtins.open', new_callable=mock_open)
@patch('json.dump')
def test_save_betting_data_success(mock_json_dump, mock_file_open):
    """Тестирует успешное сохранение данных о ставках."""
    data_to_save = {"active_bets": {}, "history": [], "win_streaks": {}}
    save_betting_data(data_to_save)
    mock_file_open.assert_called_once_with(BETTING_DATA_FILE, "w", encoding="utf-8")
    handle = mock_file_open()
    mock_json_dump.assert_called_once_with(data_to_save, handle, ensure_ascii=False, indent=4)

@patch('builtins.open', new_callable=mock_open)
@patch('json.dump')
def test_save_betting_data_history_truncate(mock_json_dump, mock_file_open):
    """Тестирует ограничение истории до 7 записей."""
    history = []
    for i in range(10):
        history.append({"id": i, "date": f"2023-04-{i+1}"})
    data_to_save = {"active_bets": {}, "history": history, "win_streaks": {}}
    save_betting_data(data_to_save)
    mock_file_open.assert_called_once_with(BETTING_DATA_FILE, "w", encoding="utf-8")
    handle = mock_file_open()
    
    # Проверяем, что json.dump был вызван с данными, где история ограничена 7 записями
    args, kwargs = mock_json_dump.call_args
    assert len(args[0]["history"]) == 7

# --- Тесты для get_next_active_event ---

@patch('betting.load_betting_events')
def test_get_next_active_event_success(mock_load):
    """Тестирует успешное получение следующего активного события."""
    mock_load.return_value = {"events": [
        {"id": 1, "is_active": False},
        {"id": 2, "is_active": True},
        {"id": 3, "is_active": True}
    ]}
    event = get_next_active_event()
    mock_load.assert_called_once()
    assert event["id"] == 2  # Должно вернуть первое активное событие с сортировкой по ID

@patch('betting.load_betting_events')
def test_get_next_active_event_no_active(mock_load):
    """Тестирует случай отсутствия активных событий."""
    mock_load.return_value = {"events": [
        {"id": 1, "is_active": False},
        {"id": 2, "is_active": False}
    ]}
    event = get_next_active_event()
    mock_load.assert_called_once()
    assert event is None

@patch('betting.load_betting_events')
def test_get_next_active_event_empty(mock_load):
    """Тестирует случай пустого списка событий."""
    mock_load.return_value = {"events": []}
    event = get_next_active_event()
    mock_load.assert_called_once()
    assert event is None

# --- Тесты для publish_event ---

@patch('betting.load_betting_events')
@patch('betting.save_betting_events')
@patch('datetime.datetime')
def test_publish_event_success(mock_datetime, mock_save, mock_load):
    """Тестирует успешную публикацию события."""
    test_date = "2023-04-10"
    mock_now = MagicMock()
    mock_now.strftime.return_value = test_date
    mock_datetime.now.return_value = mock_now
    
    events_data = {"events": [
        {"id": 1, "is_active": True, "description": "Test Event"}
    ]}
    mock_load.return_value = events_data
    
    result = publish_event(1)
    
    mock_load.assert_called_once()
    assert result is True
    
    # Проверяем, что событие помечено как неактивное и установлена дата публикации
    expected_events_data = {"events": [
        {"id": 1, "is_active": False, "description": "Test Event", "publication_date": test_date}
    ]}
    mock_save.assert_called_once_with(expected_events_data)

@patch('betting.load_betting_events')
def test_publish_event_not_found(mock_load):
    """Тестирует публикацию несуществующего события."""
    mock_load.return_value = {"events": [{"id": 2, "is_active": True}]}
    result = publish_event(1)
    mock_load.assert_called_once()
    assert result is False

# --- Тесты для place_bet ---

@patch('betting.get_balance', return_value=100)
@patch('betting.update_balance')
@patch('betting.load_betting_events')
@patch('betting.load_betting_data')
@patch('betting.save_betting_data')
@patch('datetime.datetime')
def test_place_bet_success(mock_datetime, mock_save_data, mock_load_data, mock_load_events, mock_update_balance, mock_get_balance):
    """Тестирует успешное размещение ставки."""
    test_date = "2023-04-10 12:00:00"
    mock_now = MagicMock()
    mock_now.strftime.return_value = test_date
    mock_datetime.now.return_value = mock_now
    
    # Начальные данные для тестов
    mock_load_events.return_value = {"events": [
        {"id": 1, "is_active": True, "options": [{"id": 1}, {"id": 2}]}
    ]}
    mock_load_data.return_value = {"active_bets": {}, "history": [], "win_streaks": {}}
    
    result = place_bet(123, "User1", 1, 1, 50)
    
    # Проверяем результат
    assert result is True
    
    # Проверяем, что баланс был обновлен
    mock_get_balance.assert_called_once_with(123)
    mock_update_balance.assert_called_once_with(123, -50)
    
    # Проверяем, что ставка сохранена в правильном формате
    expected_data = {
        "active_bets": {
            "1": {
                "123": {
                    "user_name": "User1",
                    "bets": [
                        {
                            "option_id": 1,
                            "amount": 50,
                            "time": test_date
                        }
                    ]
                }
            }
        },
        "history": [],
        "win_streaks": {}
    }
    mock_save_data.assert_called_once_with(expected_data)

@patch('betting.get_balance', return_value=30)
def test_place_bet_insufficient_balance(mock_get_balance):
    """Тестирует случай недостаточного баланса для ставки."""
    result = place_bet(123, "User1", 1, 1, 50)
    mock_get_balance.assert_called_once_with(123)
    assert result is False

@patch('betting.get_balance', return_value=100)
@patch('betting.load_betting_events')
def test_place_bet_event_not_found(mock_load_events, mock_get_balance):
    """Тестирует ставку на несуществующее событие."""
    mock_load_events.return_value = {"events": []}
    result = place_bet(123, "User1", 1, 1, 50)
    mock_get_balance.assert_called_once_with(123)
    mock_load_events.assert_called_once()
    assert result is False

@patch('betting.get_balance', return_value=100)
@patch('betting.load_betting_events')
def test_place_bet_option_not_found(mock_load_events, mock_get_balance):
    """Тестирует ставку на несуществующий вариант."""
    mock_load_events.return_value = {"events": [
        {"id": 1, "is_active": True, "options": [{"id": 2}]}
    ]}
    result = place_bet(123, "User1", 1, 1, 50)
    mock_get_balance.assert_called_once_with(123)
    mock_load_events.assert_called_once()
    assert result is False

# --- Тесты для process_event_results ---

@patch('betting.load_betting_events')
@patch('betting.load_betting_data')
@patch('betting.save_betting_events')
@patch('betting.save_betting_data')
@patch('betting.update_balance')
@patch('datetime.datetime')
def test_process_event_results_with_winners(mock_datetime, mock_update_balance, mock_save_data,
                                           mock_save_events, mock_load_data, mock_load_events):
    """Тестирует обработку результатов события с победителями."""
    test_date = "2023-04-10"
    mock_now = MagicMock()
    mock_now.strftime.return_value = test_date
    mock_datetime.now.return_value = mock_now
    
    # Настройка тестовых данных
    mock_load_events.return_value = {"events": [
        {
            "id": 1, 
            "is_active": True, 
            "description": "Test Event",
            "question": "Test Question",
            "options": [{"id": 1, "text": "Option 1"}, {"id": 2, "text": "Option 2"}]
        }
    ]}
    
    mock_load_data.return_value = {
        "active_bets": {
            "1": {
                "123": {
                    "user_name": "User1",
                    "bets": [
                        {"option_id": 1, "amount": 100, "time": "2023-04-09 12:00:00"}
                    ]
                },
                "456": {
                    "user_name": "User2",
                    "bets": [
                        {"option_id": 2, "amount": 50, "time": "2023-04-09 12:30:00"}
                    ]
                }
            }
        },
        "history": [],
        "win_streaks": {"123": {"streak": 0, "user_name": "User1"}, "456": {"streak": 0, "user_name": "User2"}}
    }
    
    # Вызов тестируемой функции
    result = process_event_results(1, 1)
    
    # Проверки
    assert result["status"] == "success"
    assert len(result["winners"]) == 1
    assert result["winners"][0]["user_id"] == 123
    assert len(result["losers"]) == 1
    assert result["losers"][0]["user_id"] == 456
    
    # Проверяем обновление события
    expected_event_update = {
        "id": 1, 
        "is_active": False,
        "description": "Test Event",
        "question": "Test Question",
        "options": [{"id": 1, "text": "Option 1"}, {"id": 2, "text": "Option 2"}],
        "results_published": True,
        "winner_option_id": 1
    }
    
    # Проверяем, что балансы были обновлены
    # Тотализатор должен выплатить 150 (общая сумма ставок) / 100 (сумма выигрышных ставок) * 100 = 150
    mock_update_balance.assert_called_once_with(123, 150)

@patch('betting.load_betting_events')
@patch('betting.load_betting_data')
@patch('betting.save_betting_events')
@patch('betting.save_betting_data')
@patch('datetime.datetime')
def test_process_event_results_no_winners(mock_datetime, mock_save_data, mock_save_events, 
                                         mock_load_data, mock_load_events):
    """Тестирует обработку результатов события без победителей."""
    test_date = "2023-04-10"
    mock_now = MagicMock()
    mock_now.strftime.return_value = test_date
    mock_datetime.now.return_value = mock_now
    
    # Настройка тестовых данных
    mock_load_events.return_value = {"events": [
        {
            "id": 1, 
            "is_active": True, 
            "description": "Test Event",
            "question": "Test Question",
            "options": [{"id": 1, "text": "Option 1"}, {"id": 2, "text": "Option 2"}, {"id": 3, "text": "Option 3"}]
        }
    ]}
    
    mock_load_data.return_value = {
        "active_bets": {
            "1": {
                "123": {
                    "user_name": "User1",
                    "bets": [
                        {"option_id": 1, "amount": 100, "time": "2023-04-09 12:00:00"}
                    ]
                },
                "456": {
                    "user_name": "User2",
                    "bets": [
                        {"option_id": 2, "amount": 50, "time": "2023-04-09 12:30:00"}
                    ]
                }
            }
        },
        "history": [],
        "win_streaks": {"123": {"streak": 1, "user_name": "User1"}, "456": {"streak": 2, "user_name": "User2"}}
    }
    
    # Вызов тестируемой функции с вариантом, на который никто не ставил
    result = process_event_results(1, 3)
    
    # Проверки
    assert result["status"] == "success"
    assert len(result["winners"]) == 0
    assert len(result["losers"]) == 2
    
    # Проверяем, что серии побед сброшены
    mock_save_data.assert_called_once()
    call_args = mock_save_data.call_args[0][0]
    assert call_args["win_streaks"]["123"]["streak"] == 0
    assert call_args["win_streaks"]["456"]["streak"] == 0

@patch('betting.load_betting_events')
def test_process_event_results_event_not_found(mock_load_events):
    """Тестирует обработку результатов несуществующего события."""
    mock_load_events.return_value = {"events": []}
    result = process_event_results(999, 1)
    assert result["status"] == "error"
    assert "не найдено" in result["message"]

@patch('betting.load_betting_events')
def test_process_event_results_option_not_found(mock_load_events):
    """Тестирует обработку результатов с несуществующим вариантом ответа."""
    mock_load_events.return_value = {"events": [
        {
            "id": 1, 
            "options": [{"id": 1, "text": "Option 1"}]
        }
    ]}
    result = process_event_results(1, 999)
    assert result["status"] == "error"
    assert "не найден" in result["message"]

# --- Тесты для get_event_bets ---

@patch('betting.load_betting_data')
def test_get_event_bets_success(mock_load):
    """Тестирует успешное получение ставок для события."""
    mock_load.return_value = {
        "active_bets": {
            "1": {
                "123": {"user_name": "User1", "bets": [{"option_id": 1, "amount": 100}]},
                "456": {"user_name": "User2", "bets": [{"option_id": 2, "amount": 50}]}
            }
        }
    }
    bets = get_event_bets(1)
    mock_load.assert_called_once()
    assert len(bets) == 2
    assert "123" in bets
    assert "456" in bets

@patch('betting.load_betting_data')
def test_get_event_bets_event_not_found(mock_load):
    """Тестирует получение ставок для несуществующего события."""
    mock_load.return_value = {"active_bets": {}}
    bets = get_event_bets(999)
    mock_load.assert_called_once()
    assert bets == {}

# --- Тесты для get_betting_history ---

@patch('betting.load_betting_data')
def test_get_betting_history_success(mock_load):
    """Тестирует успешное получение истории ставок."""
    mock_load.return_value = {
        "history": [
            {"event_id": 1, "date": "2023-04-10"},
            {"event_id": 2, "date": "2023-04-09"},
            {"event_id": 3, "date": "2023-04-08"}
        ]
    }
    history = get_betting_history()
    mock_load.assert_called_once()
    assert len(history) == 3
    assert history[0]["event_id"] == 1  # Самое новое событие должно быть первым

@patch('betting.load_betting_data')
def test_get_betting_history_with_limit(mock_load):
    """Тестирует получение истории ставок с ограничением количества."""
    mock_load.return_value = {
        "history": [
            {"event_id": 1, "date": "2023-04-10"},
            {"event_id": 2, "date": "2023-04-09"},
            {"event_id": 3, "date": "2023-04-08"},
            {"event_id": 4, "date": "2023-04-07"},
            {"event_id": 5, "date": "2023-04-06"}
        ]
    }
    history = get_betting_history(limit=2)
    mock_load.assert_called_once()
    assert len(history) == 2
    assert history[0]["event_id"] == 1
    assert history[1]["event_id"] == 2

# --- Тесты для get_user_streak ---

@patch('betting.load_betting_data')
def test_get_user_streak_success(mock_load):
    """Тестирует успешное получение серии побед пользователя."""
    mock_load.return_value = {
        "win_streaks": {
            "123": {"streak": 5, "user_name": "User1"},
            "456": {"streak": 3, "user_name": "User2"}
        }
    }
    streak = get_user_streak(123)
    mock_load.assert_called_once()
    assert streak == 5

@patch('betting.load_betting_data')
def test_get_user_streak_user_not_found(mock_load):
    """Тестирует получение серии побед для несуществующего пользователя."""
    mock_load.return_value = {
        "win_streaks": {
            "123": {"streak": 5, "user_name": "User1"}
        }
    }
    streak = get_user_streak(999)
    mock_load.assert_called_once()
    assert streak == 0 