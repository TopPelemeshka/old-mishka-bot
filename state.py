# state.py
import os
import json
import logging

STATE_FILE = "state_data/bot_state.json"

# Глобальные флаги (начальные значения)
autopost_enabled = True
quiz_enabled = True
wisdom_enabled = True

# Время последнего броска для каждого пользователя (для /roll)
last_roll_time = {}

# Хранение сессий рулетки (для /roulette)
ROULETTE_DATA = {}

def save_state(autopost_value, quiz_value, wisdom_value):
    """Сохраняем состояние, используя переданные значения."""
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
