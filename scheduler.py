import datetime
import random
import logging
import json
import os
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton

from autopost import autopost_10_pics_callback, autopost_3_videos_callback
from quiz import quiz_post_callback, weekly_quiz_reset
from wisdom import wisdom_post_callback

import state  # Флаги автопубликации, викторины, мудрости и т.д.

from config import POST_CHAT_ID, schedule_config

logger = logging.getLogger(__name__)

# Файл для хранения отложенных публикаций
SCHEDULED_POSTS_FILE = "state_data/scheduled_posts.json"


async def reschedule_all_posts(context: ContextTypes.DEFAULT_TYPE):
    """
    При старте бота проходит по отложенным публикациям:
    - если время публикации прошло, публикует их сразу;
    - если ещё не наступило – планирует задачу (run_once) на нужное время.
    """
    scheduled_posts = load_scheduled_posts()
    now = datetime.datetime.now()

    for post_id, data in list(scheduled_posts.items()):
        try:
            scheduled_dt = datetime.datetime.fromisoformat(data["datetime"])
        except Exception as e:
            logger.error(f"Неверный формат даты в публикации {post_id}: {e}")
            scheduled_posts.pop(post_id, None)
            continue

        if scheduled_dt <= now:
            # Если время уже прошло – публикуем немедленно
            chat_id = data["chat_id"]
            text = data.get("text", "")
            media = data.get("media")
            media_type = data.get("media_type")
            try:
                if media:
                    if media_type == "photo":
                        await context.bot.send_photo(chat_id=chat_id, photo=media, caption=text)
                    elif media_type == "video":
                        await context.bot.send_video(chat_id=chat_id, video=media, caption=text)
                    elif media_type == "audio":
                        await context.bot.send_audio(chat_id=chat_id, audio=media, caption=text)
                    else:
                        await context.bot.send_message(chat_id=chat_id, text=text)
                else:
                    await context.bot.send_message(chat_id=chat_id, text=text)
                logger.info(f"Отложенная публикация {post_id} опубликована немедленно (запланировано на {scheduled_dt}).")
            except Exception as e:
                logger.error(f"Ошибка публикации отложенной публикации {post_id}: {e}")
            scheduled_posts.pop(post_id, None)
        else:
            # Если время еще не наступило – планируем задачу
            delay = (scheduled_dt - now).total_seconds()
            context.job_queue.run_once(
                delayed_post_callback,
                when=delay,
                name=f"delayed_{post_id}",
                data={"post_id": post_id}
            )
            logger.info(f"Запланирована публикация {post_id} на {scheduled_dt} (через {delay:.0f} сек).")
    save_scheduled_posts(scheduled_posts)


