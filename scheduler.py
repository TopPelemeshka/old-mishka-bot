"""
Модуль планировщика для автоматизации публикаций и задач.
Обеспечивает:
- Расписание ежедневных автоматических публикаций
- Планирование викторин и мудрых мыслей
- Отложенную публикацию медиа-контента по команде
- Возможность указания произвольной даты для публикации
"""
import datetime
import random
import logging
import json
import os
from pathlib import Path
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo, InputMediaAudio, InputMediaDocument, InputMediaAnimation

from autopost import autopost_10_pics_callback, autopost_4_videos_callback
from quiz import quiz_post_callback, weekly_quiz_reset
from wisdom import wisdom_post_callback
from utils import random_time_in_range, parse_time_from_string

import state  # Флаги автопубликации, викторины, мудрости и т.д.

from config import POST_CHAT_ID, schedule_config

logger = logging.getLogger(__name__)

# Файл для хранения отложенных публикаций
SCHEDULED_POSTS_FILE = Path("state_data") / "scheduled_posts.json"


async def reschedule_all_posts(context: ContextTypes.DEFAULT_TYPE):
    """
    При старте бота проходит по отложенным публикациям:
    - если время публикации прошло, публикует их сразу;
    - если ещё не наступило – планирует задачу (run_once) на нужное время.
    Поддерживает как одиночные публикации, так и медиа-группы.
    
    Args:
        context: Контекст от планировщика задач Telegram
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
            
            try:
                # Проверяем, является ли публикация медиа-группой
                if data.get("is_media_group", False):
                    media_files = data.get("media_files", [])
                    
                    if not media_files:
                        await context.bot.send_message(chat_id=chat_id, text=text, read_timeout=300)
                    else:
                        # Создаем объекты InputMedia для отправки
                        media_to_send = []
                        for i, media_file in enumerate(media_files):
                            file_id = media_file.get("file_id")
                            media_type = media_file.get("type")
                            
                            # Для первого элемента добавляем caption, для остальных - нет
                            caption = text if i == 0 else None
                            
                            # Проверяем, что у нас есть caption и он корректного типа
                            if caption is not None and caption != "":
                                logger.info(f"[DEBUG] delayed_post_callback: Установка caption='{caption}' для i={i}")
                                
                                # Создаем объекты InputMedia с caption
                                if media_type == "photo":
                                    media_obj = InputMediaPhoto(media=file_id, caption=caption)
                                    media_to_send.append(media_obj)
                                elif media_type == "video":
                                    media_obj = InputMediaVideo(media=file_id, caption=caption)
                                    media_to_send.append(media_obj)
                                elif media_type == "audio":
                                    media_obj = InputMediaAudio(media=file_id, caption=caption)
                                    media_to_send.append(media_obj)
                                elif media_type == "document":
                                    media_obj = InputMediaDocument(media=file_id, caption=caption)
                                    media_to_send.append(media_obj)
                            else:
                                # Если caption нет, создаем объекты без него
                                if media_type == "photo":
                                    media_obj = InputMediaPhoto(media=file_id)
                                    media_to_send.append(media_obj)
                                elif media_type == "video":
                                    media_obj = InputMediaVideo(media=file_id)
                                    media_to_send.append(media_obj)
                                elif media_type == "audio":
                                    media_obj = InputMediaAudio(media=file_id)
                                    media_to_send.append(media_obj)
                                elif media_type == "document":
                                    media_obj = InputMediaDocument(media=file_id)
                                    media_to_send.append(media_obj)
                        
                        await context.bot.send_media_group(chat_id=chat_id, media=media_to_send, read_timeout=300)
                else:
                    # Обычная публикация
                    media = data.get("media")
                    media_type = data.get("media_type")
                    
                    if media:
                        if media_type == "photo":
                            await context.bot.send_photo(chat_id=chat_id, photo=media, caption=text, read_timeout=300)
                        elif media_type == "video":
                            await context.bot.send_video(chat_id=chat_id, video=media, caption=text, read_timeout=300)
                        elif media_type == "audio":
                            await context.bot.send_audio(chat_id=chat_id, audio=media, caption=text, read_timeout=300)
                        else:
                            await context.bot.send_message(chat_id=chat_id, text=text, read_timeout=300)
                    else:
                        await context.bot.send_message(chat_id=chat_id, text=text, read_timeout=300)
                
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
    """
    Загружает словарь отложенных публикаций из JSON файла.
    
    Returns:
        dict: Словарь с данными отложенных публикаций или пустой словарь, если файл не существует
    """
    if not SCHEDULED_POSTS_FILE.exists():
        logger.info(f"[DEBUG] load_scheduled_posts: Файл {SCHEDULED_POSTS_FILE} не существует, возвращаем пустой словарь")
        return {}
    try:
        with open(SCHEDULED_POSTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                # Логируем, что мы загрузили
                for post_id, post_data in data.items():
                    text = post_data.get("text", "")
                    logger.info(f"[DEBUG] load_scheduled_posts: Загружена публикация {post_id} с текстом: '{text}', тип: {type(text).__name__}")
                return data
    except Exception as e:
        logger.error(f"Ошибка чтения {SCHEDULED_POSTS_FILE}: {e}")
    return {}


def save_scheduled_posts(data: dict):
    """
    Сохраняет словарь отложенных публикаций в JSON файл.
    
    Args:
        data: Словарь с данными отложенных публикаций
    """
    try:
        # Создаем родительский каталог, если он не существует
        SCHEDULED_POSTS_FILE.parent.mkdir(exist_ok=True, parents=True)
        
        # Логируем, что мы сохраняем
        for post_id, post_data in data.items():
            text = post_data.get("text", "")
            logger.info(f"[DEBUG] save_scheduled_posts: Сохраняем публикацию {post_id} с текстом: '{text}', тип: {type(text).__name__}")
        
        with open(SCHEDULED_POSTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        logger.info(f"[DEBUG] save_scheduled_posts: Файл {SCHEDULED_POSTS_FILE} успешно сохранен")
    except Exception as e:
        logger.error(f"Ошибка записи {SCHEDULED_POSTS_FILE}: {e}")


#
# ==== ЕЖЕДНЕВНОЕ РАСПИСАНИЕ (автопост, викторины, мудрость) ====
#

def schedule_autopost_for_today(job_queue):
    """
    Планирует автоматические публикации на сегодня согласно расписанию из конфигурации.
    Включает утренние картинки, дневные видео, дневные и вечерние картинки.
    
    Args:
        job_queue: Очередь задач планировщика Telegram
    """
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
        autopost_4_videos_callback,
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
    """
    Планирует викторины на сегодня согласно расписанию из конфигурации.
    Если викторины отключены через state.quiz_enabled или в конфигурации, ничего не делает.
    
    Args:
        job_queue: Очередь задач планировщика Telegram
    """
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
    """
    Планирует публикацию мудрых мыслей на сегодня согласно расписанию из конфигурации.
    Если мудрые мысли отключены через state.wisdom_enabled или в конфигурации, ничего не делает.
    
    Args:
        job_queue: Очередь задач планировщика Telegram
    """
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
    """
    Обработчик для полуночного сброса и перепланирования всех задач.
    Удаляет текущие запланированные задачи и создает новые на следующий день.
    
    Args:
        context: Контекст от планировщика задач Telegram
    """
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
    
    # Планируем новые задачи на сегодня
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
    """
    Обработчик для отправки отложенной публикации, когда наступает запланированное время.
    Поддерживает как обычные сообщения с одним медиа, так и альбомы (медиа-группы).
    
    Args:
        context: Контекст от планировщика задач Telegram
    """
    job_data = context.job.data
    post_id = job_data["post_id"]
    logger.info(f"[DEBUG] delayed_post_callback: Вызван для публикации {post_id}")

    # Загружаем актуальный список публикаций на момент отправки
    scheduled_posts = load_scheduled_posts()
    if post_id not in scheduled_posts:
        logger.error(f"[DEBUG] delayed_post_callback: Публикация {post_id} не найдена")
        return

    data_to_post = scheduled_posts[post_id]
    chat_id = data_to_post["chat_id"]
    text = data_to_post.get("text", "")
    
    logger.info(f"[DEBUG] delayed_post_callback: Получен текст для публикации: '{text}'")
    
    bot = context.bot
    try:
        # Проверяем, является ли публикация медиа-группой
        if data_to_post.get("is_media_group", False):
            media_files = data_to_post.get("media_files", [])
            
            if not media_files:
                logger.error(f"[DEBUG] delayed_post_callback: Список медиа пуст для публикации {post_id}")
                await bot.send_message(chat_id=chat_id, text=text, read_timeout=300)
            else:
                logger.info(f"[DEBUG] delayed_post_callback: Отправка медиа-группы с {len(media_files)} файлами")
                
                # Преобразуем сохраненные file_ids в InputMedia объекты
                media_to_send = []
                for i, media_file in enumerate(media_files):
                    file_id = media_file.get("file_id")
                    media_type = media_file.get("type")
                    
                    # Для первого элемента добавляем caption, для остальных - нет
                    caption = text if i == 0 else None
                    
                    # Проверяем, что у нас есть caption и он корректного типа
                    if caption is not None and caption != "":
                        logger.info(f"[DEBUG] delayed_post_callback: Установка caption='{caption}' для i={i}")
                        
                        # Создаем объекты InputMedia с caption
                        if media_type == "photo":
                            media_obj = InputMediaPhoto(media=file_id, caption=caption)
                            media_to_send.append(media_obj)
                        elif media_type == "video":
                            media_obj = InputMediaVideo(media=file_id, caption=caption)
                            media_to_send.append(media_obj)
                        elif media_type == "audio":
                            media_obj = InputMediaAudio(media=file_id, caption=caption)
                            media_to_send.append(media_obj)
                        elif media_type == "document":
                            media_obj = InputMediaDocument(media=file_id, caption=caption)
                            media_to_send.append(media_obj)
                    else:
                        # Если caption нет, создаем объекты без него
                        if media_type == "photo":
                            media_obj = InputMediaPhoto(media=file_id)
                            media_to_send.append(media_obj)
                        elif media_type == "video":
                            media_obj = InputMediaVideo(media=file_id)
                            media_to_send.append(media_obj)
                        elif media_type == "audio":
                            media_obj = InputMediaAudio(media=file_id)
                            media_to_send.append(media_obj)
                        elif media_type == "document":
                            media_obj = InputMediaDocument(media=file_id)
                            media_to_send.append(media_obj)
                
                # Отправляем медиа-группу
                await bot.send_media_group(chat_id=chat_id, media=media_to_send, read_timeout=300)
                logger.info(f"[DEBUG] delayed_post_callback: Медиа-группа для публикации {post_id} успешно отправлена")
        else:
            # Обычная публикация с одним или без медиа
            media = data_to_post.get("media")
            media_type = data_to_post.get("media_type")
            
            if media:
                if media_type == "photo":
                    await bot.send_photo(chat_id=chat_id, photo=media, caption=text, read_timeout=300)
                elif media_type == "video":
                    await bot.send_video(chat_id=chat_id, video=media, caption=text, read_timeout=300)
                elif media_type == "audio":
                    await bot.send_audio(chat_id=chat_id, audio=media, caption=text, read_timeout=300)
                else:
                    await bot.send_message(chat_id=chat_id, text=text, read_timeout=300)
            else:
                await bot.send_message(chat_id=chat_id, text=text, read_timeout=300)
            
            logger.info(f"[DEBUG] delayed_post_callback: Публикация {post_id} успешно отправлена")
    except Exception as e:
        logger.error(f"[DEBUG] delayed_post_callback: Ошибка при отправке публикации {post_id}: {str(e)}")
        return  # В случае ошибки не удаляем публикацию, чтобы можно было попробовать снова

    # Перезагружаем список публикаций, чтобы получить актуальное состояние
    # (на случай, если другие публикации уже были удалены другими задачами)
    scheduled_posts = load_scheduled_posts()
    if post_id in scheduled_posts:
        # Удаляем публикацию из списка отложенных
        scheduled_posts.pop(post_id, None)
        save_scheduled_posts(scheduled_posts)
        logger.info(f"[DEBUG] delayed_post_callback: Публикация {post_id} удалена из списка отложенных")


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

#
# ==== ПРОСМОТР И УПРАВЛЕНИЕ ОТЛОЖЕННЫМИ ПУБЛИКАЦИЯМИ ====
#


async def list_scheduled_posts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда для отображения списка всех отложенных публикаций.
    При вызове выводит список постов и предоставляет кнопки для удаления.
    """
    scheduled_posts = load_scheduled_posts()
    
    if not scheduled_posts:
        await update.message.reply_text("Нет отложенных публикаций.")
        return
    
    text = "📋 Список отложенных публикаций:\n\n"
    
    for post_id, data in scheduled_posts.items():
        scheduled_dt = datetime.datetime.fromisoformat(data["datetime"])
        post_text = data.get("text", "")
        # Берем только первые 50 символов текста для краткого отображения
        preview = post_text[:50] + "..." if len(post_text) > 50 else post_text
        media_type = data.get("media_type", "текст")
        
        text += f"🔹 *ID {post_id}*: {scheduled_dt.strftime('%d.%m.%Y %H:%M')}\n"
        text += f"Тип: {media_type}, Превью: {preview}\n\n"
    
    # Создаем инлайн клавиатуру для удаления постов
    keyboard = []
    
    # Создаем строки кнопок по 2 кнопки в ряд для удаления отдельных постов
    row = []
    for post_id in scheduled_posts.keys():
        button = InlineKeyboardButton(f"Удалить #{post_id}", callback_data=f"delete_post:{post_id}")
        row.append(button)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    # Добавляем оставшиеся кнопки, если есть
    if row:
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def delete_post_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик кнопок удаления отложенных публикаций.
    Удаляет конкретную публикацию по нажатию на соответствующую кнопку.
    """
    query = update.callback_query
    await query.answer()
    
    _, post_id = query.data.split(":")
    scheduled_posts = load_scheduled_posts()
    
    # Удаляем конкретную публикацию
    if post_id not in scheduled_posts:
        await query.edit_message_text("Публикация не найдена или уже отправлена.")
        return
    
    # Удаляем задачу из планировщика
    job_queue = context.job_queue
    for job in job_queue.get_jobs_by_name(f"delayed_{post_id}"):
        job.schedule_removal()
    
    scheduled_posts.pop(post_id, None)
    save_scheduled_posts(scheduled_posts)
    
    # Проверяем остались ли еще отложенные публикации
    if scheduled_posts:
        # Создаем новое сообщение с обновленным списком публикаций
        text = "📋 Список отложенных публикаций:\n\n"
        
        for post_id, data in scheduled_posts.items():
            scheduled_dt = datetime.datetime.fromisoformat(data["datetime"])
            post_text = data.get("text", "")
            preview = post_text[:50] + "..." if len(post_text) > 50 else post_text
            media_type = data.get("media_type", "текст")
            
            text += f"🔹 *ID {post_id}*: {scheduled_dt.strftime('%d.%m.%Y %H:%M')}\n"
            text += f"Тип: {media_type}, Превью: {preview}\n\n"
        
        # Создаем обновленную инлайн клавиатуру
        keyboard = []
        row = []
        for pid in scheduled_posts.keys():
            button = InlineKeyboardButton(f"Удалить #{pid}", callback_data=f"delete_post:{pid}")
            row.append(button)
            if len(row) == 2:
                keyboard.append(row)
                row = []
        
        if row:
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await query.edit_message_text("Публикация удалена. Больше нет отложенных публикаций.")


async def talk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Немедленно отправляет сообщение в групповой чат без отложенной публикации.
    Поддерживает отправку медиа-вложений (фото, видео, аудио и другие типы файлов).
    Можно отправить несколько файлов в одном сообщении.
    
    Формат:
    /talk [текст сообщения]
    
    Args:
        update: Объект Update от Telegram
        context: Контекст от Telegram
    """
    # Если команда пришла с текстового сообщения, берем текст из update.message.text,
    # если с медиа – из update.message.caption.
    if update.message.text:
        full_command = update.message.text
    elif update.message.caption:
        full_command = update.message.caption
    else:
        await update.message.reply_text("Не найден текст команды.")
        return

    # Извлекаем текст сообщения (все, что идет после /talk)
    text_parts = full_command.split(' ', 1)
    if len(text_parts) > 1:
        message_text = text_parts[1].strip()
    else:
        message_text = ""

    # Определяем наличие медиа-файлов
    media_files = []
    
    # Проверяем различные типы медиа
    if update.message.photo:
        await context.bot.send_photo(
            chat_id=POST_CHAT_ID, 
            photo=update.message.photo[-1].file_id, 
            caption=message_text,
            read_timeout=300
        )
        await update.message.reply_text("Сообщение с фото отправлено в групповой чат.")
        return
    
    elif update.message.video:
        await context.bot.send_video(
            chat_id=POST_CHAT_ID, 
            video=update.message.video.file_id, 
            caption=message_text,
            read_timeout=300
        )
        await update.message.reply_text("Сообщение с видео отправлено в групповой чат.")
        return
        
    elif update.message.audio:
        await context.bot.send_audio(
            chat_id=POST_CHAT_ID, 
            audio=update.message.audio.file_id, 
            caption=message_text,
            read_timeout=300
        )
        await update.message.reply_text("Сообщение с аудио отправлено в групповой чат.")
        return
        
    elif update.message.animation:
        await context.bot.send_animation(
            chat_id=POST_CHAT_ID, 
            animation=update.message.animation.file_id, 
            caption=message_text,
            read_timeout=300
        )
        await update.message.reply_text("Сообщение с GIF отправлено в групповой чат.")
        return
        
    elif update.message.document:
        await context.bot.send_document(
            chat_id=POST_CHAT_ID, 
            document=update.message.document.file_id, 
            caption=message_text,
            read_timeout=300
        )
        await update.message.reply_text("Сообщение с документом отправлено в групповой чат.")
        return
        
    elif update.message.voice:
        await context.bot.send_voice(
            chat_id=POST_CHAT_ID, 
            voice=update.message.voice.file_id, 
            caption=message_text,
            read_timeout=300
        )
        await update.message.reply_text("Сообщение с голосовым сообщением отправлено в групповой чат.")
        return
        
    elif update.message.video_note:
        await context.bot.send_video_note(
            chat_id=POST_CHAT_ID, 
            video_note=update.message.video_note.file_id,
            read_timeout=300
        )
        if message_text:
            await context.bot.send_message(chat_id=POST_CHAT_ID, text=message_text, read_timeout=300)
        await update.message.reply_text("Видеосообщение отправлено в групповой чат.")
        return
    
    # Если нет медиа, отправляем простое текстовое сообщение
    elif message_text:
        await context.bot.send_message(chat_id=POST_CHAT_ID, text=message_text, read_timeout=300)
        await update.message.reply_text("Сообщение отправлено в групповой чат.")
        return
    
    # Если нет ни текста, ни медиа
    else:
        await update.message.reply_text("Пожалуйста, укажите текст сообщения или прикрепите медиа для отправки в групповой чат.")
        return


