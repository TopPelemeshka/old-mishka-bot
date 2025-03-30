# state.py
"""
Модуль для управления постоянным состоянием бота.
Хранит и загружает состояние из файла, хранит временные данные в памяти.
"""
import os
import json
import logging

STATE_FILE = "state_data/bot_state.json"

# Глобальные флаги (начальные значения)
autopost_enabled = True  # Включен ли автопостинг
quiz_enabled = True      # Включены ли викторины
wisdom_enabled = True    # Включены ли мудрые мысли

# Время последнего броска для каждого пользователя (для /roll)
last_roll_time = {}

# Хранение сессий рулетки (для /roulette)
ROULETTE_DATA = {}

def save_state(autopost_value, quiz_value, wisdom_value):
    """
    Сохраняет состояние флагов бота в JSON файл.
    
    Args:
        autopost_value: Новое значение для флага автопостинга
        quiz_value: Новое значение для флага викторин
        wisdom_value: Новое значение для флага мудрых мыслей
    """
    logger = logging.getLogger(__name__)
    logger.info("save_state called: autopost_enabled=%s, quiz_enabled=%s, wisdom_enabled=%s", 
                autopost_value, quiz_value, wisdom_value)
    abs_path = os.path.abspath(STATE_FILE)
    logger.info("Writing bot_state.json to: %s", abs_path)
    data = {
        "autopost_enabled": autopost_value,
        "quiz_enabled": quiz_value,
        "wisdom_enabled": wisdom_value
    }
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
    """
    global autopost_enabled, quiz_enabled, wisdom_enabled
    if not os.path.exists(STATE_FILE):
        return
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    autopost_enabled = data.get("autopost_enabled", True)
    quiz_enabled = data.get("quiz_enabled", True)
    wisdom_enabled = data.get("wisdom_enabled", True)
    logging.getLogger(__name__).info("Loaded state: autopost_enabled=%s, quiz_enabled=%s, wisdom_enabled=%s", 
                                     autopost_enabled, quiz_enabled, wisdom_enabled)
