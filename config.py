# config.py
"""
Модуль конфигурации телеграм-бота.
Обеспечивает загрузку настроек из JSON-файлов с оптимизацией через кэширование.
Предоставляет глобальные переменные для удобного доступа к настройкам.
"""

import json
import os
import time
from pathlib import Path
from functools import lru_cache

# Кэш для конфигураций и время их последнего изменения
_config_cache = {}  # Содержимое конфигурационных файлов
_config_mtime = {}  # Время модификации файлов

def load_config(config_file, use_cache=True):
    """
    Загружает конфигурационный файл. Использует кэширование для оптимизации.
    
    Args:
        config_file: Имя файла конфигурации
        use_cache: Использовать ли кэш (по умолчанию True)
    
    Returns:
        dict: Содержимое конфигурационного файла
    """
    config_path = Path('config') / config_file
    
    # Если кэширование отключено, просто загружаем файл
    if not use_cache:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Проверяем, изменился ли файл с момента последней загрузки
    try:
        mtime = config_path.stat().st_mtime
        
        # Если файл в кэше и не изменился, возвращаем закэшированное значение
        if config_file in _config_cache and _config_mtime.get(config_file) == mtime:
            return _config_cache[config_file]
        
        # Иначе загружаем файл заново и обновляем кэш
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            _config_cache[config_file] = config_data
            _config_mtime[config_file] = mtime
            return config_data
    except FileNotFoundError:
        # В случае ошибки возвращаем кэшированное значение, если оно есть
        if config_file in _config_cache:
            return _config_cache[config_file]
        # Иначе пробрасываем ошибку дальше
        raise
    except json.JSONDecodeError:
        # Если JSON невалидный, пробрасываем ошибку дальше
        raise
    except Exception as e:
        # В случае других ошибок возвращаем кэшированное значение, если оно есть
        if config_file in _config_cache:
            return _config_cache[config_file]
        # Иначе пробрасываем ошибку дальше
        raise

def reload_all_configs():
    """
    Принудительно перезагружает все конфигурации.
    Полезно вызывать при изменении конфигурационных файлов вручную.
    Обновляет все глобальные переменные настроек.
    """
    global bot_config, paths_config, sound_config, file_ids, schedule_config
    global TOKEN, ALLOWED_CHAT_IDS, DICE_GIF_ID, COOLDOWN, MANUAL_USERNAMES, POST_CHAT_ID
    global MATERIALS_DIR, ARCHIVE_DIR
    global ERO_ANIME_DIR, ERO_REAL_DIR, SINGLE_MEME_DIR, STANDART_ART_DIR, STANDART_MEME_DIR, VIDEO_MEME_DIR, VIDEO_ERO_DIR, VIDEO_AUTO_DIR
    global ARCHIVE_ERO_ANIME_DIR, ARCHIVE_ERO_REAL_DIR, ARCHIVE_SINGLE_MEME_DIR, ARCHIVE_STANDART_ART_DIR, ARCHIVE_STANDART_MEME_DIR, ARCHIVE_VIDEO_MEME_DIR, ARCHIVE_VIDEO_ERO_DIR, ARCHIVE_VIDEO_AUTO_DIR
    global ANECDOTES_FILE
    global CHAT_ID, ADMIN_GROUP_ID, TIMEZONE_OFFSET, ADMIN_USERNAMES
    
    # Загружаем все конфигурации, игнорируя кэш
    bot_config = load_config('bot_config.json', use_cache=False)
    paths_config = load_config('paths_config.json', use_cache=False)
    sound_config = load_config('sound_config.json', use_cache=False)
    file_ids = load_config('file_ids.json', use_cache=False)
    schedule_config = load_config('schedule_config.json', use_cache=False)
    
    # Переустанавливаем все переменные
    TOKEN = bot_config['token']
    ALLOWED_CHAT_IDS = bot_config['allowed_chat_ids']
    DICE_GIF_ID = file_ids['animations']['dice']
    COOLDOWN = bot_config['cooldown']
    MANUAL_USERNAMES = bot_config['manual_usernames']
    POST_CHAT_ID = bot_config['post_chat_id']
    
    # Настройки для системы ставок
    CHAT_ID = bot_config['allowed_chat_ids'][0]  # Используем первый разрешенный чат как основной
    ADMIN_GROUP_ID = bot_config.get('admin_group_id', CHAT_ID)  # Если не указана отдельная группа администраторов, используем основной чат
    TIMEZONE_OFFSET = bot_config.get('timezone_offset', 0)  # Смещение часового пояса в часах
    # Список юзернеймов администраторов для проверки прав
    ADMIN_USERNAMES = ["TikFuchs", "Veanyk", "TopPelemeshka", "Fallen_Psycho"]  # Список администраторов без @
    
    # Создаем базовые пути с использованием Path
    MATERIALS_DIR = Path(paths_config['materials_dir'])
    ARCHIVE_DIR = Path(paths_config['archive_dir'])
    
    # Контент директории
    ERO_ANIME_DIR = Path(paths_config['content_dirs']['ero_anime'])
    ERO_REAL_DIR = Path(paths_config['content_dirs']['ero_real'])
    SINGLE_MEME_DIR = Path(paths_config['content_dirs']['single_meme'])
    STANDART_ART_DIR = Path(paths_config['content_dirs']['standart_art'])
    STANDART_MEME_DIR = Path(paths_config['content_dirs']['standart_meme'])
    VIDEO_MEME_DIR = Path(paths_config['content_dirs']['video_meme'])
    VIDEO_ERO_DIR = Path(paths_config['content_dirs']['video_ero'])
    VIDEO_AUTO_DIR = Path(paths_config['content_dirs']['video_auto'])
    
    # Архивные директории
    ARCHIVE_ERO_ANIME_DIR = Path(paths_config['archive_dirs']['ero_anime'])
    ARCHIVE_ERO_REAL_DIR = Path(paths_config['archive_dirs']['ero_real'])
    ARCHIVE_SINGLE_MEME_DIR = Path(paths_config['archive_dirs']['single_meme'])
    ARCHIVE_STANDART_ART_DIR = Path(paths_config['archive_dirs']['standart_art'])
    ARCHIVE_STANDART_MEME_DIR = Path(paths_config['archive_dirs']['standart_meme'])
    ARCHIVE_VIDEO_MEME_DIR = Path(paths_config['archive_dirs']['video_meme'])
    ARCHIVE_VIDEO_ERO_DIR = Path(paths_config['archive_dirs']['video_ero'])
    ARCHIVE_VIDEO_AUTO_DIR = Path(paths_config['archive_dirs']['video_auto'])
    
    # Путь к файлу с анекдотами
    ANECDOTES_FILE = Path(paths_config['anecdotes_file'])

