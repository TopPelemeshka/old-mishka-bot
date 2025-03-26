# main.py
import logging
import datetime
import os
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PollAnswerHandler,
    filters,
)

from telegram.ext.filters import BaseFilter

# Убедитесь, что директория для логов существует
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

from config import TOKEN
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

# Импортируем из autopost
from autopost import (
    stop_autopost_command,
    start_autopost_command,
    stats_command,
    next_posts_command
)

from scheduler import midnight_reset_callback, schedule_post_command, change_date_callback, custom_date_handler, reschedule_all_posts
from quiz import poll_answer_handler, rating_command, weekly_quiz_reset
from state import load_state

from quiz import start_quiz_command, stop_quiz_command

from wisdom import start_wisdom_command, stop_wisdom_command

from handlers.logout_command import logout_command

from handlers.balance_command import balance_command
from casino.casino_main import casino_command, casino_callback_handler
from casino.slots import handle_slots_bet_callback
from casino.roulette import handle_roulette_bet_callback, handle_change_bet


# Настройка логирования
log_file = os.path.join(log_dir, "bot.log")

# Настройка логирования
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Уровень для всех логов (для вывода в консоль)

# Обработчик для вывода в консоль (все логи)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # Все логи будут выводиться в консоль
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

# Обработчик для записи в файл (только предупреждения и выше)
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.WARNING)  # В файл пишем только WARNING и выше
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

# Добавляем обработчики
logger.addHandler(console_handler)
logger.addHandler(file_handler)

class MediaCommandFilter(BaseFilter):
    def check_update(self, update):
        message = update.effective_message
        if not message:
            return False
        # Проверяем, есть ли медиа и caption начинается с "/schedule_post"
        if (message.photo or message.video or message.audio) and message.caption:
            return message.caption.startswith("/post")
        return False

def main() -> None:
    app = ApplicationBuilder().token(TOKEN).build()

    # --- ВАЖНО ---:
    # Считываем состояние флагов до того, как отдадим бота в run_polling
    load_state()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("getfileid", getfileid_command))
    app.add_handler(MessageHandler(filters.ANIMATION, catch_animation_fileid))
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

    # Новая команда для одноразовой отложенной публикации:
    app.add_handler(CommandHandler("post", schedule_post_command))
    app.add_handler(MessageHandler(MediaCommandFilter(), schedule_post_command))

    app.add_handler(CallbackQueryHandler(change_date_callback, pattern=r"^set_date:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, custom_date_handler))

    app.add_handler(CommandHandler("stop_autopost", stop_autopost_command))
    app.add_handler(CommandHandler("start_autopost", start_autopost_command))
    app.add_handler(CommandHandler("status", stats_command))
    app.add_handler(CommandHandler("jobs", next_posts_command))

    app.add_handler(PollAnswerHandler(poll_answer_handler))
    app.add_handler(CommandHandler("rating", rating_command))
    
    app.add_handler(CommandHandler("start_quiz", start_quiz_command))
    app.add_handler(CommandHandler("stop_quiz", stop_quiz_command))

    app.add_handler(CommandHandler("start_wisdom", start_wisdom_command))
    app.add_handler(CommandHandler("stop_wisdom", stop_wisdom_command))

    app.add_handler(CommandHandler("sound", sound_command))
    app.add_handler(CallbackQueryHandler(sound_callback, pattern=r"^sound:"))

    app.add_handler(CommandHandler("sleep", sleep_command))

    app.add_handler(CommandHandler("logout", logout_command))

    # Команда /balance
    app.add_handler(CommandHandler("balance", balance_command))

    # Команда /casino (показывает меню)
    app.add_handler(CommandHandler("casino", casino_command))

    # Единый колбэк для "casino:slots" и "casino:roulette"
    app.add_handler(CallbackQueryHandler(casino_callback_handler, pattern=r"^casino:"))

    # Колбэк для ставок в слотах: "slots_bet:5" и т.д.
    app.add_handler(CallbackQueryHandler(handle_slots_bet_callback, pattern=r"^slots_bet:"))

    # Обработчик для ставок в рулетке (pattern изменен)
    app.add_handler(CallbackQueryHandler(
        lambda update, context: handle_roulette_bet_callback(
            update.callback_query, 
            context, 
            update.callback_query.data.split(":")[1]
        ),
        pattern=r"^roulette_bet:"
    ))

    # Добавляем обработчик для изменения ставки
    app.add_handler(CallbackQueryHandler(handle_change_bet, pattern=r"^change_bet:"))



    # Назначаем "ночной" джоб (например, в 00:05)
    # чтобы каждый день пересоздавать расписание на случайное время
    app.job_queue.run_daily(
        midnight_reset_callback,
        time=datetime.time(hour=0, minute=5),
        days=(0,1,2,3,4,5,6),
        name="reset_schedule"
    )

    app.job_queue.run_daily(
        weekly_quiz_reset,
        time=datetime.time(hour=15, minute=00),
        days=(0,),
        name="weekly_quiz_reset"
    )

    # При первом запуске бота — сразу же сделаем сброс расписания
    # чтобы назначить на сегодня (иначе оно впервые сработает только в полночь).
    # Можно сделать так:
    #   app.job_queue.run_once(midnight_reset_callback, when=0)  # сразу же
    # ИЛИ руками вызвать функцию midnight_reset_callback(...)
    # Но вызывать придётся в контексте:
    #   midnight_reset_callback(context=app.job_queue)  # или создать MockContext.
    # Проще: назначим run_once:
    app.job_queue.run_once(midnight_reset_callback, 0)
    # Проверяем, есть ли отложенные публикации, время которых уже прошло
    app.job_queue.run_once(reschedule_all_posts, 0)

    app.run_polling()

if __name__ == "__main__":
    main()