def load_scheduled_posts() -> dict:
    if not os.path.exists(SCHEDULED_POSTS_FILE):
        return {}
    try:
        with open(SCHEDULED_POSTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception as e:
        logger.error(f"Ошибка чтения {SCHEDULED_POSTS_FILE}: {e}")
    return {}


def save_scheduled_posts(data: dict):
    try:
        with open(SCHEDULED_POSTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Ошибка записи {SCHEDULED_POSTS_FILE}: {e}")


def random_time_in_range(start: datetime.time, end: datetime.time) -> datetime.time:
    start_s = start.hour * 3600 + start.minute * 60 + start.second
    end_s = end.hour * 3600 + end.minute * 60 + end.second
    r = random.randint(start_s, end_s)
    hh = r // 3600
    mm = (r % 3600) // 60
    ss = r % 60
    return datetime.time(hour=hh, minute=mm, second=ss)


def parse_time_from_string(time_str):
    """Преобразует строку времени в формате HH:MM в объект datetime.time"""
    hours, minutes = map(int, time_str.split(':'))
    return datetime.time(hour=hours, minute=minutes)


#
# ==== ЕЖЕДНЕВНОЕ РАСПИСАНИЕ (автопост, викторины, мудрость) ====
#

def schedule_autopost_for_today(job_queue):
    # Расписание утренних картинок
    morning_config = schedule_config['autopost']['morning_pics']
    start_time = parse_time_from_string(morning_config['time_range']['start'])
    end_time = parse_time_from_string(morning_config['time_range']['end'])
    time1 = random_time_in_range(start_time, end_time)
    job_queue.run_daily(
        autopost_10_pics_callback,
        time=time1,
        days=tuple(morning_config['days']),
        name="morning_pics"
    )

    # Расписание дневных видео
    day_videos_config = schedule_config['autopost']['day_videos']
    start_time = parse_time_from_string(day_videos_config['time_range']['start'])
    end_time = parse_time_from_string(day_videos_config['time_range']['end'])
    time2 = random_time_in_range(start_time, end_time)
    job_queue.run_daily(
        autopost_3_videos_callback,
        time=time2,
        days=tuple(day_videos_config['days']),
        name="day_videos"
    )

    # Расписание дневных картинок
    day_pics_config = schedule_config['autopost']['day_pics']
    start_time = parse_time_from_string(day_pics_config['time_range']['start'])
    end_time = parse_time_from_string(day_pics_config['time_range']['end'])
    time3 = random_time_in_range(start_time, end_time)
    job_queue.run_daily(
        autopost_10_pics_callback,
        time=time3,
        days=tuple(day_pics_config['days']),
        name="day_pics"
    )

    # Расписание вечерних картинок
    evening_pics_config = schedule_config['autopost']['evening_pics']
    start_time = parse_time_from_string(evening_pics_config['time_range']['start'])
    end_time = parse_time_from_string(evening_pics_config['time_range']['end'])
    time4 = random_time_in_range(start_time, end_time)
    job_queue.run_daily(
        autopost_10_pics_callback,
        time=time4,
        days=tuple(evening_pics_config['days']),
        name="evening_pics"
    )


def schedule_quizzes_for_today(job_queue):
    if not state.quiz_enabled or not schedule_config['quiz']['enabled']:
        return

    for i, quiz_time_config in enumerate(schedule_config['quiz']['quiz_times'], start=1):
        start_time = parse_time_from_string(quiz_time_config['time_range']['start'])
        end_time = parse_time_from_string(quiz_time_config['time_range']['end'])
        time = random_time_in_range(start_time, end_time)
        job_queue.run_daily(
            quiz_post_callback,
            time=time,
            days=tuple(quiz_time_config['days']),
            name=f"quiz_{i}"
        )


def schedule_wisdom_for_today(job_queue):
    if not state.wisdom_enabled or not schedule_config['wisdom']['enabled']:
        return
        
    wisdom_config = schedule_config['wisdom']
    start_time = parse_time_from_string(wisdom_config['time_range']['start'])
    end_time = parse_time_from_string(wisdom_config['time_range']['end'])
    time = random_time_in_range(start_time, end_time)
    job_queue.run_daily(
        wisdom_post_callback,
        time=time,
        days=tuple(wisdom_config['days']),
        name="wisdom"
    )


async def midnight_reset_callback(context: ContextTypes.DEFAULT_TYPE):
    job_queue = context.job_queue
    names_to_remove = [
        "morning_pics", "day_videos", "day_pics", "evening_pics",
        "quiz_1", "quiz_2", "quiz_3", "quiz_4", "quiz_5", "quiz_6", "quiz_7", "quiz_8",
        "wisdom",
        # Оставляем и старые имена для обратной совместимости
        "10pics_morning", "3videos_day", "10pics_evening", "10pics_day",
        "wisdom_of_day"
    ]
    for name in names_to_remove:
        for job in job_queue.get_jobs_by_name(name):
            job.schedule_removal()

    schedule_autopost_for_today(job_queue)
    schedule_quizzes_for_today(job_queue)
    schedule_wisdom_for_today(job_queue)
    logger.info("Расписание на сегодня обновлено (автопост, викторины, мудрость).")


#
# ==== РАЗОВЫЕ ОТЛОЖЕННЫЕ ПУБЛИКАЦИИ ====
#
# Логика:
# 1. Пользователь вводит команду "/schedule_post 15:30" и далее в сообщении многострочный текст.
#    Если к сообщению прикреплено медиа (фото, видео, аудио), то оно берется из поля caption.
# 2. Если указанное время уже прошло для сегодня, публикация назначается на следующий день.
# 3. После создания публикации бот отправляет сообщение с inline‑кнопками для смены даты:
#    - "Сегодня" (назначить на текущую дату),
#    - "Завтра" (на следующий день),
#    - "Выбрать дату" – в этом случае бот ждёт от пользователя нового ввода даты в формате YYYY-MM-DD HH:MM.
#

async def schedule_post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Если команда пришла с текстового сообщения, берем args из update.message.text,
    # если с медиа – из update.message.caption.
    if update.message.text:
        full_command = update.message.text
    elif update.message.caption:
        full_command = update.message.caption
    else:
        await update.message.reply_text("Не найден текст команды.")
        return

    # Разбиваем команду на слова:
    parts = full_command.split()
    if len(parts) < 2:
        await update.message.reply_text("Укажите время в формате HH:MM, например: /schedule_post 15:30")
        return

    # Первый элемент — это команда, второй должен быть временем:
    time_str = parts[1]
    try:
        time_obj = datetime.datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        await update.message.reply_text("Неверный формат времени. Используйте HH:MM, например: 15:30")
        return

    now = datetime.datetime.now()
    scheduled_date = now.date()
    scheduled_dt = datetime.datetime.combine(scheduled_date, time_obj)
    if scheduled_dt <= now:
        scheduled_dt += datetime.timedelta(days=1)

    # Текст публикации — всё, что идёт после первой строки (если есть)
    lines = full_command.splitlines()
    if len(lines) > 1:
        content_text = "\n".join(lines[1:]).strip()
    else:
        content_text = ""

    # Определяем наличие медиа – если есть, берем только первое
    media = None
    media_type = None
    if update.message.photo:
        media = update.message.photo[-1].file_id
        media_type = "photo"
    elif update.message.video:
        media = update.message.video.file_id
        media_type = "video"
    elif update.message.audio:
        media = update.message.audio.file_id
        media_type = "audio"

    scheduled_posts = load_scheduled_posts()
    post_id = str(len(scheduled_posts) + 1)
    data_to_post = {
        "chat_id": POST_CHAT_ID,
        "datetime": scheduled_dt.isoformat(),
        "text": content_text,
        "media": media,
        "media_type": media_type
    }
    scheduled_posts[post_id] = data_to_post
    save_scheduled_posts(scheduled_posts)

    delay = (scheduled_dt - now).total_seconds()
    context.job_queue.run_once(
        delayed_post_callback,
        when=delay,
        name=f"delayed_{post_id}",
        data={"post_id": post_id}
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Сегодня", callback_data=f"set_date:today:{post_id}"),
            InlineKeyboardButton("Завтра", callback_data=f"set_date:tomorrow:{post_id}"),
            InlineKeyboardButton("Выбрать дату", callback_data=f"set_date:custom:{post_id}")
        ]
    ])

    await update.message.reply_text(
        f"Публикация создана на {scheduled_dt.strftime('%Y-%m-%d %H:%M')}.",
        reply_markup=keyboard
    )



