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
import time
from pathlib import Path

SEPARATOR = "=================================================="

import config
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
        
        # Определяем директорию архива в зависимости от категории
        archive_dir = None
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
            logger.warning(f"Неизвестная категория: {category}")
            return False
        
        # Создаем директорию архива, если она не существует
        os.makedirs(archive_dir, exist_ok=True)
        
        # Получаем имя файла без пути
        filename = os.path.basename(filepath)
        new_path = os.path.join(archive_dir, filename)
        
        # Если уже есть файл с таким именем, добавляем к имени временную метку
        if os.path.exists(new_path):
            name, ext = os.path.splitext(filename)
            timestamp = int(time.time())  # Текущая временная метка Unix
            new_path = os.path.join(archive_dir, f"{name}_{timestamp}{ext}")
        
        # Перемещаем файл
        shutil.move(filepath, new_path)
        logger.info(f"Файл {filepath} успешно перемещен в архив: {new_path}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при перемещении файла {filepath} в архив: {str(e)}")
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
    Собирает статистику по доступным файлам для публикации.
    
    Returns:
        dict: Словарь с количеством файлов каждого типа
    """
    result = {
        'ero-anime': count_files_in_folder(ERO_ANIME_DIR),
        'ero-real': count_files_in_folder(ERO_REAL_DIR),
        'single-meme': count_files_in_folder(SINGLE_MEME_DIR),
        'standart-art': count_files_in_folder(STANDART_ART_DIR),
        'standart-meme': count_files_in_folder(STANDART_MEME_DIR),
        'video-meme': count_files_in_folder(VIDEO_MEME_DIR),
        'video-ero': count_files_in_folder(VIDEO_ERO_DIR),
        'video-auto': count_files_in_folder(VIDEO_AUTO_DIR),
        'anecdotes': count_anecdotes(),
    }
    return result

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
    
    Returns:
        dict: Словарь с количеством постов, которые можно сделать для каждой категории
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

    # Возвращаем количество постов, которые можно сделать для каждой категории
    # Делим на 10, потому что у нас 10 картинок в посте
    result = {
        'ero-real': st['ero-real'] // 10,
        'ero-anime': st['ero-anime'] // 10,
        'standart-art': st['standart-art'] // 10,
        'standart-meme': st['standart-meme'] // 10,
        'single-meme': st['single-meme'] // 10
    }
    
    return result

def predict_4videos_posts(stats):
    """
    Считает, сколько раз мы можем сделать пост с 4 видео (1 video-meme, 1 video-ero, 2 video-auto) + 1 анекдот.
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
        
    # Количество постов, которые можно создать исходя из имеющихся видео
    # Для поста нужно 1 video-meme, 1 video-ero и 2 video-auto
    # Если какие-то видео отсутствуют, они заменяются на video-meme
    
    # Вычисляем, сколько video-meme нам понадобится для замены
    need_replacements = 0
    
    # Если нет video-ero, нужна 1 замена
    if st['video-ero'] == 0:
        need_replacements += 1
    
    # Если video-auto меньше 2, нужны замены (1 или 2)
    if st['video-auto'] < 2:
        need_replacements += (2 - st['video-auto'])
    
    # Рассчитываем, сколько постов можем сделать
    
    # Количество постов по video-meme (учитывая возможные замены)
    # Каждый пост требует минимум 1 video-meme + need_replacements для замены
    posts_from_meme = st['video-meme'] // (1 + need_replacements) if (1 + need_replacements) > 0 else 0
    
    # Количество постов по video-ero (если нет замен)
    posts_from_ero = st['video-ero'] if need_replacements < 1 else 0
    
    # Количество постов по video-auto (нужно 2 на пост)
    posts_from_auto = st['video-auto'] // 2 if need_replacements < 2 else 0
    
    # Определяем лимитирующий фактор
    if need_replacements > 0:
        # Если нужны замены, лимитирует video-meme
        count_posts = posts_from_meme
    else:
        # Если замены не нужны, лимитирует минимум из всех трех
        count_posts = min(posts_from_meme, posts_from_ero, posts_from_auto)
    
    # Ограничиваем количество постов количеством доступных анекдотов
    count_posts = min(count_posts, st['anecdotes'])
    
    return count_posts

def predict_full_days(stats):
    """
    Считает, сколько "полных дней" по схеме:
    - 3 поста "10 картинок"
    - 1 пост "4 видео"
    - 1 анекдот
    в сутки
    (т.е. всего 4 анекдота в день: 3 для картинок + 1 для видео).
    
    Для видео учитывается возможность замены video-auto и video-ero на video-meme.
    
    Returns:
        dict: Словарь с количеством полных дней и ограничивающим фактором
    """
    st = stats.copy()
    
    # Получаем количество постов для разных категорий
    pics_predictions = predict_10pics_posts(st)
    total_pics_posts = sum(pics_predictions.values())
    pics_days = total_pics_posts / 3  # 3 поста с картинками в день
    
    video_posts = predict_4videos_posts(st)
    video_days = video_posts    # 1 пост с видео в день
    
    anecdote_count = st.get('anecdotes', 0)
    anecdote_days = anecdote_count / 4 if anecdote_count else 0 # 4 анекдота в день
    
    # Определяем ограничивающий фактор
    limiting_factors = {
        'pics': int(pics_days),
        'videos': int(video_days),
        'anecdotes': int(anecdote_days)
    }
    
    min_days = min(limiting_factors.values())
    
    # Находим, какая категория ограничивает количество дней
    limiting_factor = None
    for factor, days in limiting_factors.items():
        if days == min_days:
            limiting_factor = factor
            break
    
    # Если ограничение по картинкам, определяем конкретную категорию
    if limiting_factor == 'pics':
        min_category = None
        min_value = float('inf')
        for category, count in pics_predictions.items():
            if count < min_value:
                min_value = count
                min_category = category
        
        limiting_factor = min_category
    
    # Если ограничение по видео и video-ero == 0, ограничивающий фактор - video-ero
    # Иначе проверяем, меньше ли video-ero остальных видео
    if limiting_factor == 'videos':
        if st.get('video-ero', 0) == 0:
            limiting_factor = 'video-ero'
        elif st.get('video-ero', 0) <= st.get('video-meme', 0) // 2 and st.get('video-ero', 0) <= st.get('video-auto', 0) // 2:
            limiting_factor = 'video-ero'
    
    return {
        'days': min_days,
        'limiting_factor': limiting_factor
    }