# Загружаем все конфигурации при импорте модуля
bot_config = load_config('bot_config.json')       # Основные настройки бота
paths_config = load_config('paths_config.json')   # Пути к файлам и директориям
sound_config = load_config('sound_config.json')   # Настройки звуковой панели
file_ids = load_config('file_ids.json')           # ID файлов в Telegram
schedule_config = load_config('schedule_config.json')  # Настройки расписания

# Экспортируем переменные для удобного доступа из других модулей
# Основные настройки
TOKEN = bot_config['token']                     # Токен бота
ALLOWED_CHAT_IDS = bot_config['allowed_chat_ids']  # Списк разрешенных чатов
DICE_GIF_ID = file_ids['animations']['dice']    # ID анимации кубика
COOLDOWN = bot_config['cooldown']               # Задержка между командами
MANUAL_USERNAMES = bot_config['manual_usernames']  # Пользователи для команды @all
POST_CHAT_ID = bot_config['post_chat_id']       # ID чата для публикаций

# Настройки для системы ставок
CHAT_ID = bot_config['allowed_chat_ids'][0]  # Используем первый разрешенный чат как основной
ADMIN_GROUP_ID = bot_config.get('admin_group_id', CHAT_ID)  # Если не указана отдельная группа администраторов, используем основной чат
TIMEZONE_OFFSET = bot_config.get('timezone_offset', 0)  # Смещение часового пояса в часах
# Список юзернеймов администраторов для проверки прав
ADMIN_USERNAMES = ["TikFuchs", "Veanyk", "TopPelemeshka", "Fallen_Psycho"]  # Список администраторов без @

# Создаем базовые пути с использованием Path
MATERIALS_DIR = Path(paths_config['materials_dir'])  # Директория с материалами
ARCHIVE_DIR = Path(paths_config['archive_dir'])      # Директория с архивами

# Контент директории - откуда брать контент для постов
ERO_ANIME_DIR = Path(paths_config['content_dirs']['ero_anime'])
ERO_REAL_DIR = Path(paths_config['content_dirs']['ero_real'])
SINGLE_MEME_DIR = Path(paths_config['content_dirs']['single_meme'])
STANDART_ART_DIR = Path(paths_config['content_dirs']['standart_art'])
STANDART_MEME_DIR = Path(paths_config['content_dirs']['standart_meme'])
VIDEO_MEME_DIR = Path(paths_config['content_dirs']['video_meme'])
VIDEO_ERO_DIR = Path(paths_config['content_dirs']['video_ero'])
VIDEO_AUTO_DIR = Path(paths_config['content_dirs']['video_auto'])

# Архивные директории - куда перемещать использованный контент
ARCHIVE_ERO_ANIME_DIR = Path(paths_config['archive_dirs']['ero_anime'])
ARCHIVE_ERO_REAL_DIR = Path(paths_config['archive_dirs']['ero_real'])
ARCHIVE_SINGLE_MEME_DIR = Path(paths_config['archive_dirs']['single_meme'])
ARCHIVE_STANDART_ART_DIR = Path(paths_config['archive_dirs']['standart_art'])
ARCHIVE_STANDART_MEME_DIR = Path(paths_config['archive_dirs']['standart_meme'])
ARCHIVE_VIDEO_MEME_DIR = Path(paths_config['archive_dirs']['video_meme'])
ARCHIVE_VIDEO_ERO_DIR = Path(paths_config['archive_dirs']['video_ero'])
ARCHIVE_VIDEO_AUTO_DIR = Path(paths_config['archive_dirs']['video_auto'])

# Путь к файлу с анекдотами
ANECDOTES_FILE = Path(paths_config['anecdotes_file'])

