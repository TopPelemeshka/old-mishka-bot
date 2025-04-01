# main.py
"""
Основной модуль Telegram-бота с множеством функций:
- Автопостинг медиаконтента
- Викторины и опросы
- Развлекательные команды (кубики, рулетка, казино)
- Звуковая панель
- Управление расписанием постов
"""
import logging
import datetime
import os
from pathlib import Path
import logging.handlers
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PollAnswerHandler,
    filters,
)

from telegram.ext.filters import BaseFilter

# Настройка логирования
def setup_logging():
    """
    Настраивает систему логирования с ротацией файлов логов:
    - Основной лог в logs/bot.log
    - Отдельный лог ошибок в logs/errors.log
    - Вывод в консоль
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "bot.log"
    
    # Настройка корневого логгера
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Форматтер для логов
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Обработчик для файла с ротацией
    # Ротация каждые 5 МБ, храним 5 бэкапов
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Обработчик для ошибок с отдельной ротацией
    error_log_file = log_dir / "errors.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file, maxBytes=2*1024*1024, backupCount=3, encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    
    # Добавляем обработчики
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    
    # Устанавливаем обработчик для необработанных исключений
    def handle_exception(exc_type, exc_value, exc_traceback):
        logger.error("Необработанное исключение", exc_info=(exc_type, exc_value, exc_traceback))
    
    import sys
    sys.excepthook = handle_exception
    
    return logger

# Инициализация логгера
logger = setup_logging()

from config import TOKEN, schedule_config, reload_all_configs
from handlers.start_help import start, help_command
from handlers.getfileid import getfileid_command, catch_animation_fileid
from handlers.roll import roll_command, roll_callback
from handlers.roulette import roulette_command, roulette_callback
from handlers.all import all_command
from handlers.coffee_mishka import coffee_command, mishka_command, durka_command
from handlers.chatid import chatid_command
from handlers.technical_work import technical_work_command
from handlers.sound import sound_command, sound_callback
from handlers.sleep_command import sleep_command
from handlers.morning_command import morning_command

# Импортируем из autopost
from autopost import (
    stop_autopost_command,
    start_autopost_command,
    stats_command,
    next_posts_command
)

from scheduler import (
    midnight_reset_callback, 
    schedule_post_command, 
    change_date_callback, 
    custom_date_handler, 
    reschedule_all_posts, 
    parse_time_from_string, 
    list_scheduled_posts_command, 
    delete_post_callback,
    talk_command,
    talk_media_group_command,
    schedule_media_group_post_command
)
from quiz import poll_answer_handler, rating_command, weekly_quiz_reset
from state import load_state

from quiz import start_quiz_command, stop_quiz_command

from wisdom import start_wisdom_command, stop_wisdom_command

from handlers.logout_command import logout_command

from handlers.balance_command import balance_command
from casino.casino_main import casino_command, casino_callback_handler
from casino.slots import handle_slots_bet_callback
from casino.roulette import handle_roulette_bet_callback, handle_change_bet

class MediaCommandFilter(BaseFilter):
    """
    Фильтр для обработки команд, отправленных с медиа-вложениями.
    Например, для команды /post с прикрепленным фото или видео.
    """
    def check_update(self, update):
        message = update.effective_message
        if not message:
            return False
        # Проверяем, есть ли медиа и caption начинается с "/post"
        if (message.photo or message.video or message.audio) and message.caption:
            # ВАЖНО: медиа-группы (альбомы) обрабатываются отдельным фильтром
            if message.media_group_id is not None:
                return False
            return message.caption.startswith("/post")
        return False

class MediaGroupCommandFilter(BaseFilter):
    """
    Фильтр для обработки команды /post, отправленной с медиа-группой (альбомом).
    Срабатывает на сообщения с media_group_id, когда первое сообщение содержит caption с /post.
    """
    # Статические множества для отслеживания обрабатываемых групп
    _post_media_groups = set()
    
    def check_update(self, update):
        message = update.effective_message
        if not message:
            return False
        
        # Проверяем наличие media_group_id
        media_group_id = message.media_group_id
        if not media_group_id:
            return False
            
        has_post_command = message.caption and message.caption.startswith("/post")
        has_talk_command = message.caption and message.caption.startswith("/talk")
        
        # Для отладки выводим все сообщения с медиа-группами
        caption_text = message.caption if message.caption else 'None'
        logging.info(f"[DEBUG] MediaGroupCommandFilter: Проверка медиа-группы id={media_group_id}, caption='{caption_text}'")
        
        # Если это группа с командой /talk, игнорируем
        if has_talk_command:
            logging.info(f"[DEBUG] MediaGroupCommandFilter: Игнорируем группу {media_group_id} с командой /talk")
            return False
        
        # Если группа уже обрабатывается, перехватываем все её сообщения
        if media_group_id in self._post_media_groups:
            logging.info(f"[DEBUG] MediaGroupCommandFilter: Перехватываем последующее сообщение группы {media_group_id}")
            return True
        
        # Если это новая группа с командой /post, добавляем её в список обрабатываемых
        if has_post_command:
            self._post_media_groups.add(media_group_id)
            logging.info(f"[DEBUG] MediaGroupCommandFilter: УСПЕШНО! Первое сообщение группы {media_group_id} с командой /post")
            return True
        
        # Иначе игнорируем
        return False
        
    @classmethod
    def remove_group(cls, media_group_id):
        """Удаляет идентификатор медиа-группы из списка обрабатываемых"""
        if media_group_id in cls._post_media_groups:
            cls._post_media_groups.remove(media_group_id)
            logging.info(f"[DEBUG] MediaGroupCommandFilter: Удалена группа {media_group_id} из списка обрабатываемых")
            return True
        return False

class TalkCommandFilter(BaseFilter):
    """
    Фильтр для обработки команды /talk, отправленной с одиночным медиа-вложением.
    Игнорирует сообщения, принадлежащие медиа-группам (альбомам).
    """
    def check_update(self, update):
        message = update.effective_message
        if not message:
            return False
            
        # Проверяем, что это НЕ часть медиа-группы (у него нет media_group_id)
        if message.media_group_id is not None:
            return False
            
        # Проверяем наличие любого типа медиа и caption начинается с "/talk"
        if (message.photo or message.video or message.audio or message.animation or 
            message.document or message.voice or message.video_note) and message.caption:
            return message.caption.startswith("/talk")
        return False

class MediaGroupTalkCommandFilter(BaseFilter):
    """
    Фильтр для обработки команды /talk, отправленной с медиа-группой (альбомом).
    Срабатывает на все сообщения из медиа-группы, если первое сообщение содержит caption с /talk.
    """
    # Статические множества для отслеживания обрабатываемых групп
    _talk_media_groups = set()
    
    def check_update(self, update):
        message = update.effective_message
        if not message:
            return False
        
        # Проверяем наличие media_group_id
        media_group_id = message.media_group_id
        if not media_group_id:
            return False
            
        has_post_command = message.caption and message.caption.startswith("/post")
        has_talk_command = message.caption and message.caption.startswith("/talk")
        
        # Если это группа с командой /post, игнорируем
        if has_post_command:
            logging.info(f"[DEBUG] MediaGroupTalkCommandFilter: Игнорируем медиа-группу id={media_group_id} с командой /post")
            return False
        
        # Если группа уже обрабатывается, перехватываем все её сообщения
        if media_group_id in self._talk_media_groups:
            logging.info(f"[DEBUG] MediaGroupTalkCommandFilter: Перехватываем последующее сообщение группы {media_group_id}")
            return True
        
        # Если это новая группа с командой /talk, добавляем её в список обрабатываемых
        if has_talk_command:
            self._talk_media_groups.add(media_group_id)
            logging.info(f"[DEBUG] MediaGroupTalkCommandFilter: Обнаружена медиа-группа id={media_group_id} с командой /talk")
            return True
        
        # Игнорируем сообщения без caption или с неизвестной командой
        logging.info(f"[DEBUG] MediaGroupTalkCommandFilter: Игнорируем медиа-группу id={media_group_id} без команды")
        return False
        
    @classmethod
    def remove_group(cls, media_group_id):
        """Удаляет идентификатор медиа-группы из списка обрабатываемых"""
        if media_group_id in cls._talk_media_groups:
            cls._talk_media_groups.remove(media_group_id)
            logging.info(f"[DEBUG] MediaGroupTalkCommandFilter: Удалена группа {media_group_id} из списка обрабатываемых")
            return True
        return False

# Добавим обработчик команды для перезагрузки конфигураций
async def reload_config_command(update, context):
    """Обработчик команды для перезагрузки всех конфигураций бота"""
    reload_all_configs()
    await update.message.reply_text("Конфигурации перезагружены!")

def main() -> None:
    """
    Основная функция, которая инициализирует бота, добавляет обработчики команд
    и запускает опрос сервера Telegram на наличие обновлений
    """
    app = ApplicationBuilder().token(TOKEN).build()

    # --- ВАЖНО ---:
    # Считываем состояние флагов до того, как отдадим бота в run_polling
    load_state()

    # Команды базовые
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("getfileid", getfileid_command))
    app.add_handler(MessageHandler(filters.ANIMATION, catch_animation_fileid))
    
    # Развлекательные команды
    app.add_handler(CommandHandler("roll", roll_command))
    app.add_handler(CallbackQueryHandler(roll_callback, pattern=r"^roll\|"))
    app.add_handler(CommandHandler("roulette", roulette_command))
    app.add_handler(CallbackQueryHandler(roulette_callback, pattern=r"^roulette\|"))
    app.add_handler(CommandHandler("all", all_command))
    app.add_handler(CommandHandler("coffee", coffee_command))
    app.add_handler(CommandHandler("mishka", mishka_command))
    app.add_handler(CommandHandler("durka", durka_command))
    app.add_handler(CommandHandler("chatid", chatid_command))
    app.add_handler(CommandHandler("technical_work", technical_work_command))

    # Обработчики для команды /talk - должны быть зарегистрированы РАНЬШЕ, чем /post
    app.add_handler(MessageHandler(MediaGroupTalkCommandFilter(), talk_media_group_command))  # Для групп медиа (альбомов)
    app.add_handler(CommandHandler("talk", talk_command))  # Для текстовых сообщений
    app.add_handler(MessageHandler(TalkCommandFilter(), talk_command))  # Для одиночных медиа
    
    # Команды для управления постами
    app.add_handler(CommandHandler("post", schedule_post_command))
    app.add_handler(MessageHandler(MediaGroupCommandFilter(), schedule_media_group_post_command))
    app.add_handler(MessageHandler(MediaCommandFilter(), schedule_post_command))
    app.add_handler(CallbackQueryHandler(change_date_callback, pattern=r"^set_date:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, custom_date_handler))
    app.add_handler(CommandHandler("posts", list_scheduled_posts_command))
    app.add_handler(CallbackQueryHandler(delete_post_callback, pattern=r"^delete_post:"))

    # Команды автопостинга
    app.add_handler(CommandHandler("stop_autopost", stop_autopost_command))
    app.add_handler(CommandHandler("start_autopost", start_autopost_command))
    app.add_handler(CommandHandler("status", stats_command))
    app.add_handler(CommandHandler("jobs", next_posts_command))

    # Викторины и мудрости
    app.add_handler(PollAnswerHandler(poll_answer_handler))
    app.add_handler(CommandHandler("rating", rating_command))
    app.add_handler(CommandHandler("start_quiz", start_quiz_command))
    app.add_handler(CommandHandler("stop_quiz", stop_quiz_command))
    app.add_handler(CommandHandler("start_wisdom", start_wisdom_command))
    app.add_handler(CommandHandler("stop_wisdom", stop_wisdom_command))

    # Звуковая панель и другие команды
    app.add_handler(CommandHandler("sound", sound_command))
    app.add_handler(CallbackQueryHandler(sound_callback, pattern=r"^sound:"))
    app.add_handler(CommandHandler("sleep", sleep_command))
    app.add_handler(CommandHandler("morning", morning_command))
    app.add_handler(CommandHandler("logout", logout_command))
    app.add_handler(CommandHandler("reload_config", reload_config_command))

    # Казино и баланс
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("casino", casino_command))
    app.add_handler(CallbackQueryHandler(casino_callback_handler, pattern=r"^casino:"))
    app.add_handler(CallbackQueryHandler(handle_slots_bet_callback, pattern=r"^slots_bet:"))
    app.add_handler(CallbackQueryHandler(
        lambda update, context: handle_roulette_bet_callback(
            update.callback_query, 
            context, 
            update.callback_query.data.split(":")[1]
        ),
        pattern=r"^roulette_bet:"
    ))
    app.add_handler(CallbackQueryHandler(handle_change_bet, pattern=r"^change_bet:"))


    # Планировщик задач
    # Назначаем "ночной" джоб для сброса расписания
    midnight_config = schedule_config['midnight_reset']
    midnight_time = parse_time_from_string(midnight_config['time'])
    app.job_queue.run_daily(
        midnight_reset_callback,
        time=midnight_time,
        days=tuple(midnight_config['days']),
        name="reset_schedule"
    )

    # Еженедельный сброс викторин
    quiz_reset_config = schedule_config['weekly_quiz_reset']
    quiz_reset_time = parse_time_from_string(quiz_reset_config['time'])
    app.job_queue.run_daily(
        weekly_quiz_reset,
        time=quiz_reset_time,
        days=tuple(quiz_reset_config['days']),
        name="weekly_quiz_reset"
    )

    # При первом запуске бота — сразу же сделаем сброс расписания
    # чтобы назначить на сегодня (иначе оно впервые сработает только в полночь).
    app.job_queue.run_once(midnight_reset_callback, 0)
    # Проверяем, есть ли отложенные публикации, время которых уже прошло
    app.job_queue.run_once(reschedule_all_posts, 0)

    app.run_polling()

if __name__ == "__main__":
    main()
