# config.py
"""
Модуль конфигурации телеграм-бота.
Обеспечивает загрузку настроек из JSON-файлов с оптимизацией через кэширование.
Предоставляет глобальные переменные для удобного доступа к настройкам.
"""

import json
import os
import time # time не используется в текущей версии, можно убрать, если не планируется для TTL кэша
from pathlib import Path
# from functools import lru_cache # lru_cache не используется, можно убрать

# Кэш для конфигураций и время их последнего изменения
_config_cache = {}  # Содержимое конфигурационных файлов
_config_mtime = {}  # Время модификации файлов

def load_config(config_file_name, use_cache=True):
    """
    Загружает конфигурационный файл из папки 'config'. Использует кэширование.
    
    Args:
        config_file_name: Имя файла конфигурации (например, 'bot_config.json')
        use_cache: Использовать ли кэш (по умолчанию True)
    
    Returns:
        dict: Содержимое конфигурационного файла
    """
    config_path = Path('config') / config_file_name # Убедитесь, что папка 'config' существует в корне проекта этого бота
    
    if not use_cache:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Логирование или обработка ошибки, если файл не найден и кэш отключен
            print(f"ОШИБКА: Файл конфигурации {config_path} не найден (кэш отключен).")
            raise # Пробрасываем ошибку, так как без файла и без кэша работать нельзя
        except json.JSONDecodeError as e:
            print(f"ОШИБКА: Некорректный JSON в файле {config_path}: {e}")
            raise
        except Exception as e:
            print(f"ОШИБКА: Не удалось загрузить конфигурацию из {config_path}: {e}")
            raise

    try:
        mtime = config_path.stat().st_mtime
        
        if config_file_name in _config_cache and _config_mtime.get(config_file_name) == mtime:
            return _config_cache[config_file_name]
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            _config_cache[config_file_name] = config_data
            _config_mtime[config_file_name] = mtime
            return config_data
    except FileNotFoundError:
        print(f"ПРЕДУПРЕЖДЕНИЕ: Файл конфигурации {config_path} не найден.")
        if config_file_name in _config_cache:
            print(f"Используется закэшированное значение для {config_file_name}.")
            return _config_cache[config_file_name]
        print(f"ОШИБКА: Кэш для {config_file_name} пуст, файл не найден. Невозможно загрузить конфигурацию.")
        raise # Критическая ошибка, если файла нет и кэша тоже
    except json.JSONDecodeError as e:
        print(f"ОШИБКА: Некорректный JSON в файле {config_path}: {e}")
        if config_file_name in _config_cache: # Возвращаем кэш, если JSON битый
            print(f"Используется закэшированное значение для {config_file_name} из-за ошибки парсинга JSON.")
            return _config_cache[config_file_name]
        raise # Если и кэша нет, то ошибка
    except Exception as e:
        print(f"ОШИБКА: Не удалось загрузить конфигурацию из {config_path}: {e}")
        if config_file_name in _config_cache:
            print(f"Используется закэшированное значение для {config_file_name} из-за общей ошибки.")
            return _config_cache[config_file_name]
        raise

# --- Глобальные переменные для хранения загруженных конфигураций ---
# Они будут инициализированы функцией reload_all_configs()
bot_config = {}
paths_config = {}
sound_config = {}
file_ids = {}
schedule_config = {}

TOKEN = None
ALLOWED_CHAT_IDS = []
DICE_GIF_ID = None
COOLDOWN = 3
MANUAL_USERNAMES = []
POST_CHAT_ID = None
CHAT_ID = None # Основной чат для некоторых операций
ADMIN_GROUP_ID = None
TIMEZONE_OFFSET = 0

MEMOTEKA_API_URL = None # Для API Мемотеки
MEMOTEKA_WEB_APP_URL = None # Для полных URL картинок из Мемотеки

