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

    # Проверка наличия необходимых ключей
    if 'anecdotes' not in st:
        st['anecdotes'] = 0
    if 'ero-real' not in st:
        st['ero-real'] = 0
    if 'ero-anime' not in st:
        st['ero-anime'] = 0
    if 'standart-art' not in st:
        st['standart-art'] = 0
    if 'standart-meme' not in st:
        st['standart-meme'] = 0
    if 'single-meme' not in st:
        st['single-meme'] = 0

    # Подсчитываем общую сумму контента
    ero_content = min(st['ero-real'], st['ero-anime'] * 1.5) # Соотношение 3:2
    art_content = st['standart-art'] 
    meme_content = st['standart-meme'] + st['single-meme']
    
    # Для каждого поста требуется: 1 ero, 3 art и 6 meme
    # Соотношение 1:3:6
    total_posts_content = ero_content*1 + art_content*3 + meme_content*6
    
    # Делим на 10 (количество картинок в посте) и округляем в меньшую сторону
    count_posts = int(total_posts_content / 10)
    
    # Ограничиваем количество постов количеством доступных анекдотов
    count_posts = min(count_posts, st['anecdotes'])
    
    return count_posts

def predict_3videos_posts(stats):
    """
    Считает, сколько раз мы можем сделать пост с 3 видео (1 video-meme, 1 video-ero, 1 video-auto) + 1 анекдот.
    Если нет видео из категории video-auto или video-ero, то вместо него используется видео из video-meme.
    """
    st = stats.copy()
    
    # Проверка наличия необходимых ключей
    if 'anecdotes' not in st:
        st['anecdotes'] = 0
    if 'video-meme' not in st:
        st['video-meme'] = 0
    if 'video-ero' not in st:
        st['video-ero'] = 0
    if 'video-auto' not in st:
        st['video-auto'] = 0
        
    # Подсчитываем общую сумму видео-контента
    # Количество гарантированных постов = сумма всех видео / 3
    total_videos = st['video-meme'] + st['video-ero'] + st['video-auto']
    count_posts = int(total_videos / 3)
    
    # Ограничиваем количество постов количеством доступных анекдотов
    count_posts = min(count_posts, st['anecdotes'])
    
    return count_posts

def predict_full_days(stats):
    """
    Считает, сколько "полных дней" по схеме:
    - 2 поста "10 картинок"
    - 1 пост "3 видео"
    - 1 анекдот
    в сутки
    (т.е. всего 4 поста в день).
    
    Для видео учитывается возможность замены video-auto и video-ero на video-meme.
    """
    st = stats.copy()
    
    # Получаем количество постов от других предиктивных функций
    pics_posts = predict_10pics_posts(st)
    video_posts = predict_3videos_posts(st)
    anecdote_count = st.get('anecdotes', 0)
    
    # Для полного дня нужно:
    # - 2 поста с картинками
    # - 1 пост с видео
    # - 1 анекдот
    pics_days = pics_posts / 2  # 2 поста с картинками в день
    video_days = video_posts    # 1 пост с видео в день
    anecdote_days = anecdote_count  # 1 анекдот в день
    
    # Минимальное количество полных дней
    days = min(int(pics_days), int(video_days), int(anecdote_days))
    
    return days
