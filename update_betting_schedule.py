#!/usr/bin/env python3
"""
Скрипт для обновления расписания ставок.
Запускать из командной строки: python update_betting_schedule.py
"""

import os
import sys
import logging
import datetime
import json

# Настраиваем логирование для вывода в консоль
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

def main():
    """
    Основная функция для обновления расписания ставок.
    """
    from config import schedule_config
    import state
    
    # Устанавливаем флаг ставок в True для гарантии планирования
    state.betting_enabled = True
    
    logging.info("Начинаю перепланирование расписания ставок...")
    
    # Получаем настройки из конфига
    betting_config = schedule_config.get("betting", {})
    logging.info(f"Текущие настройки ставок: {betting_config}")
    
    # Форсируем планирование на текущий день
    now = datetime.datetime.now()
    today = now.date()
    
    # Получаем текущее локальное время в часах и минутах
    current_hour = now.hour
    current_minute = now.minute
    
    # Получаем время для публикации результатов из конфига
    close_time_str = betting_config.get("close_time", "20:00")
    close_hour, close_minute = map(int, close_time_str.split(':'))
    
    results_time_str = betting_config.get("results_time", "21:00")
    results_hour, results_minute = map(int, results_time_str.split(':'))
    
    # Проверяем, не прошло ли время публикации результатов
    if current_hour > results_hour or (current_hour == results_hour and current_minute >= results_minute):
        logging.info("Время публикации результатов на сегодня уже прошло.")
        logging.info("Расписание не было обновлено.")
        return
    
    # Формируем время закрытия и публикации ставок с учетом текущего времени
    if current_hour >= close_hour and current_minute >= close_minute:
        # Если время закрытия ставок прошло, но время публикации результатов ещё нет,
        # форсируем закрытие ставок через 1 минуту, а публикацию результатов через 5 минут
        logging.info("Время закрытия ставок прошло. Устанавливаю закрытие через 1 минуту и публикацию через 5 минут.")
        close_datetime = now + datetime.timedelta(minutes=1)
        results_datetime = now + datetime.timedelta(minutes=5)
    else:
        # Если еще не прошло время закрытия, используем время из конфига
        logging.info(f"Использую время закрытия {close_time_str} и публикации {results_time_str} из конфига.")
        close_datetime = datetime.datetime.combine(today, datetime.time(close_hour, close_minute))
        results_datetime = datetime.datetime.combine(today, datetime.time(results_hour, results_minute))
    
    # Записываем временное расписание в файл для проверки
    temp_schedule = {
        "close_betting": close_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "publish_results": results_datetime.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    with open("state_data/scheduled_betting.json", "w", encoding="utf-8") as f:
        json.dump(temp_schedule, f, ensure_ascii=False, indent=4)
    
    logging.info(f"Временное расписание сохранено в файл state_data/scheduled_betting.json")
    logging.info(f"Закрытие ставок: {close_datetime}")
    logging.info(f"Публикация результатов: {results_datetime}")
    
    # Проверяем события для ставок в файле
    from betting import load_betting_events
    events_data = load_betting_events()
    
    for event in events_data.get("events", []):
        if event.get("winner_option_id") and event.get("is_active", False):
            logging.warning(f"Событие ID {event.get('id')} имеет установленного победителя, но всё ещё активно!")
            logging.warning("Это может привести к проблемам с публикацией результатов.")
            logging.warning("Рекомендуется установить is_active: false для этого события.")
        
        if event.get("is_active", False):
            logging.info(f"Активное событие найдено: ID {event.get('id')} - {event.get('description')}")
    
    logging.info("Расписание обновлено успешно!")
    logging.info("Для применения расписания перезапустите бота или выполните команду /update_betting_schedule в чате администраторов.")

if __name__ == "__main__":
    main() 