MATERIALS_DIR = Path('.')
ARCHIVE_DIR = Path('.')
ERO_ANIME_DIR = Path('.')
ERO_REAL_DIR = Path('.')
SINGLE_MEME_DIR = Path('.')
STANDART_ART_DIR = Path('.')
STANDART_MEME_DIR = Path('.')
VIDEO_MEME_DIR = Path('.')
VIDEO_ERO_DIR = Path('.')
VIDEO_AUTO_DIR = Path('.')
ARCHIVE_ERO_ANIME_DIR = Path('.')
ARCHIVE_ERO_REAL_DIR = Path('.')
ARCHIVE_SINGLE_MEME_DIR = Path('.')
ARCHIVE_STANDART_ART_DIR = Path('.')
ARCHIVE_STANDART_MEME_DIR = Path('.')
ARCHIVE_VIDEO_MEME_DIR = Path('.')
ARCHIVE_VIDEO_ERO_DIR = Path('.')
ARCHIVE_VIDEO_AUTO_DIR = Path('.')
ANECDOTES_FILE = Path('.')
# --- Конец глобальных переменных ---


def reload_all_configs(use_cache_override=None):
    """
    Принудительно перезагружает все конфигурации и обновляет глобальные переменные.
    Args:
        use_cache_override: Если установлено (True/False), переопределяет use_cache для всех load_config.
                           Если None, используется значение по умолчанию True для load_config.
    """
    global bot_config, paths_config, sound_config, file_ids, schedule_config
    global TOKEN, ALLOWED_CHAT_IDS, DICE_GIF_ID, COOLDOWN, MANUAL_USERNAMES, POST_CHAT_ID
    global MATERIALS_DIR, ARCHIVE_DIR
    global ERO_ANIME_DIR, ERO_REAL_DIR, SINGLE_MEME_DIR, STANDART_ART_DIR, STANDART_MEME_DIR
    global VIDEO_MEME_DIR, VIDEO_ERO_DIR, VIDEO_AUTO_DIR
    global ARCHIVE_ERO_ANIME_DIR, ARCHIVE_ERO_REAL_DIR, ARCHIVE_SINGLE_MEME_DIR
    global ARCHIVE_STANDART_ART_DIR, ARCHIVE_STANDART_MEME_DIR, ARCHIVE_VIDEO_MEME_DIR
    global ARCHIVE_VIDEO_ERO_DIR, ARCHIVE_VIDEO_AUTO_DIR
    global ANECDOTES_FILE
    global CHAT_ID, ADMIN_GROUP_ID, TIMEZONE_OFFSET
    global MEMOTEKA_API_URL, MEMOTEKA_WEB_APP_URL

    # Определяем, использовать ли кэш для этой конкретной перезагрузки
    # По умолчанию при вызове reload_all_configs() кэш НЕ используется для свежих данных.
    # Если use_cache_override не None, используем его. Иначе use_cache=False.
    # Для первоначальной загрузки при импорте модуля, мы вызовем reload_all_configs(use_cache_override=True)
    # чтобы он использовал кэш по умолчанию (т.е. load_config с use_cache=True)
    # Это немного запутанно, давайте сделаем проще:
    # reload_all_configs всегда будет пытаться загрузить свежее, если это возможно (т.е. файл изменился).
    # load_config сама решает, использовать кэш или нет, на основе use_cache и mtime.
    # Поэтому use_cache_override здесь не сильно нужен, если только не для полного сброса кэша.
    # Мы можем просто передавать False в load_config, если хотим гарантированно свежие данные.

    # Если функция вызвана для ПРИНУДИТЕЛЬНОЙ перезагрузки (например, по команде),
    # то use_cache_for_reload = False.
    # Если это первоначальная загрузка, то use_cache_for_reload = True (чтобы load_config работала как обычно).
    
    # Аргумент use_cache_override не использовался, сделаем проще:
    # reload_all_configs будет загружать с учетом кэша (поведение по умолчанию load_config)
    # Если нужна полная перезагрузка без кэша, нужно будет передать use_cache=False в каждый load_config.
    # Для команды /reload_config можно так и сделать.
    # А при старте бота - с use_cache=True.

    # Давайте определим параметр для самой reload_all_configs
    # use_cache_for_this_reload = True # По умолчанию, при импорте
    # if use_cache_override is not None:
    #     use_cache_for_this_reload = use_cache_override

    # Для команды /reload_config, которая есть у вас, нужно use_cache=False.
    # Для первоначального импорта - use_cache=True.
    # Поэтому load_config() сама должна решать.
    # Аргумент use_cache_override в reload_all_configs не нужен.
    # Функция reload_all_configs просто последовательно вызывает load_config.
    # А сама load_config решает, читать из файла или из кэша.
    # Для команды /reload_config, сама команда должна вызывать load_config с False.
    # Мы вызываем reload_all_configs() ниже без аргументов, значит load_config будет использовать use_cache=True.

    print("Перезагрузка конфигураций...")
    try:
        bot_config = load_config('bot_config.json') # use_cache=True по умолчанию
        paths_config = load_config('paths_config.json')
        sound_config = load_config('sound_config.json')
        file_ids = load_config('file_ids.json')
        schedule_config = load_config('schedule_config.json')
    except Exception as e:
        print(f"Критическая ошибка при загрузке одного из конфигурационных файлов: {e}. Бот может работать некорректно.")
        # В этом случае глобальные переменные могут остаться старыми или неинициализированными.
        # Это нужно обрабатывать в вызывающем коде или здесь завершать работу.
        # Пока что просто выведем ошибку.

    # Установка глобальных переменных из загруженных конфигов
    # Используем .get() с значениями по умолчанию, чтобы избежать KeyError, если поле отсутствует
    TOKEN = bot_config.get('token')
    ALLOWED_CHAT_IDS = bot_config.get('allowed_chat_ids', [])
    COOLDOWN = bot_config.get('cooldown', 3)
    MANUAL_USERNAMES = bot_config.get('manual_usernames', [])
    POST_CHAT_ID = bot_config.get('post_chat_id')
    
    if ALLOWED_CHAT_IDS: # Устанавливаем CHAT_ID только если список не пуст
        CHAT_ID = ALLOWED_CHAT_IDS[0]
    else:
        CHAT_ID = None # Или какое-то значение по умолчанию / ошибка
        print("ПРЕДУПРЕЖДЕНИЕ: 'allowed_chat_ids' не задан или пуст в bot_config.json. CHAT_ID не установлен.")

    ADMIN_GROUP_ID = bot_config.get('admin_group_id', CHAT_ID) 
    TIMEZONE_OFFSET = bot_config.get('timezone_offset', 0)

    # Настройки для Мемотеки
    MEMOTEKA_API_URL = bot_config.get('memoteka_api_url')
    MEMOTEKA_WEB_APP_URL = bot_config.get('memoteka_web_app_url')

    if not MEMOTEKA_API_URL:
        print("ПРЕДУПРЕЖДЕНИЕ: 'memoteka_api_url' не найден в bot_config.json. Команда /meme не будет работать.")
    if not MEMOTEKA_WEB_APP_URL:
        print("ПРЕДУПРЕЖДЕНИЕ: 'memoteka_web_app_url' не найден в bot_config.json. Формирование полных URL для картинок мемов может быть неполным.")


    # File IDs
    DICE_GIF_ID = file_ids.get('animations', {}).get('dice')
    if not DICE_GIF_ID:
        print("ПРЕДУПРЕЖДЕНИЕ: file_ids['animations']['dice'] не найден в file_ids.json.")


    # Paths config
    MATERIALS_DIR = Path(paths_config.get('materials_dir', 'materials_default')) # Пример значения по умолчанию
    ARCHIVE_DIR = Path(paths_config.get('archive_dir', 'archive_default'))
    ANECDOTES_FILE = Path(paths_config.get('anecdotes_file', 'anecdotes_default.txt'))

    content_dirs = paths_config.get('content_dirs', {})
    ERO_ANIME_DIR = Path(content_dirs.get('ero_anime', MATERIALS_DIR / 'ero_anime')) # Пути по умолчанию относительно MATERIALS_DIR
    ERO_REAL_DIR = Path(content_dirs.get('ero_real', MATERIALS_DIR / 'ero_real'))
    SINGLE_MEME_DIR = Path(content_dirs.get('single_meme', MATERIALS_DIR / 'single_meme'))
    STANDART_ART_DIR = Path(content_dirs.get('standart_art', MATERIALS_DIR / 'standart_art'))
    STANDART_MEME_DIR = Path(content_dirs.get('standart_meme', MATERIALS_DIR / 'standart_meme'))
    VIDEO_MEME_DIR = Path(content_dirs.get('video_meme', MATERIALS_DIR / 'video_meme'))
    VIDEO_ERO_DIR = Path(content_dirs.get('video_ero', MATERIALS_DIR / 'video_ero'))
    VIDEO_AUTO_DIR = Path(content_dirs.get('video_auto', MATERIALS_DIR / 'video_auto'))

    archive_dirs_conf = paths_config.get('archive_dirs', {})
    ARCHIVE_ERO_ANIME_DIR = Path(archive_dirs_conf.get('ero_anime', ARCHIVE_DIR / 'ero_anime'))
    ARCHIVE_ERO_REAL_DIR = Path(archive_dirs_conf.get('ero_real', ARCHIVE_DIR / 'ero_real'))
    ARCHIVE_SINGLE_MEME_DIR = Path(archive_dirs_conf.get('single_meme', ARCHIVE_DIR / 'single_meme'))
    ARCHIVE_STANDART_ART_DIR = Path(archive_dirs_conf.get('standart_art', ARCHIVE_DIR / 'standart_art'))
    ARCHIVE_STANDART_MEME_DIR = Path(archive_dirs_conf.get('standart_meme', ARCHIVE_DIR / 'standart_meme'))
    ARCHIVE_VIDEO_MEME_DIR = Path(archive_dirs_conf.get('video_meme', ARCHIVE_DIR / 'video_meme'))
    ARCHIVE_VIDEO_ERO_DIR = Path(archive_dirs_conf.get('video_ero', ARCHIVE_DIR / 'video_ero'))
    ARCHIVE_VIDEO_AUTO_DIR = Path(archive_dirs_conf.get('video_auto', ARCHIVE_DIR / 'video_auto'))
    
    # Важно: Создать директории, если они не существуют, чтобы избежать ошибок при работе с файлами
    # Это лучше делать при старте бота или в reload_all_configs один раз
    _ensure_configured_dirs_exist()
    
    print("Конфигурации успешно (пере)загружены и глобальные переменные обновлены.")

