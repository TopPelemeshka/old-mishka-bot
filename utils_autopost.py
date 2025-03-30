# utils_autopost.py
"""
Модуль вспомогательных функций для автоматической публикации контента.
Обеспечивает:
- Работу с файлами контента (картинки, видео)
- Управление анекдотами
- Перемещение использованного контента в архив
- Статистику и предсказание возможного количества публикаций
"""
import os
import random
import shutil
import logging
from pathlib import Path

SEPARATOR = "=================================================="

from config import (
    ANECDOTES_FILE,
    ERO_ANIME_DIR,
    ERO_REAL_DIR,
    SINGLE_MEME_DIR,
    STANDART_ART_DIR,
    STANDART_MEME_DIR,
    VIDEO_MEME_DIR,
    VIDEO_ERO_DIR,
    VIDEO_AUTO_DIR,
    ARCHIVE_ERO_ANIME_DIR,
    ARCHIVE_ERO_REAL_DIR,
    ARCHIVE_SINGLE_MEME_DIR,
    ARCHIVE_STANDART_ART_DIR,
    ARCHIVE_STANDART_MEME_DIR,
    ARCHIVE_VIDEO_MEME_DIR,
    ARCHIVE_VIDEO_ERO_DIR,
    ARCHIVE_VIDEO_AUTO_DIR,
)

logger = logging.getLogger(__name__)

def is_valid_file(file_path):
    """
    Проверяет, что файл подходит для отправки в Telegram.
    
    Файл должен:
    - Не быть .gitkeep
    - Не быть пустым
    - Иметь допустимое расширение
    - Быть доступным для чтения
    - Не превышать ограничение Telegram по размеру (50 МБ)
    
    Args:
        file_path: Путь к проверяемому файлу
        
    Returns:
        bool: True если файл валидный, False в противном случае
    """
    try:
        # Проверка, что это не .gitkeep
        if os.path.basename(file_path) == '.gitkeep':
            logger.warning(f"Файл {file_path} является .gitkeep")
            return False
        
        # Проверка, что файл существует
        if not os.path.exists(file_path):
            logger.warning(f"Файл {file_path} не существует")
            return False
        
        # Проверка, что файл не пустой
        if os.path.getsize(file_path) == 0:
            logger.warning(f"Файл {file_path} пустой")
            return False
        
        # Проверка, что файл доступен для чтения
        if not os.access(file_path, os.R_OK):
            logger.warning(f"Файл {file_path} недоступен для чтения")
            return False
        
        # Проверка размера файла (не более 50 МБ для видео, Telegram ограничение)
        max_size = 50 * 1024 * 1024  # 50 МБ в байтах
        if os.path.getsize(file_path) > max_size:
            logger.warning(f"Файл {file_path} превышает максимальный размер 50 МБ")
            return False
        
        # Проверка расширения
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.webp']
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in valid_extensions:
            logger.warning(f"Файл {file_path} имеет недопустимое расширение {ext}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при проверке файла {file_path}: {str(e)}")
        return False

