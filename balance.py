# balance.py

import os
import json
import logging

BALANCE_FILE = "state_data/balance.json"

def load_balances() -> dict:
    """
    Считывает словарь { str(user_id): { 'balance': int, 'name': str } }
    из файла BALANCE_FILE. Если файл пуст или не существует,
    возвращается пустой словарь.
    """
    if not os.path.exists(BALANCE_FILE):
        return {}
    try:
        with open(BALANCE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception as e:
        logging.error(f"Ошибка при чтении {BALANCE_FILE}: {e}")
    return {}

def save_balances(balances: dict):
    """
    Сохраняет словарь балансов в файл BALANCE_FILE.
    """
    try:
        with open(BALANCE_FILE, "w", encoding="utf-8") as f:
            json.dump(balances, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Ошибка при записи {BALANCE_FILE}: {e}")

def get_balance(user_id: int) -> int:
    """
    Возвращает баланс пользователя по его user_id.
    Если записи нет, вернёт 0.
    """
    data = load_balances()
    user_id_str = str(user_id)
    
    if user_id_str in data:
        logging.debug(f"Получение баланса пользователя {user_id}: {data[user_id_str].get('balance', 0)}")
        return data[user_id_str].get("balance", 0)
    return 0

def update_balance(user_id: int, delta: int):
    """
    Изменяет баланс пользователя (прибавляет delta) по его user_id.
    Может быть отрицательным, тогда баланс уменьшится.
    """
    data = load_balances()  # Загружаем все данные
    user_id_str = str(user_id)
    
    if user_id_str in data:
        current_balance = data[user_id_str].get("balance", 0)
        new_balance = current_balance + delta
        if new_balance < 0:
            new_balance = 0  # Не даем упасть ниже нуля
        data[user_id_str]["balance"] = new_balance
        logging.debug(f"Обновление баланса для {user_id}: новый баланс {new_balance}")
    else:
        # Если пользователя нет, создаём его с начальным балансом
        data[user_id_str] = {"balance": delta if delta > 0 else 0, "name": "Unknown"}
        logging.debug(f"Создание баланса для {user_id}: новый баланс {data[user_id_str]}")
    
    save_balances(data)  # Сохраняем изменения