async def talk_media_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает команду /talk, отправленную с группой медиа-файлов (альбомом).
    Собирает все файлы из группы и отправляет их одним альбомом.
    Перезапускает таймер отправки при поступлении нового файла группы.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст от Telegram
    """
    message = update.effective_message
    media_group_id = message.media_group_id
    job_name = f"send_group_{media_group_id}"
    delay = 5 # Увеличиваем задержку до 5 секунд, чтобы успели собраться все изображения
    
    # Подробное логирование входящего сообщения
    caption_text = message.caption if message.caption else 'None'
    logger.info(f"[DEBUG] talk_media_group_command: Получено сообщение с media_group_id={media_group_id}. "
                f"Caption: '{caption_text}'. "
                f"Photo: {bool(message.photo)}, Video: {bool(message.video)}, "
                f"Audio: {bool(message.audio)}, Document: {bool(message.document)}")
    
    # Если у сообщения есть caption и он начинается с /post, игнорируем его
    # (добавляем для безопасности, должно фильтроваться на уровне MediaGroupTalkCommandFilter)
    if message.caption and message.caption.startswith("/post"):
        logger.warning(f"[DEBUG] talk_media_group_command: Сообщение с командой /post не должно сюда попадать! Игнорируем.")
        return

    # Инициализируем хранилище для медиа-групп, если его нет
    if 'media_groups' not in context.bot_data:
        context.bot_data['media_groups'] = {}
        logger.info(f"[DEBUG] talk_media_group_command: Инициализирован пустой словарь media_groups")
    
    # Формируем объект InputMedia для текущего сообщения
    current_media = None
    if message.photo:
        current_media = InputMediaPhoto(message.photo[-1].file_id)
    elif message.video:
        current_media = InputMediaVideo(message.video.file_id)
    elif message.audio:
        current_media = InputMediaAudio(message.audio.file_id)
    elif message.document:
        current_media = InputMediaDocument(message.document.file_id)
    # Добавьте другие типы медиа при необходимости (animation?)
    
    if not current_media:
        logger.warning(f"[DEBUG] talk_media_group_command: Не удалось создать InputMedia для сообщения в группе {media_group_id}")
        return

    # Если это первое сообщение из группы, которое мы видим
    if media_group_id not in context.bot_data['media_groups']:
        # Проверяем наличие caption именно в первом сообщении
        if message.caption and message.caption.startswith("/talk"):
            # Извлекаем текст сообщения
            text_parts = message.caption.split(' ', 1)
            message_text = text_parts[1].strip() if len(text_parts) > 1 else ""
            
            logger.info(f"[DEBUG] talk_media_group_command: Найдена команда /talk, извлечен текст: '{message_text}'")
            
            # Создаем запись для группы
            context.bot_data['media_groups'][media_group_id] = {
                'media': [current_media],
                'caption': message_text,
                'chat_id': message.chat_id, # Сохраняем chat_id пользователя для ответа
                'processed': False
            }
            logger.info(f"[DEBUG] talk_media_group_command: Создана новая группа {media_group_id} с caption='{message_text}'")
            
            # Удаляем существующие задачи для этой группы, если они есть
            current_jobs = context.job_queue.get_jobs_by_name(job_name)
            for job in current_jobs:
                job.schedule_removal()
                logger.info(f"[DEBUG] talk_media_group_command: Удалена существующая задача для группы {media_group_id}")
            
            # Планируем отправку
            context.job_queue.run_once(
                send_media_group_callback,
                when=delay, 
                data={'media_group_id': media_group_id},
                name=job_name
            )
            logger.info(f"[DEBUG] talk_media_group_command: Запланирована отправка группы {media_group_id} через {delay} сек.")
        else:
            # Если это первое сообщение, но без команды /talk - игнорируем
            logger.warning(f"[DEBUG] talk_media_group_command: Первое сообщение группы {media_group_id} без caption /talk. Игнорируем группу.")
            return
    else:
        # Это последующее сообщение из группы
        group_data = context.bot_data['media_groups'][media_group_id]
        logger.info(f"[DEBUG] talk_media_group_command: Найдена существующая группа {media_group_id} с {len(group_data['media'])} файлами")
        
        # Проверяем, что группа еще не была обработана
        if not group_data['processed']:
            group_data['media'].append(current_media)
            count = len(group_data['media'])
            logger.info(f"[DEBUG] talk_media_group_command: Добавлен файл в группу {media_group_id}. Всего файлов: {count}")
            
            # Удаляем существующие задачи для этой группы
            current_jobs = context.job_queue.get_jobs_by_name(job_name)
            for job in current_jobs:
                job.schedule_removal()
                logger.info(f"[DEBUG] talk_media_group_command: Удалена существующая задача для группы {media_group_id}")
            
            # Перезапускаем таймер отправки
            context.job_queue.run_once(
                send_media_group_callback,
                when=delay, 
                data={'media_group_id': media_group_id},
                name=job_name
            )
            logger.info(f"[DEBUG] talk_media_group_command: Перезапущен таймер отправки группы {media_group_id} на {delay} сек.")
        else:
             logger.info(f"[DEBUG] talk_media_group_command: Группа {media_group_id} уже обработана, игнорируем новый файл.")

async def send_media_group_callback(context: ContextTypes.DEFAULT_TYPE):
    """
    Функция обратного вызова для отправки накопленной медиа-группы.
    Отправляет все файлы, накопленные в группе, с указанным caption.
    
    Args:
        context: Контекст, содержащий данные о медиа-группе
    """
    # Получаем данные о группе
    media_group_id = context.job.data['media_group_id']
    logger.info(f"[DEBUG] send_media_group_callback: Вызван для группы {media_group_id}")
    
    if 'media_groups' not in context.bot_data:
        logger.error(f"[DEBUG] send_media_group_callback: Ошибка - словарь media_groups не найден в bot_data")
        return
    
    if media_group_id not in context.bot_data['media_groups']:
        logger.error(f"[DEBUG] send_media_group_callback: Ошибка - группа {media_group_id} не найдена в bot_data['media_groups']")
        return
    
    # Очищаем идентификатор медиа-группы из списка обрабатываемых
    from main import MediaGroupTalkCommandFilter
    MediaGroupTalkCommandFilter.remove_group(media_group_id)
    
    group_data = context.bot_data['media_groups'][media_group_id]
    
    # Отмечаем группу как обработанную
    group_data['processed'] = True
    
    # Создаем копии объектов InputMedia с нужным caption
    media_to_send = []
    for i, media in enumerate(group_data['media']):
        # Для первого элемента добавляем caption, для остальных - нет
        caption = group_data['caption'] if i == 0 else None
        
        logger.info(f"[DEBUG] send_media_group_callback: Обработка медиа {i}, caption='{caption}'")
        
        # Проверяем, что у нас есть caption и он корректного типа
        if caption is not None and caption != "":
            # Создаем новый объект с теми же данными, но с нужным caption
            if isinstance(media, InputMediaPhoto):
                media_obj = InputMediaPhoto(media=media.media, caption=caption)
                media_to_send.append(media_obj)
            elif isinstance(media, InputMediaVideo):
                media_obj = InputMediaVideo(media=media.media, caption=caption)
                media_to_send.append(media_obj)
            elif isinstance(media, InputMediaAudio):
                media_obj = InputMediaAudio(media=media.media, caption=caption)
                media_to_send.append(media_obj)
            elif isinstance(media, InputMediaDocument):
                media_obj = InputMediaDocument(media=media.media, caption=caption)
                media_to_send.append(media_obj)
            else:
                # Если тип неизвестен, попробуем обработать как фото
                logger.warning(f"[DEBUG] send_media_group_callback: Неизвестный тип медиа, пробуем как фото")
                try:
                    media_obj = InputMediaPhoto(media=media.media if hasattr(media, 'media') else media, caption=caption)
                    media_to_send.append(media_obj)
                except Exception as e:
                    logger.error(f"[DEBUG] send_media_group_callback: Не удалось обработать медиа неизвестного типа: {e}")
        else:
            # Без caption
            if isinstance(media, InputMediaPhoto):
                media_obj = InputMediaPhoto(media=media.media)
                media_to_send.append(media_obj)
            elif isinstance(media, InputMediaVideo):
                media_obj = InputMediaVideo(media=media.media)
                media_to_send.append(media_obj)
            elif isinstance(media, InputMediaAudio):
                media_obj = InputMediaAudio(media=media.media)
                media_to_send.append(media_obj)
            elif isinstance(media, InputMediaDocument):
                media_obj = InputMediaDocument(media=media.media)
                media_to_send.append(media_obj)
            else:
                # Если тип неизвестен, попробуем обработать как фото
                logger.warning(f"[DEBUG] send_media_group_callback: Неизвестный тип медиа, пробуем как фото")
                try:
                    media_obj = InputMediaPhoto(media=media.media if hasattr(media, 'media') else media)
                    media_to_send.append(media_obj)
                except Exception as e:
                    logger.error(f"[DEBUG] send_media_group_callback: Не удалось обработать медиа неизвестного типа: {e}")
    
    # Отправляем группу
    files_count = len(media_to_send)
    logger.info(f"[DEBUG] send_media_group_callback: Отправляем группу {media_group_id} с {files_count} файлами")
    
    if not media_to_send:
        logger.error(f"[DEBUG] send_media_group_callback: Ошибка - список медиа пуст для группы {media_group_id}")
        return
    
    try:
        await context.bot.send_media_group(
            chat_id=POST_CHAT_ID,
            media=media_to_send,
            read_timeout=300
        )
        logger.info(f"[DEBUG] send_media_group_callback: Группа {media_group_id} успешно отправлена")
        
        # Отправляем подтверждение пользователю
        await context.bot.send_message(
            chat_id=group_data['chat_id'],
            text=f"Альбом с {files_count} медиа-файлами создан на {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Сегодня", callback_data=f"set_date:today:{media_group_id}"),
                    InlineKeyboardButton("Завтра", callback_data=f"set_date:tomorrow:{media_group_id}"),
                    InlineKeyboardButton("Выбрать дату", callback_data=f"set_date:custom:{media_group_id}")
                ]
            ]),
            read_timeout=300
        )
    except Exception as e:
        logger.error(f"[DEBUG] send_media_group_callback: Ошибка при отправке группы {media_group_id}: {str(e)}")
        
        # Сообщаем пользователю об ошибке
        await context.bot.send_message(
            chat_id=group_data['chat_id'],
            text=f"Не удалось отправить альбом: {str(e)}",
            read_timeout=300
        )
    
    # Удаляем данные группы, если они больше не нужны
    del context.bot_data['media_groups'][media_group_id]


async def schedule_media_group_post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает команду /post, отправленную с группой медиа-файлов (альбомом).
    Собирает все файлы из группы и отправляет их одним альбомом в запланированное время.
    Перезапускает таймер сбора при поступлении нового файла группы.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст от Telegram
    """
    message = update.effective_message
    media_group_id = message.media_group_id
    job_name = f"collect_group_{media_group_id}"
    delay = 5  # Увеличиваем задержку до 5 секунд, чтобы успели собраться все изображения
    
    # Подробное логирование входящего сообщения
    caption_text = message.caption if message.caption else 'None'
    logger.info(f"[DEBUG] schedule_media_group_post_command: Получено сообщение с media_group_id={media_group_id}. "
                f"Caption: '{caption_text}'. "
                f"Photo: {bool(message.photo)}, Video: {bool(message.video)}, "
                f"Audio: {bool(message.audio)}, Document: {bool(message.document)}")
    
    # Проверяем, существует ли уже эта медиа-группа в обработке
    if media_group_id in context.bot_data.get('scheduled_media_groups', {}):
        # Это последующее сообщение из группы, обрабатываем его без проверки caption
        group_data = context.bot_data['scheduled_media_groups'][media_group_id]
        logger.info(f"[DEBUG] schedule_media_group_post_command: Найдена существующая группа {media_group_id} с {len(group_data['media'])} файлами")
        
        # Формируем объект InputMedia для текущего сообщения
        current_media = None
        media_type = None
        
        if message.photo:
            current_media = InputMediaPhoto(message.photo[-1].file_id)
            media_type = "photo"
        elif message.video:
            current_media = InputMediaVideo(message.video.file_id)
            media_type = "video"
        elif message.audio:
            current_media = InputMediaAudio(message.audio.file_id)
            media_type = "audio"
        elif message.document:
            current_media = InputMediaDocument(message.document.file_id)
            media_type = "document"
        
        if not current_media:
            logger.warning(f"[DEBUG] schedule_media_group_post_command: Не удалось создать InputMedia для сообщения в группе {media_group_id}")
            return
            
        # Проверяем, что группа еще не была обработана
        if not group_data['processed']:
            group_data['media'].append(current_media)
            group_data['media_types'].append(media_type)
            count = len(group_data['media'])
            logger.info(f"[DEBUG] schedule_media_group_post_command: Добавлен файл в группу {media_group_id}. Всего файлов: {count}")
            
            # Удаляем существующие задачи для этой группы
            current_jobs = context.job_queue.get_jobs_by_name(job_name)
            for job in current_jobs:
                job.schedule_removal()
                logger.info(f"[DEBUG] schedule_media_group_post_command: Удалена существующая задача для группы {media_group_id}")
            
            # Перезапускаем таймер сбора
            context.job_queue.run_once(
                collect_media_group_callback,
                when=delay, 
                data={'media_group_id': media_group_id},
                name=job_name
            )
            logger.info(f"[DEBUG] schedule_media_group_post_command: Перезапущен таймер сбора группы {media_group_id} на {delay} сек.")
        else:
            logger.info(f"[DEBUG] schedule_media_group_post_command: Группа {media_group_id} уже обработана, игнорируем новый файл.")
        return
    
    # Если это первое сообщение из группы - проверяем наличие caption с командой /post
    if not (message.caption and message.caption.startswith("/post")):
        logger.warning(f"[DEBUG] schedule_media_group_post_command: Первое сообщение группы {media_group_id} без команды /post. Игнорируем группу.")
        return
        
    # Инициализируем хранилище для медиа-групп отложенных постов, если его нет
    if 'scheduled_media_groups' not in context.bot_data:
        context.bot_data['scheduled_media_groups'] = {}
        logger.info(f"[DEBUG] schedule_media_group_post_command: Инициализирован пустой словарь scheduled_media_groups")
    
    # Формируем объект InputMedia для текущего сообщения
    current_media = None
    media_type = None
    
    if message.photo:
        current_media = InputMediaPhoto(message.photo[-1].file_id)
        media_type = "photo"
    elif message.video:
        current_media = InputMediaVideo(message.video.file_id)
        media_type = "video"
    elif message.audio:
        current_media = InputMediaAudio(message.audio.file_id)
        media_type = "audio"
    elif message.document:
        current_media = InputMediaDocument(message.document.file_id)
        media_type = "document"
    # Добавьте другие типы медиа при необходимости
    
    if not current_media:
        logger.warning(f"[DEBUG] schedule_media_group_post_command: Не удалось создать InputMedia для сообщения в группе {media_group_id}")
        return

    # Если это первое сообщение из группы, которое мы видим
    if media_group_id not in context.bot_data['scheduled_media_groups']:
        # Проверяем наличие caption с командой /post именно в первом сообщении
        if message.caption and message.caption.startswith("/post"):
            # Извлекаем время и текст сообщения
            parts = message.caption.split()
            if len(parts) < 2:
                await message.reply_text("Укажите время в формате HH:MM, например: /post 15:30")
                return
                
            time_str = parts[1]
            try:
                time_obj = datetime.datetime.strptime(time_str, "%H:%M").time()
            except ValueError:
                await message.reply_text("Неверный формат времени. Используйте HH:MM, например: 15:30")
                return
                
            now = datetime.datetime.now()
            scheduled_date = now.date()
            scheduled_dt = datetime.datetime.combine(scheduled_date, time_obj)
            if scheduled_dt <= now:
                scheduled_dt += datetime.timedelta(days=1)
                
            # Извлекаем текст сообщения (все, что идет после времени)
            # Разбиваем строку вручную, чтобы корректно получить все, что после времени
            command_and_time = f"/post {time_str}"
            if len(message.caption) > len(command_and_time):
                message_text = message.caption[len(command_and_time):].strip()
            else:
                message_text = ""
                
            logger.info(f"[DEBUG] Извлеченный текст сообщения: '{message_text}', тип: {type(message_text).__name__}")
            
            # Создаем запись для группы
            context.bot_data['scheduled_media_groups'][media_group_id] = {
                'media': [current_media],
                'media_types': [media_type],
                'caption': message_text,
                'chat_id': message.chat_id,  # Сохраняем chat_id пользователя для ответа
                'datetime': scheduled_dt.isoformat(),
                'processed': False
            }
            logger.info(f"[DEBUG] schedule_media_group_post_command: Создана новая группа {media_group_id} на {scheduled_dt}")
            
            # Удаляем существующие задачи для этой группы, если они есть
            current_jobs = context.job_queue.get_jobs_by_name(job_name)
            for job in current_jobs:
                job.schedule_removal()
                logger.info(f"[DEBUG] schedule_media_group_post_command: Удалена существующая задача для группы {media_group_id}")
            
            # Планируем завершение сбора медиа-группы
            context.job_queue.run_once(
                collect_media_group_callback,
                when=delay, 
                data={'media_group_id': media_group_id},
                name=job_name
            )
            logger.info(f"[DEBUG] schedule_media_group_post_command: Запланировано завершение сбора группы {media_group_id} через {delay} сек.")
        else:
            # Первое сообщение без валидной команды - игнорируем группу
            logger.warning(f"[DEBUG] schedule_media_group_post_command: Первое сообщение группы {media_group_id} без команды /post. Игнорируем группу.")
            return
    else:
        # Это последующее сообщение из группы
        group_data = context.bot_data['scheduled_media_groups'][media_group_id]
        logger.info(f"[DEBUG] schedule_media_group_post_command: Найдена существующая группа {media_group_id} с {len(group_data['media'])} файлами")
        
        # Проверяем, что группа еще не была обработана
        if not group_data['processed']:
            group_data['media'].append(current_media)
            group_data['media_types'].append(media_type)
            count = len(group_data['media'])
            logger.info(f"[DEBUG] schedule_media_group_post_command: Добавлен файл в группу {media_group_id}. Всего файлов: {count}")
            
            # Удаляем существующие задачи для этой группы
            current_jobs = context.job_queue.get_jobs_by_name(job_name)
            for job in current_jobs:
                job.schedule_removal()
                logger.info(f"[DEBUG] schedule_media_group_post_command: Удалена существующая задача для группы {media_group_id}")
            
            # Перезапускаем таймер сбора
            context.job_queue.run_once(
                collect_media_group_callback,
                when=delay, 
                data={'media_group_id': media_group_id},
                name=job_name
            )
            logger.info(f"[DEBUG] schedule_media_group_post_command: Перезапущен таймер сбора группы {media_group_id} на {delay} сек.")
        else:
            logger.info(f"[DEBUG] schedule_media_group_post_command: Группа {media_group_id} уже обработана, игнорируем новый файл.")