def get_top_anecdote_and_remove():
    """
    Возвращает случайный анекдот из файла и удаляет его из файла.
    Анекдоты в файле разделены строкой-разделителем SEPARATOR.
    
    Returns:
        str|None: Текст анекдота или None, если анекдотов нет или произошла ошибка
    """
    try:
        if not os.path.exists(ANECDOTES_FILE):
            logger.warning(f"Файл анекдотов {ANECDOTES_FILE} не существует")
            return None

        with open(ANECDOTES_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            logger.warning(f"Файл анекдотов {ANECDOTES_FILE} пуст")
            return None

        # Разбиваем контент на отдельные анекдоты по разделителю
        parts = [x.strip() for x in content.split(SEPARATOR) if x.strip()]
        if not parts:
            logger.warning(f"В файле анекдотов {ANECDOTES_FILE} нет анекдотов")
            return None

        # Выбираем случайный индекс
        idx = random.randint(0, len(parts) - 1)
        anecdote = parts.pop(idx)

        # Сохраняем оставшиеся анекдоты обратно в файл
        remaining_str = f"\n{SEPARATOR}\n".join(parts)
        with open(ANECDOTES_FILE, "w", encoding="utf-8") as f:
            f.write(remaining_str.strip())

        return anecdote
    except Exception as e:
        logger.error(f"Ошибка при получении анекдота: {str(e)}")
        return None


def count_anecdotes():
    """
    Подсчитывает количество оставшихся анекдотов в файле.
    
    Returns:
        int: Количество анекдотов или 0, если файла нет или произошла ошибка
    """
    try:
        if not os.path.exists(ANECDOTES_FILE):
            return 0
        with open(ANECDOTES_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return 0
        parts = [x.strip() for x in content.split(SEPARATOR) if x.strip()]
        return len(parts)
    except Exception as e:
        logger.error(f"Ошибка при подсчете анекдотов: {str(e)}")
        return 0

def get_random_file_from_folder(folder):
    """
    Возвращает путь к случайному файлу из указанной папки.
    Выбираются только валидные файлы (проверка через is_valid_file).
    
    Args:
        folder: Путь к папке, из которой нужно выбрать файл
        
    Returns:
        str|None: Путь к случайному файлу или None, если папка пуста или произошла ошибка
    """
    try:
        if not folder or not os.path.exists(folder) or not os.path.isdir(folder):
            logger.warning(f"Директория {folder} не существует или не является директорией")
            return None
        
        # Получаем список файлов и фильтруем только валидные
        all_files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
        valid_files = [os.path.join(folder, f) for f in all_files if is_valid_file(os.path.join(folder, f))]
        
        if not valid_files:
            logger.warning(f"В директории {folder} нет валидных файлов")
            return None
        
        return random.choice(valid_files)
    except Exception as e:
        logger.error(f"Ошибка при получении случайного файла из {folder}: {str(e)}")
        return None

def move_file_to_archive(filepath, category):
    """
    Перемещает использованный файл в соответствующую архивную папку.
    
    Args:
        filepath: Путь к файлу, который нужно переместить
        category: Категория файла (ero-anime, ero-real, standart-meme и т.д.)
        
    Returns:
        bool: True если перемещение успешно, False в случае ошибки
    """
    try:
        if not os.path.exists(filepath):
            logger.warning(f"Не удалось переместить файл {filepath} в архив: файл не существует")
            return False
            
        # Определяем архивную директорию на основе категории
        if category == "ero-anime":
            archive_dir = ARCHIVE_ERO_ANIME_DIR
        elif category == "ero-real":
            archive_dir = ARCHIVE_ERO_REAL_DIR
        elif category == "single-meme":
            archive_dir = ARCHIVE_SINGLE_MEME_DIR
        elif category == "standart-art":
            archive_dir = ARCHIVE_STANDART_ART_DIR
        elif category == "standart-meme":
            archive_dir = ARCHIVE_STANDART_MEME_DIR
        elif category == "video-meme":
            archive_dir = ARCHIVE_VIDEO_MEME_DIR
        elif category == "video-ero":
            archive_dir = ARCHIVE_VIDEO_ERO_DIR
        elif category == "video-auto":
            archive_dir = ARCHIVE_VIDEO_AUTO_DIR
        else:
            # Для прочих категорий, если появятся
            archive_dir = os.path.join("archive", category)

        # Создаем директорию архива, если она не существует
        os.makedirs(archive_dir, exist_ok=True)

        basename = os.path.basename(filepath)
        new_path = os.path.join(archive_dir, basename)
        
        # Проверяем, существует ли уже файл с таким именем в архиве
        if os.path.exists(new_path):
            # Добавляем к имени файла временную метку
            base, ext = os.path.splitext(basename)
            import time
            timestamp = int(time.time())
            new_basename = f"{base}_{timestamp}{ext}"
            new_path = os.path.join(archive_dir, new_basename)
            
        # Перемещаем файл в архив
        shutil.move(filepath, new_path)
        logger.info(f"Файл {filepath} перемещен в архив: {new_path}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при перемещении файла {filepath} в архив {archive_dir}: {str(e)}")
        return False

def count_files_in_folder(folder):
    """Подсчитать число файлов (только файлы) в папке."""
    try:
        if not folder or not os.path.exists(folder):
            logger.warning(f"Директория {folder} не существует")
            return 0
        
        # Подсчитываем только валидные файлы (не .gitkeep и т.д.)
        valid_files = [f for f in os.listdir(folder) 
                      if os.path.isfile(os.path.join(folder, f)) and is_valid_file(os.path.join(folder, f))]
        return len(valid_files)
    except Exception as e:
        logger.error(f"Ошибка при подсчете файлов в директории {folder}: {str(e)}")
        return 0

def get_available_stats():
    """
    Возвращает словарь с информацией о количестве файлов в каждой категории + анекдоты.
    """
    stats = {
        "ero-anime": count_files_in_folder(ERO_ANIME_DIR),
        "ero-real": count_files_in_folder(ERO_REAL_DIR),
        "single-meme": count_files_in_folder(SINGLE_MEME_DIR),
        "standart-art": count_files_in_folder(STANDART_ART_DIR),
        "standart-meme": count_files_in_folder(STANDART_MEME_DIR),
        "video-meme": count_files_in_folder(VIDEO_MEME_DIR),
        "video-ero": count_files_in_folder(VIDEO_ERO_DIR),
        "video-auto": count_files_in_folder(VIDEO_AUTO_DIR),
        "anecdotes": count_anecdotes()
    }
    return stats

def predict_10pics_posts(stats):
    """
    Считает, сколько раз мы можем сделать пост с 10 картинками, учитывая текущие остатки stats.
    Конфигурация:
        1 - ero-real
        2 - standart-art/standart-meme
        3 - ero-anime
        4 - single-meme/standart-meme
        5 - ero-real
        6 - standart-meme
        7 - ero-anime
        8 - standart-meme
        9 - ero-real
        10 - standart-meme
    Каждый такой пост требует 1 анекдот.
    """
    # Будем копировать словарь, чтобы не портить оригинал
    st = stats.copy()

    count_posts = 0
    while True:
        # Нужно 1 анекдот
        if st["anecdotes"] < 1:
            break

        # Нужно 3 ero-real (пункты 1,5,9)
        if st["ero-real"] < 3:
            break

        # Нужно 2 ero-anime (пункты 3,7)
        if st["ero-anime"] < 2:
            break

        # Нужно минимум 3 "standart-meme" (пункты 6,8,10) — это без учёта фолбэка
        if st["standart-meme"] < 3:
            break

        # Позиция 2: standart-art, а если нет — standart-meme
        need_art_for_2 = 1
        # Позиция 4: single-meme, а если нет — standart-meme
        need_single_for_4 = 1

        # Посчитаем, сколько *дополнительно* может понадобиться "standart-meme", если нет арт или single
        additional_meme_needed = 0

        # Есть ли standart-art для позиции 2?
        if st["standart-art"] >= need_art_for_2:
            # используем 1 шт. standart-art
            pass
        else:
            # fallback в stand-meme
            additional_meme_needed += need_art_for_2

        # Есть ли single-meme для позиции 4?
        if st["single-meme"] >= need_single_for_4:
            # используем 1 шт. single-meme
            pass
        else:
            # fallback в stand-meme
            additional_meme_needed += need_single_for_4

        # Проверим, хватит ли "standart-meme" на fallback + 3 обязательных
        total_meme_needed = 3 + additional_meme_needed
        if st["standart-meme"] < total_meme_needed:
            break

        # Если мы дошли сюда, значит можем сформировать пост
        # "Списываем" ресурсы:
        st["anecdotes"] -= 1
        st["ero-real"] -= 3
        st["ero-anime"] -= 2
        st["standart-meme"] -= 3  # обязательная часть

        # Позиция 2:
        if st["standart-art"] >= 1:
            st["standart-art"] -= 1
        else:
            st["standart-meme"] -= 1  # fallback

        # Позиция 4:
        if st["single-meme"] >= 1:
            st["single-meme"] -= 1
        else:
            st["standart-meme"] -= 1  # fallback

        count_posts += 1

    return count_posts

def predict_3videos_posts(stats):
    """
    Считает, сколько раз мы можем сделать пост с 3 видео (1 video-meme, 1 video-ero, 1 video-auto) + 1 анекдот.
    Если нет видео из категории video-auto или video-ero, то вместо него используется видео из video-meme.
    """
    st = stats.copy()
    count_posts = 0
    while True:
        # Нужно 1 анекдот
        if st["anecdotes"] < 1:
            break
            
        # Нужно минимум 1 видео из video-meme (обязательно)
        if st["video-meme"] < 1:
            break
            
        # Подсчитаем, сколько всего видео из video-meme нам понадобится
        needed_meme_videos = 1
        
        # Проверяем video-ero (если нет, нужно ещё видео из video-meme)
        if st["video-ero"] < 1:
            needed_meme_videos += 1
            
        # Проверяем video-auto (если нет, нужно ещё видео из video-meme)
        if st["video-auto"] < 1:
            needed_meme_videos += 1
            
        # Проверяем хватает ли в итоге видео из video-meme
        if st["video-meme"] < needed_meme_videos:
            break
            
        # Если мы дошли сюда, значит можем сформировать пост
        # "Списываем" ресурсы:
        st["anecdotes"] -= 1
        
        # Списываем видео из video-meme (минимум 1, максимум 3)
        st["video-meme"] -= needed_meme_videos
        
        # Списываем video-ero, если он есть
        if st["video-ero"] >= 1:
            st["video-ero"] -= 1
            
        # Списываем video-auto, если он есть
        if st["video-auto"] >= 1:
            st["video-auto"] -= 1

        count_posts += 1

    return count_posts

def predict_full_days(stats):
    """
    Считает, сколько "полных дней" по схеме:
    - 3 поста "10 картинок"
    - 1 пост "3 видео"
    в сутки
    (т.е. всего 4 анекдота в день и соответствующие файлы).
    
    Для видео учитывается возможность замены video-auto и video-ero на video-meme.
    """
    st = stats.copy()
    days = 0
    while True:
        # За 1 день нужно 3 поста с 10 картинками + 1 пост с 3 видео.
        # Суммарно 4 анекдота.
        if st["anecdotes"] < 4:
            break

        # Для 3 постов "10 картинок" по описанной схеме (см. predict_10pics_posts — но нам нужно сделать это 3 раза)
        # Упростим: 3 * (3 ero-real, 2 ero-anime, ...). Но нужно учесть fallback на stand-meme и т.д.

        # Проверим сразу, хватит ли ero-real и ero-anime:
        if st["ero-real"] < 9:   # 3*3
            break
        if st["ero-anime"] < 6: # 2*3
            break

        # stand-meme: минимум 3*3 = 9 на гарантированные позиции (6,8,10) в каждом посте.
        # Но также нужно учесть fallback:
        # Позиция 2 (в каждом посте): всего 3 шт. -> при нехватке stand-art => fallback stand-meme
        # Позиция 4 (в каждом посте): всего 3 шт. -> при нехватке single-meme => fallback stand-meme
        # То есть потенциально ещё +3 (если stand-art=0) +3 (если single-meme=0) = +6. Итого максимум 15.

        # Посчитаем, сколько у нас stand-art и single-meme
        # Для 3 постов нужно 3 stand-art (позиция 2) и 3 single-meme (позиция 4), если хотим без fallback.
        fallback_meme_needed = 0

        # Позиция 2: нужно 3 stand-art
        needed_art = 3
        if st["standart-art"] < needed_art:
            fallback_meme_needed += (needed_art - st["standart-art"])

        # Позиция 4: нужно 3 single-meme
        needed_single = 3
        if st["single-meme"] < needed_single:
            fallback_meme_needed += (needed_single - st["single-meme"])

        total_meme_needed = 9 + fallback_meme_needed
        if st["standart-meme"] < total_meme_needed:
            break

        # Для 1 поста "3 видео" нужно video-meme и, возможно, video-ero и video-auto
        
        # Подсчитаем, сколько всего video-meme нам понадобится
        needed_meme_videos = 1
        
        # Если нет video-ero, то нужно ещё одно video-meme
        if st["video-ero"] < 1:
            needed_meme_videos += 1
            
        # Если нет video-auto, то нужно ещё одно video-meme
        if st["video-auto"] < 1:
            needed_meme_videos += 1
            
        # Проверяем, хватает ли нам video-meme
        if st["video-meme"] < needed_meme_videos:
            break

        # Если все проверки пройдены, то "списываем" ресурсы на 3*10pics + 1*3videos
        st["anecdotes"] -= 4  # 3 для 10pics + 1 для видео
        st["ero-real"] -= 9   # 3*3 для 10pics
        st["ero-anime"] -= 6  # 2*3 для 10pics

        # stand-meme - списываем 9 «обязательных» для 10pics
        st["standart-meme"] -= 9

        # stand-art:
        if st["standart-art"] >= needed_art:
            st["standart-art"] -= needed_art
        else:
            # используем, что есть
            used_art = st["standart-art"]
            st["standart-art"] = 0
            # оставшиеся идут в fallback
            fallback_for_art = needed_art - used_art
            st["standart-meme"] -= fallback_for_art

        # single-meme:
        if st["single-meme"] >= needed_single:
            st["single-meme"] -= needed_single
        else:
            used_single = st["single-meme"]
            st["single-meme"] = 0
            fallback_for_single = needed_single - used_single
            st["standart-meme"] -= fallback_for_single

        # Списываем видео
        st["video-meme"] -= needed_meme_videos
        
        # Если есть video-ero, списываем 1
        if st["video-ero"] >= 1:
            st["video-ero"] -= 1
            
        # Если есть video-auto, списываем 1
        if st["video-auto"] >= 1:
            st["video-auto"] -= 1

        days += 1

    return days
