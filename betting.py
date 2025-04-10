# betting.py
"""
Модуль для управления системой ставок на события.
Обеспечивает создание событий, прием ставок, определение результатов и выплату выигрышей.
"""

import os
import json
import logging
import datetime
from balance import load_balances, update_balance, get_balance

# Константы для хранения путей к файлам
BETTING_EVENTS_FILE = "post_materials/betting_events.json"
BETTING_DATA_FILE = "state_data/betting_data.json"

def load_betting_events():
    """
    Загружает список событий для ставок.
    
    Returns:
        dict: Словарь с событиями
    """
    if not os.path.exists(BETTING_EVENTS_FILE):
        return {"events": []}
    
    try:
        with open(BETTING_EVENTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception as e:
        logging.error(f"Ошибка при чтении {BETTING_EVENTS_FILE}: {e}")
        return {"events": []}

def save_betting_events(data):
    """
    Сохраняет список событий в файл.
    
    Args:
        data (dict): Словарь с событиями для сохранения
    """
    try:
        with open(BETTING_EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Ошибка при записи {BETTING_EVENTS_FILE}: {e}")

def load_betting_data():
    """
    Загружает данные о текущих ставках и истории.
    
    Returns:
        dict: Словарь с активными ставками, историей и сериями побед
    """
    if not os.path.exists(BETTING_DATA_FILE):
        return {"active_bets": {}, "history": [], "win_streaks": {}}
    
    try:
        with open(BETTING_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Обеспечиваем совместимость со старым форматом данных
            if "win_streaks" not in data:
                data["win_streaks"] = {}
                
            # Конвертируем старый формат win_streaks в новый, если нужно
            updated_win_streaks = {}
            for user_id, streak_data in data["win_streaks"].items():
                if isinstance(streak_data, dict):
                    # Проверяем что все необходимые поля есть
                    if "streak" not in streak_data:
                        streak_data["streak"] = 0
                    if "user_name" not in streak_data:
                        streak_data["user_name"] = "Unknown"
                        
                    # Удаляем @ из имени пользователя, если есть
                    if streak_data["user_name"].startswith('@'):
                        streak_data["user_name"] = streak_data["user_name"][1:]
                        
                    updated_win_streaks[user_id] = streak_data
                else:
                    # Старый формат - просто число
                    updated_win_streaks[user_id] = {
                        "streak": streak_data,
                        "user_name": "Unknown"
                    }
            
            data["win_streaks"] = updated_win_streaks
            
            # Также очищаем имена пользователей в истории ставок
            for entry in data.get("history", []):
                for winner in entry.get("winners", []):
                    if "user_name" in winner and winner["user_name"].startswith('@'):
                        winner["user_name"] = winner["user_name"][1:]
                        
                for loser in entry.get("losers", []):
                    if "user_name" in loser and loser["user_name"].startswith('@'):
                        loser["user_name"] = loser["user_name"][1:]
            
            return data
    except Exception as e:
        logging.error(f"Ошибка при чтении {BETTING_DATA_FILE}: {e}")
        return {"active_bets": {}, "history": [], "win_streaks": {}}

def save_betting_data(data):
    """
    Сохраняет данные о ставках в файл.
    
    Args:
        data (dict): Словарь с данными для сохранения
    """
    try:
        # Оставляем только последние 7 записей в истории
        if "history" in data and len(data["history"]) > 7:
            data["history"] = sorted(data["history"], key=lambda x: x.get("date"), reverse=True)[:7]
        
        with open(BETTING_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Ошибка при записи {BETTING_DATA_FILE}: {e}")

def get_next_active_event():
    """
    Получает следующее активное событие.
    
    Returns:
        dict: Данные события или None, если нет активных событий
    """
    events_data = load_betting_events()
    events = events_data.get("events", [])
    
    # Сортируем события по ID, чтобы они публиковались по порядку
    events.sort(key=lambda x: x.get("id", 0))
    
    for event in events:
        if event.get("is_active", True):
            return event
    
    return None

def publish_event(event_id):
    """
    Помечает событие как неактивное после публикации.
    
    Args:
        event_id (int): ID события
        
    Returns:
        bool: True, если событие успешно помечено, False в противном случае
    """
    events_data = load_betting_events()
    events = events_data.get("events", [])
    
    for event in events:
        if event.get("id") == event_id:
            event["is_active"] = False
            event["publication_date"] = datetime.datetime.now().strftime("%Y-%m-%d")
            save_betting_events(events_data)
            return True
    
    return False

def place_bet(user_id, user_name, event_id, option_id, amount):
    """
    Размещает ставку пользователя на конкретное событие.
    
    Args:
        user_id (int): ID пользователя
        user_name (str): Имя пользователя (username)
        event_id (int или str): ID события
        option_id (int или str): ID выбранного варианта
        amount (int): Размер ставки
        
    Returns:
        bool: True, если ставка успешно размещена, False в противном случае
    """
    # Проверяем баланс пользователя
    user_balance = get_balance(user_id)
    if user_balance < amount:
        return False

    # Проверяем существование события
    events_data = load_betting_events()
    event = None

    for e in events_data.get("events", []):
        if str(e.get("id")) == str(event_id):
            event = e
            break

    if not event:
        return False

    # Проверяем существование выбранного варианта
    option_exists = False
    for option in event.get("options", []):
        if str(option.get("id")) == str(option_id):
            option_exists = True
            break

    if not option_exists:
        return False

    # Загружаем данные о ставках
    betting_data = load_betting_data()

    user_id_str = str(user_id)
    event_id_str = str(event_id)

    if event_id_str not in betting_data["active_bets"]:
        betting_data["active_bets"][event_id_str] = {}

    if user_id_str not in betting_data["active_bets"][event_id_str]:
        betting_data["active_bets"][event_id_str][user_id_str] = {
            "user_name": user_name,
            "bets": []
        }

    # Добавляем ставку в список ставок пользователя
    betting_data["active_bets"][event_id_str][user_id_str]["bets"].append({
        "option_id": option_id,
        "amount": amount,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    try:
        # Сначала сохраняем ставку
        save_betting_data(betting_data)
        
        # Если сохранение прошло успешно, снимаем деньги с баланса
        update_balance(user_id, -amount)
        
        return True
    except Exception as e:
        logging.error(f"Ошибка при сохранении ставки: {e}")
        return False

def process_event_results(event_id, winner_option_id):
    """
    Обрабатывает результаты события, определяет победителей и проигравших,
    обновляет балансы и серии побед.
    
    Args:
        event_id (int или str): ID события
        winner_option_id (int или str): ID победившего варианта
        
    Returns:
        dict: Словарь с результатами обработки ставок
    """
    events_data = load_betting_events()
    betting_data = load_betting_data()
    
    event = None
    for e in events_data.get("events", []):
        if str(e.get("id")) == str(event_id):
            event = e
            break
    
    if not event:
        return {"status": "error", "message": "Событие не найдено"}
    
    # Получаем правильный вариант ответа и его описание
    correct_option = None
    for option in event.get("options", []):
        if str(option.get("id")) == str(winner_option_id):
            correct_option = option
            break
    
    if not correct_option:
        return {"status": "error", "message": "Вариант ответа не найден"}
    
    # Обновляем данные события
    event["results_published"] = True
    event["winner_option_id"] = winner_option_id
    event["is_active"] = False
    save_betting_events(events_data)
    
    # Обрабатываем ставки
    event_id_str = str(event_id)
    if event_id_str not in betting_data["active_bets"]:
        return {"status": "success", "message": "Нет активных ставок на данное событие"}
    
    # Подсчитываем общие суммы ставок
    total_bets = 0  # общая сумма всех ставок
    total_winning_bets = 0  # общая сумма выигрышных ставок
    
    # Проходим все ставки для подсчета сумм
    for user_id_str, user_data in betting_data["active_bets"][event_id_str].items():
        for bet in user_data.get("bets", []):
            bet_amount = bet.get("amount", 0)
            bet_option = bet.get("option_id")
            
            total_bets += bet_amount
            
            # Если ставка на победивший вариант
            if str(bet_option) == str(winner_option_id):
                total_winning_bets += bet_amount
    
    # Если нет выигрышных ставок, все ставки возвращаются
    if total_winning_bets == 0:
        losers = []  # Создаем список проигравших
        for user_id_str, user_data in betting_data["active_bets"][event_id_str].items():
            user_id = int(user_id_str)
            user_name = user_data.get("user_name", "Unknown")
            total_bet = sum(bet.get("amount", 0) for bet in user_data.get("bets", []))
            
            # При проигрыше не возвращаем ставку, но добавляем пользователя в список проигравших
            if total_bet > 0:
                losers.append({
                    "user_id": user_id,
                    "user_name": user_name,
                    "loss_amount": total_bet
                })
                
                # Сбрасываем серию побед
                if user_id_str not in betting_data["win_streaks"]:
                    betting_data["win_streaks"][user_id_str] = {
                        "streak": 0,
                        "user_name": user_name
                    }
                else:
                    betting_data["win_streaks"][user_id_str]["streak"] = 0
        
        # Создаем запись в истории без победителей, но с проигравшими
        history_entry = {
            "event_id": event_id,
            "description": event.get("description", ""),
            "question": event.get("question", ""),
            "options": event.get("options", []),
            "correct_option": correct_option,
            "result_description": event.get("result_description", ""),
            "winner_option_id": winner_option_id,
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "total_bets": total_bets,
            "winners": [],
            "losers": losers
        }
        
        betting_data["history"].append(history_entry)
        del betting_data["active_bets"][event_id_str]
        save_betting_data(betting_data)
        
        return {
            "status": "success", 
            "message": "Нет выигрышных ставок, ставки не возвращаются",
            "event": event,
            "correct_option": correct_option,
            "winners": [],
            "losers": losers,
            "total_bets": total_bets
        }
    
    # Коэффициент тотализатора: общая сумма ставок / сумма выигрышных ставок
    tote_coefficient = total_bets / total_winning_bets
    
    winners = []
    losers = []
    
    for user_id_str, user_data in betting_data["active_bets"][event_id_str].items():
        user_id = int(user_id_str)
        user_name = user_data.get("user_name", "Unknown")
        
        # Обрабатываем все ставки пользователя
        total_win = 0
        total_loss = 0
        user_winning_bets = 0
        won = False
        
        for bet in user_data.get("bets", []):
            bet_amount = bet.get("amount", 0)
            bet_option = bet.get("option_id")
            
            # Если пользователь угадал
            if str(bet_option) == str(winner_option_id):
                user_winning_bets += bet_amount
                won = True
            else:
                total_loss += bet_amount
        
        # Рассчитываем выигрыш по тотализатору
        if won:
            # Выигрыш = ставка на победивший вариант * коэффициент тотализатора
            win_amount = int(user_winning_bets * tote_coefficient)
            total_win = win_amount
            # В тотализаторе ставка НЕ возвращается, начисляется только чистый выигрыш
            update_balance(user_id, win_amount)
        
        # Обновляем серию побед
        if user_id_str not in betting_data["win_streaks"]:
            betting_data["win_streaks"][user_id_str] = {
                "streak": 0,
                "user_name": user_name
            }
        else:
            # Обновляем имя пользователя, если оно изменилось
            betting_data["win_streaks"][user_id_str]["user_name"] = user_name
        
        if won:
            betting_data["win_streaks"][user_id_str]["streak"] += 1
            winners.append({
                "user_id": user_id,
                "user_name": user_name,
                "win_amount": total_win,
                "bet_amount": user_winning_bets,
                "streak": betting_data["win_streaks"][user_id_str]["streak"]
            })
        else:
            betting_data["win_streaks"][user_id_str]["streak"] = 0
            losers.append({
                "user_id": user_id,
                "user_name": user_name,
                "loss_amount": total_loss
            })
    
    # Создаем запись в истории
    history_entry = {
        "event_id": event_id,
        "description": event.get("description", ""),
        "question": event.get("question", ""),
        "options": event.get("options", []),
        "correct_option": correct_option,
        "result_description": event.get("result_description", ""),
        "winner_option_id": winner_option_id,
        "tote_coefficient": tote_coefficient,
        "total_winning_bets": total_winning_bets,
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "total_bets": total_bets,
        "winners": winners,
        "losers": losers
    }
    
    betting_data["history"].append(history_entry)
    
    # Очищаем активные ставки для данного события
    del betting_data["active_bets"][event_id_str]
    
    save_betting_data(betting_data)
    
    return {
        "status": "success",
        "event": event,
        "correct_option": correct_option,
        "winners": winners,
        "losers": losers,
        "total_bets": total_bets,
        "tote_coefficient": tote_coefficient
    }

def get_event_bets(event_id):
    """
    Получает все ставки на указанное событие.
    
    Args:
        event_id (int): ID события
        
    Returns:
        dict: Словарь со ставками пользователей
    """
    betting_data = load_betting_data()
    event_id_str = str(event_id)
    
    if event_id_str in betting_data["active_bets"]:
        return betting_data["active_bets"][event_id_str]
    
    return {}

def get_betting_history(limit=7):
    """
    Получает историю ставок.
    
    Args:
        limit (int): Максимальное количество записей
        
    Returns:
        list: Список с записями истории ставок
    """
    betting_data = load_betting_data()
    history = betting_data.get("history", [])
    
    # Сортируем по дате (от новых к старым)
    sorted_history = sorted(history, key=lambda x: x.get("date"), reverse=True)
    
    # Возвращаем указанное количество записей
    return sorted_history[:limit]

def get_user_streak(user_id):
    """
    Получает серию побед пользователя.
    
    Args:
        user_id (int): ID пользователя
        
    Returns:
        int: Количество побед подряд
    """
    betting_data = load_betting_data()
    user_id_str = str(user_id)
    
    if user_id_str in betting_data["win_streaks"]:
        return betting_data["win_streaks"][user_id_str].get("streak", 0)
    
    return 0 