async def collect_media_group_callback(context: ContextTypes.DEFAULT_TYPE):
    """
    Функция обратного вызова для завершения сбора медиа-группы и планирования её отправки.
    Создаёт отложенную публикацию с собранными медиа-файлами.
    
    Args:
        context: Контекст, содержащий данные о медиа-группе
    """
    # Получаем данные о группе
    media_group_id = context.job.data['media_group_id']
    logger.info(f"[DEBUG] collect_media_group_callback: Вызван для группы {media_group_id}")
    
    if 'scheduled_media_groups' not in context.bot_data:
        logger.error(f"[DEBUG] collect_media_group_callback: Ошибка - словарь scheduled_media_groups не найден в bot_data")
        return
    
    if media_group_id not in context.bot_data['scheduled_media_groups']:
        logger.error(f"[DEBUG] collect_media_group_callback: Ошибка - группа {media_group_id} не найдена в scheduled_media_groups")
        return
    
    # Очищаем идентификатор медиа-группы из списка обрабатываемых
    from main import MediaGroupCommandFilter
    MediaGroupCommandFilter.remove_group(media_group_id)
    
    group_data = context.bot_data['scheduled_media_groups'][media_group_id]
    
    # Отмечаем группу как обработанную
    group_data['processed'] = True
    
    # Добавляем в хранилище отложенных публикаций
    scheduled_posts = load_scheduled_posts()
    post_id = str(len(scheduled_posts) + 1)
    
    # Преобразуем объекты InputMedia в file_ids для сохранения
    media_files = []
    for i, media in enumerate(group_data['media']):
        if isinstance(media, InputMediaPhoto):
            media_files.append({"file_id": media.media, "type": "photo"})
        elif isinstance(media, InputMediaVideo):
            media_files.append({"file_id": media.media, "type": "video"})
        elif isinstance(media, InputMediaAudio):
            media_files.append({"file_id": media.media, "type": "audio"})
        elif isinstance(media, InputMediaDocument):
            media_files.append({"file_id": media.media, "type": "document"})
    
    # Получаем текст для публикации
    caption_text = group_data.get('caption', '')
    logger.info(f"[DEBUG] collect_media_group_callback: Текст для публикации: '{caption_text}'")
    
    # Создаем запись для отложенной публикации
    data_to_post = {
        "chat_id": POST_CHAT_ID,
        "datetime": group_data['datetime'],
        "text": caption_text,
        "is_media_group": True,
        "media_files": media_files
    }
    
    # Проверяем, что текст правильно сохранился
    logger.info(f"[DEBUG] collect_media_group_callback: В data_to_post сохранен текст: '{data_to_post['text']}'")
    
    # Сохраняем в отложенные публикации
    scheduled_posts[post_id] = data_to_post
    save_scheduled_posts(scheduled_posts)
    
    # Проверим, что текст сохранился в словаре
    logger.info(f"[DEBUG] collect_media_group_callback: После сохранения text={scheduled_posts[post_id].get('text', 'НЕТ ТЕКСТА!')}")
    
    # Планируем отправку
    scheduled_dt = datetime.datetime.fromisoformat(group_data['datetime'])
    now = datetime.datetime.now()
    delay = (scheduled_dt - now).total_seconds()
    
    context.job_queue.run_once(
        delayed_post_callback,
        when=delay,
        name=f"delayed_{post_id}",
        data={"post_id": post_id}
    )
    
    # Создаем клавиатуру с кнопками для изменения даты
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Сегодня", callback_data=f"set_date:today:{post_id}"),
            InlineKeyboardButton("Завтра", callback_data=f"set_date:tomorrow:{post_id}"),
            InlineKeyboardButton("Выбрать дату", callback_data=f"set_date:custom:{post_id}")
        ]
    ])
    
    # Отправляем сообщение пользователю
    await context.bot.send_message(
        chat_id=group_data['chat_id'],
        text=f"Публикация альбома с {len(media_files)} медиа-файлами создана на {scheduled_dt.strftime('%Y-%m-%d %H:%M')}.",
        reply_markup=keyboard
    )
    
    # Удаляем данные группы, т.к. они уже перенесены в отложенные публикации
    del context.bot_data['scheduled_media_groups'][media_group_id]
    logger.info(f"[DEBUG] collect_media_group_callback: Альбом {media_group_id} запланирован на {scheduled_dt}")
