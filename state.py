# state.py
"""
Модуль для управления постоянным состоянием бота.
Хранит и загружает состояние из файла, хранит временные данные в памяти.
"""
import os
import json
import logging
from pathlib import Path

STATE_FILE = "state_data/bot_state.json"

# Глобальные флаги (начальные значения)
autopost_enabled = True  # Включен ли автопостинг
quiz_enabled = True      # Включены ли викторины
wisdom_enabled = True    # Включены ли мудрые мысли
betting_enabled = True   # Включены ли ставки

# Время последнего броска для каждого пользователя (для /roll)
last_roll_time = {}

# Хранение сессий рулетки (для /roulette)
ROULETTE_DATA = {}

def save_state(autopost_value, quiz_value, wisdom_value, betting_value):
    """
    Сохраняет состояние флагов бота в JSON файл.
    
    Args:
        autopost_value: Новое значение для флага автопостинга
        quiz_value: Новое значение для флага викторин
        wisdom_value: Новое значение для флага мудрых мыслей
        betting_value: Новое значение для флага ставок
    
    Raises:
        IOError: Если произошла ошибка при записи файла
        TypeError: Если произошла ошибка при сериализации JSON
    """
    logger = logging.getLogger(__name__)
    logger.info("save_state called: autopost_enabled=%s, quiz_enabled=%s, wisdom_enabled=%s, betting_enabled=%s", 
                autopost_value, quiz_value, wisdom_value, betting_value)
    abs_path = os.path.abspath(STATE_FILE)
    logger.info("Writing bot_state.json to: %s", abs_path)
    data = {
        "autopost_enabled": autopost_value,
        "quiz_enabled": quiz_value,
        "wisdom_enabled": wisdom_value,
        "betting_enabled": betting_value
    }
    # Не обрабатываем исключения, чтобы они были видны в тестах
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_state():
    """
    Загружает состояние флагов бота из JSON файла.
    Если файл не существует, используются значения по умолчанию.
    
    Изменяет глобальные переменные:
    - autopost_enabled
    - quiz_enabled
    - wisdom_enabled
    - betting_enabled
    
    Raises:
        IOError: Если произошла ошибка при чтении файла
        json.JSONDecodeError: Если файл содержит невалидный JSON
    """
    global autopost_enabled, quiz_enabled, wisdom_enabled, betting_enabled
    if not os.path.exists(STATE_FILE):
        return
    
    # Не обрабатываем исключения, они должны быть видны в тестах
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    autopost_enabled = data.get("autopost_enabled", True)
    quiz_enabled = data.get("quiz_enabled", True)
    wisdom_enabled = data.get("wisdom_enabled", True)
    betting_enabled = data.get("betting_enabled", True)
    logging.getLogger(__name__).info("Loaded state: autopost_enabled=%s, quiz_enabled=%s, wisdom_enabled=%s, betting_enabled=%s", 
                                     autopost_enabled, quiz_enabled, wisdom_enabled, betting_enabled)