async def delayed_post_callback(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    post_id = job_data["post_id"]

    scheduled_posts = load_scheduled_posts()
    if post_id not in scheduled_posts:
        return

    data_to_post = scheduled_posts[post_id]
    chat_id = data_to_post["chat_id"]
    text = data_to_post.get("text", "")
    media = data_to_post.get("media")
    media_type = data_to_post.get("media_type")

    bot = context.bot
    try:
        if media:
            if media_type == "photo":
                await bot.send_photo(chat_id=chat_id, photo=media, caption=text)
            elif media_type == "video":
                await bot.send_video(chat_id=chat_id, video=media, caption=text)
            elif media_type == "audio":
                await bot.send_audio(chat_id=chat_id, audio=media, caption=text)
            else:
                await bot.send_message(chat_id=chat_id, text=text)
        else:
            await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        logger.error(f"Ошибка при отправке отложенной публикации {post_id}: {e}")

    scheduled_posts.pop(post_id, None)
    save_scheduled_posts(scheduled_posts)


async def change_date_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        _, option, post_id = query.data.split(":")
    except ValueError:
        await query.edit_message_text("Неверный формат данных.")
        return

    scheduled_posts = load_scheduled_posts()
    if post_id not in scheduled_posts:
        await query.edit_message_text("Публикация не найдена или уже отправлена.")
        return

    publication = scheduled_posts[post_id]
    original_dt = datetime.datetime.fromisoformat(publication["datetime"])
    now = datetime.datetime.now()

    if option == "today":
        new_date = now.date()
    elif option == "tomorrow":
        new_date = now.date() + datetime.timedelta(days=1)
    elif option == "custom":
        # Сохраняем post_id в context.user_data и просим ввести дату
        context.user_data["awaiting_custom_date"] = post_id
        await query.edit_message_text("Введите новую дату и время в формате YYYY-MM-DD HH:MM")
        return
    else:
        await query.edit_message_text("Неизвестный вариант даты.")
        return

    new_dt = datetime.datetime.combine(new_date, original_dt.time())
    if new_dt <= now:
        new_dt += datetime.timedelta(days=1)

    publication["datetime"] = new_dt.isoformat()
    save_scheduled_posts(scheduled_posts)

    # Удаляем старую задачу и создаем новую
    job_queue = context.job_queue
    for job in job_queue.get_jobs_by_name(f"delayed_{post_id}"):
        job.schedule_removal()
    delay = (new_dt - now).total_seconds()
    job_queue.run_once(
        delayed_post_callback,
        when=delay,
        name=f"delayed_{post_id}",
        data={"post_id": post_id}
    )

    await query.edit_message_text(f"Дата публикации изменена на {new_dt.strftime('%Y-%m-%d %H:%M')}.")


async def custom_date_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик для ввода кастомной даты.
    Если в context.user_data есть ключ 'awaiting_custom_date', то пытаемся распарсить сообщение.
    """
    if "awaiting_custom_date" not in context.user_data:
        return  # не ожидаем ввода

    post_id = context.user_data.pop("awaiting_custom_date")
    text = update.message.text.strip()
    try:
        new_dt = datetime.datetime.strptime(text, "%Y-%m-%d %H:%M")
    except ValueError:
        await update.message.reply_text("Неверный формат даты. Используйте YYYY-MM-DD HH:MM")
        # Сохраняем post_id обратно, чтобы можно было повторить ввод
        context.user_data["awaiting_custom_date"] = post_id
        return

    now = datetime.datetime.now()
    if new_dt <= now:
        new_dt = new_dt + datetime.timedelta(days=1)

    scheduled_posts = load_scheduled_posts()
    if post_id not in scheduled_posts:
        await update.message.reply_text("Публикация не найдена или уже отправлена.")
        return

    publication = scheduled_posts[post_id]
    publication["datetime"] = new_dt.isoformat()
    save_scheduled_posts(scheduled_posts)

    job_queue = context.job_queue
    for job in job_queue.get_jobs_by_name(f"delayed_{post_id}"):
        job.schedule_removal()
    delay = (new_dt - now).total_seconds()
    job_queue.run_once(
        delayed_post_callback,
        when=delay,
        name=f"delayed_{post_id}",
        data={"post_id": post_id}
    )

    await update.message.reply_text(f"Дата публикации изменена на {new_dt.strftime('%Y-%m-%d %H:%M')}.")


# Для корректной работы inline-кнопок и ввода новой даты необходимо зарегистрировать:
# - CallbackQueryHandler для change_date_callback, например:
#       app.add_handler(CallbackQueryHandler(change_date_callback, pattern=r"^set_date:"))
# - MessageHandler для текстовых сообщений, чтобы отлавливать ввод кастомной даты:
#       app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, custom_date_handler))
