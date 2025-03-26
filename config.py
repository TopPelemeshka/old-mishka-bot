# config.py

import json
import os
from pathlib import Path

def load_config(config_file):
    config_path = Path('config') / config_file
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Загружаем все конфигурации
bot_config = load_config('bot_config.json')
paths_config = load_config('paths_config.json')
sound_config = load_config('sound_config.json')
file_ids = load_config('file_ids.json')

# Экспортируем переменные для обратной совместимости
TOKEN = bot_config['token']
ALLOWED_CHAT_IDS = bot_config['allowed_chat_ids']
DICE_GIF_ID = file_ids['animations']['dice']
COOLDOWN = bot_config['cooldown']
MANUAL_USERNAMES = bot_config['manual_usernames']
POST_CHAT_ID = bot_config['post_chat_id']

# Пути к директориям
MATERIALS_DIR = paths_config['materials_dir']
ARCHIVE_DIR = paths_config['archive_dir']

# Контент директории
ERO_ANIME_DIR = paths_config['content_dirs']['ero_anime']
ERO_REAL_DIR = paths_config['content_dirs']['ero_real']
SINGLE_MEME_DIR = paths_config['content_dirs']['single_meme']
STANDART_ART_DIR = paths_config['content_dirs']['standart_art']
STANDART_MEME_DIR = paths_config['content_dirs']['standart_meme']
VIDEO_MEME_DIR = paths_config['content_dirs']['video_meme']

# Архивные директории
ARCHIVE_ERO_ANIME_DIR = paths_config['archive_dirs']['ero_anime']
ARCHIVE_ERO_REAL_DIR = paths_config['archive_dirs']['ero_real']
ARCHIVE_SINGLE_MEME_DIR = paths_config['archive_dirs']['single_meme']
ARCHIVE_STANDART_ART_DIR = paths_config['archive_dirs']['standart_art']
ARCHIVE_STANDART_MEME_DIR = paths_config['archive_dirs']['standart_meme']
ARCHIVE_VIDEO_MEME_DIR = paths_config['archive_dirs']['video_meme']

# Путь к файлу с анекдотами
ANECDOTES_FILE = paths_config['anecdotes_file']