def _ensure_configured_dirs_exist():
    """Создает директории, указанные в конфигурации, если они не существуют."""
    dirs_to_check_or_create = [
        MATERIALS_DIR, ARCHIVE_DIR,
        ERO_ANIME_DIR, ERO_REAL_DIR, SINGLE_MEME_DIR, STANDART_ART_DIR, STANDART_MEME_DIR,
        VIDEO_MEME_DIR, VIDEO_ERO_DIR, VIDEO_AUTO_DIR,
        ARCHIVE_ERO_ANIME_DIR, ARCHIVE_ERO_REAL_DIR, ARCHIVE_SINGLE_MEME_DIR,
        ARCHIVE_STANDART_ART_DIR, ARCHIVE_STANDART_MEME_DIR, ARCHIVE_VIDEO_MEME_DIR,
        ARCHIVE_VIDEO_ERO_DIR, ARCHIVE_VIDEO_AUTO_DIR,
        Path(ANECDOTES_FILE).parent # Директория для файла анекдотов
    ]
    for dir_path in dirs_to_check_or_create:
        if isinstance(dir_path, Path): # Убедимся, что это объект Path
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"Не удалось создать директорию {dir_path}: {e}")


# Первоначальная загрузка всех конфигураций при импорте модуля
# и установка глобальных переменных.
# Вызов reload_all_configs() здесь установит все глобальные переменные.
reload_all_configs()