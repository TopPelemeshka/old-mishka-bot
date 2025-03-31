import pytest
import os
import random
import shutil
import time
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock, call

# Импортируем тестируемый модуль и его функции/переменные
try:
    import utils_autopost
    from utils_autopost import (
        is_valid_file,
        get_top_anecdote_and_remove,
        count_anecdotes,
        get_random_file_from_folder,
        move_file_to_archive,
        count_files_in_folder,
        get_available_stats,
        predict_10pics_posts,
        predict_3videos_posts,
        predict_full_days,
        SEPARATOR, # Импортируем разделитель для тестов анекдотов
    )
    # Импортируем config для доступа к путям, которые используются в моках
    import config 
except ImportError as e:
    pytest.skip(f"Пропуск тестов utils_autopost: не удалось импортировать модуль utils_autopost или его зависимости ({e}).", allow_module_level=True)

# --- Тесты для is_valid_file ---

@patch('os.path.exists', return_value=True)
@patch('os.path.getsize')
@patch('os.access', return_value=True)
@patch('utils_autopost.logger') # Мок логгера
def test_is_valid_file_success(mock_logger, mock_access, mock_getsize, mock_exists):
    """Тест валидного файла."""
    mock_getsize.return_value = 1024 # Не пустой и меньше лимита
    filepath = "/path/to/image.jpg"
    assert is_valid_file(filepath) is True
    mock_exists.assert_called_once_with(filepath)
    mock_getsize.assert_called()
    mock_access.assert_called_once_with(filepath, os.R_OK)
    mock_logger.warning.assert_not_called()

@patch('utils_autopost.logger')
def test_is_valid_file_gitkeep(mock_logger):
    """Тест файла .gitkeep."""
    filepath = "/path/to/.gitkeep"
    assert is_valid_file(filepath) is False
    mock_logger.warning.assert_called_once()

@patch('os.path.exists', return_value=False)
@patch('utils_autopost.logger')
def test_is_valid_file_not_exists(mock_logger, mock_exists):
    """Тест несуществующего файла."""
    filepath = "/path/to/nonexistent.png"
    assert is_valid_file(filepath) is False
    mock_exists.assert_called_once_with(filepath)
    mock_logger.warning.assert_called_once()

@patch('os.path.exists', return_value=True)
@patch('os.path.getsize', return_value=0)
@patch('utils_autopost.logger')
def test_is_valid_file_empty(mock_logger, mock_getsize, mock_exists):
    """Тест пустого файла."""
    filepath = "/path/to/empty.gif"
    assert is_valid_file(filepath) is False
    mock_exists.assert_called_once_with(filepath)
    mock_getsize.assert_called_once_with(filepath)
    mock_logger.warning.assert_called_once()

@patch('os.path.exists', return_value=True)
@patch('os.path.getsize', return_value=1024)
@patch('os.access', return_value=False)
@patch('utils_autopost.logger')
def test_is_valid_file_not_readable(mock_logger, mock_access, mock_getsize, mock_exists):
    """Тест недоступного для чтения файла."""
    filepath = "/path/to/forbidden.mp4"
    assert is_valid_file(filepath) is False
    mock_access.assert_called_once_with(filepath, os.R_OK)
    mock_logger.warning.assert_called_once()

@patch('os.path.exists', return_value=True)
@patch('os.path.getsize', return_value=60 * 1024 * 1024) # 60 MB
@patch('os.access', return_value=True)
@patch('utils_autopost.logger')
def test_is_valid_file_too_large(mock_logger, mock_access, mock_getsize, mock_exists):
    """Тест файла, превышающего лимит размера."""
    filepath = "/path/to/large.webm"
    assert is_valid_file(filepath) is False
    mock_getsize.assert_any_call(filepath)
    mock_logger.warning.assert_called_once()

@patch('os.path.exists', return_value=True)
@patch('os.path.getsize', return_value=1024)
@patch('os.access', return_value=True)
@patch('utils_autopost.logger')
def test_is_valid_file_invalid_extension(mock_logger, mock_access, mock_getsize, mock_exists):
    """Тест файла с недопустимым расширением."""
    filepath = "/path/to/document.txt"
    assert is_valid_file(filepath) is False
    mock_logger.warning.assert_called_once()

# --- Тесты для get_top_anecdote_and_remove ---

@patch('os.path.exists')
@patch('builtins.open', new_callable=mock_open)
@patch('random.randint') # Мок нужен, т.к. используется randint
@patch('utils_autopost.logger')
def test_get_top_anecdote_success(mock_logger, mock_randint, mock_file, mock_exists):
    """Тест успешного получения и удаления анекдота."""
    anec1 = "Анекдот 1"
    anec2 = "Анекдот 2"
    anec3 = "Анекдот 3"
    file_content = f"{anec1}\n{SEPARATOR}\n{anec2}\n{SEPARATOR}\n{anec3}"
    mock_exists.return_value = True
    # Настраиваем mock_open для чтения и записи
    mock_file.return_value.read.return_value = file_content
    mock_randint.return_value = 1 # Выбираем второй анекдот (индекс 1)
    
    anecdote = get_top_anecdote_and_remove()
    
    assert anecdote == anec2
    mock_exists.assert_called_once_with(config.ANECDOTES_FILE)
    # Проверяем чтение
    mock_file.assert_any_call(config.ANECDOTES_FILE, "r", encoding="utf-8")
    # Проверяем запись оставшихся анекдотов
    expected_remaining = f"{anec1}\n{SEPARATOR}\n{anec3}"
    mock_file.assert_any_call(config.ANECDOTES_FILE, "w", encoding="utf-8")
    # Получаем хэндл записи и проверяем, что было записано
    write_handle = mock_file() 
    write_handle.write.assert_called_once_with(expected_remaining)
    mock_randint.assert_called_once_with(0, 2) # Был выбор из 3 элементов (индексы 0, 1, 2)
    mock_logger.error.assert_not_called()

@patch('os.path.exists', return_value=False)
@patch('utils_autopost.logger')
def test_get_top_anecdote_file_not_exists(mock_logger, mock_exists):
    assert get_top_anecdote_and_remove() is None
    mock_exists.assert_called_once_with(config.ANECDOTES_FILE)
    mock_logger.warning.assert_called_once()

@patch('os.path.exists', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data="") # Пустой файл
@patch('utils_autopost.logger')
def test_get_top_anecdote_empty_file(mock_logger, mock_file, mock_exists):
    assert get_top_anecdote_and_remove() is None
    mock_file.assert_called_once_with(config.ANECDOTES_FILE, "r", encoding="utf-8")
    mock_logger.warning.assert_called_once()

# --- Тесты для count_anecdotes ---

@patch('os.path.exists')
@patch('builtins.open', new_callable=mock_open)
def test_count_anecdotes_success(mock_file, mock_exists):
    mock_exists.return_value = True
    file_content = f"Anecdote 1\n{SEPARATOR}\nAnecdote 2"
    mock_file.return_value.read.return_value = file_content
    assert count_anecdotes() == 2
    mock_file.assert_called_once_with(config.ANECDOTES_FILE, "r", encoding="utf-8")

@patch('os.path.exists', return_value=False)
def test_count_anecdotes_no_file(mock_exists):
    assert count_anecdotes() == 0

@patch('os.path.exists', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data="")
def test_count_anecdotes_empty_file(mock_file, mock_exists):
    assert count_anecdotes() == 0

# --- Тесты для get_random_file_from_folder ---

@patch('os.path.exists')
@patch('os.path.isdir')
@patch('os.listdir')
@patch('os.path.isfile')
@patch('utils_autopost.is_valid_file') # Мокаем нашу же функцию проверки
@patch('random.choice')
def test_get_random_file_success(mock_choice, mock_is_valid, mock_isfile, mock_listdir, mock_isdir, mock_exists):
    folder = "/path/to/content"
    mock_exists.return_value = True
    mock_isdir.return_value = True
    files_in_dir = ["valid1.jpg", "invalid.txt", "valid2.png", ".gitkeep"]
    mock_listdir.return_value = files_in_dir
    
    # Настройка моков isfile и is_valid_file
    def isfile_side_effect(p): return p != os.path.join(folder, "subdir")
    def is_valid_side_effect(p):
        return p.endswith(("valid1.jpg", "valid2.png"))
    mock_isfile.side_effect = isfile_side_effect
    mock_is_valid.side_effect = is_valid_side_effect
    
    # Настройка random.choice
    expected_valid_paths = [os.path.join(folder, "valid1.jpg"), os.path.join(folder, "valid2.png")]
    mock_choice.return_value = expected_valid_paths[1] # Выбираем второй валидный
    
    result = get_random_file_from_folder(folder)
    
    assert result == expected_valid_paths[1]
    mock_exists.assert_called_once_with(folder)
    mock_isdir.assert_called_once_with(folder)
    mock_listdir.assert_called_once_with(folder)
    # Проверяем вызовы is_valid_file для файлов
    assert mock_is_valid.call_count == 4 # Вызван для всех файлов
    mock_is_valid.assert_any_call(os.path.join(folder, "valid1.jpg"))
    mock_is_valid.assert_any_call(os.path.join(folder, "invalid.txt"))
    mock_choice.assert_called_once_with(expected_valid_paths)

@patch('os.path.exists', return_value=False)
@patch('utils_autopost.logger')
def test_get_random_file_folder_not_exists(mock_logger, mock_exists):
    assert get_random_file_from_folder("/no/such/folder") is None
    mock_logger.warning.assert_called_once()

@patch('os.path.exists', return_value=True)
@patch('os.path.isdir', return_value=True)
@patch('os.listdir', return_value=["invalid.txt", ".gitkeep"])
@patch('os.path.isfile', return_value=True)
@patch('utils_autopost.is_valid_file', return_value=False) # Все файлы невалидны
@patch('utils_autopost.logger')
def test_get_random_file_no_valid_files(mock_logger, mock_is_valid, mock_isfile, mock_listdir, mock_isdir, mock_exists):
    folder = "/path/to/empty_valid"
    assert get_random_file_from_folder(folder) is None
    mock_listdir.assert_called_once_with(folder)
    assert mock_is_valid.call_count == 2
    mock_logger.warning.assert_called_once()

# --- Тесты для move_file_to_archive ---

@patch('os.path.exists')
@patch('os.makedirs')
@patch('shutil.move')
@patch('time.time', return_value=12345) # Мок времени для конфликта имен
@patch('utils_autopost.logger')
def test_move_file_to_archive_success(mock_logger, mock_time, mock_move, mock_makedirs, mock_exists):
    filepath = "/path/content/meme.jpg"
    category = "standart-meme"
    expected_archive_dir = config.ARCHIVE_STANDART_MEME_DIR
    expected_new_path = os.path.join(expected_archive_dir, "meme.jpg")
    
    # Первый exists проверяет исходный файл, второй - файл в архиве (нет конфликта)
    mock_exists.side_effect = [True, False]
    
    result = move_file_to_archive(filepath, category)
    
    assert result is True
    mock_exists.assert_has_calls([call(filepath), call(expected_new_path)])
    mock_makedirs.assert_called_once_with(expected_archive_dir, exist_ok=True)
    mock_move.assert_called_once_with(filepath, expected_new_path)
    mock_logger.info.assert_called_once()
    mock_logger.error.assert_not_called()
    mock_time.assert_not_called() # Время не использовалось

@patch('os.path.exists')
@patch('os.makedirs')
@patch('shutil.move')
@patch('time.time', return_value=12345)
@patch('utils_autopost.logger')
def test_move_file_to_archive_name_conflict(mock_logger, mock_time, mock_move, mock_makedirs, mock_exists):
    filepath = "/path/content/video.mp4"
    category = "video-meme"
    expected_archive_dir = config.ARCHIVE_VIDEO_MEME_DIR
    original_archive_path = os.path.join(expected_archive_dir, "video.mp4")
    expected_new_path_with_ts = os.path.join(expected_archive_dir, "video_12345.mp4")
    
    # Первый exists проверяет исходный файл, второй - файл в архиве (конфликт)
    mock_exists.side_effect = [True, True]
    
    result = move_file_to_archive(filepath, category)
    
    assert result is True
    mock_exists.assert_has_calls([call(filepath), call(original_archive_path)])
    mock_makedirs.assert_called_once_with(expected_archive_dir, exist_ok=True)
    mock_time.assert_called_once() # Время использовалось для генерации имени
    mock_move.assert_called_once_with(filepath, expected_new_path_with_ts)
    mock_logger.info.assert_called_once()
    mock_logger.error.assert_not_called()

@patch('os.path.exists', return_value=False) # Файл не существует
@patch('utils_autopost.logger')
def test_move_file_to_archive_source_not_found(mock_logger, mock_exists):
    filepath = "/gone/file.png"
    category = "ero-anime"
    result = move_file_to_archive(filepath, category)
    assert result is False
    mock_exists.assert_called_once_with(filepath)
    mock_logger.warning.assert_called_once()
    mock_logger.error.assert_not_called()

@patch('os.path.exists', return_value=True)
@patch('os.makedirs')
@patch('shutil.move', side_effect=OSError("Move failed")) # Ошибка при перемещении
@patch('utils_autopost.logger')
def test_move_file_to_archive_move_error(mock_logger, mock_move, mock_makedirs, mock_exists):
    filepath = "/path/content/art.png"
    category = "standart-art"
    expected_archive_dir = config.ARCHIVE_STANDART_ART_DIR
    expected_new_path = os.path.join(expected_archive_dir, "art.png")
    mock_exists.side_effect = [True, False]

    result = move_file_to_archive(filepath, category)
    
    assert result is False
    mock_move.assert_called_once_with(filepath, expected_new_path)
    mock_logger.error.assert_called_once()

# --- Тесты для count_files_in_folder ---
# ... (Аналогично get_random_file_from_folder, но без random и is_valid_file)

# --- Тесты для get_available_stats ---

@patch('utils_autopost.count_files_in_folder')
@patch('utils_autopost.count_anecdotes')
def test_get_available_stats(mock_count_anecdotes, mock_count_files):
    # Настройка возвращаемых значений для каждой папки и анекдотов
    def count_side_effect(folder):
        if folder == config.ERO_ANIME_DIR: return 10
        if folder == config.ERO_REAL_DIR: return 5
        if folder == config.SINGLE_MEME_DIR: return 20
        if folder == config.STANDART_ART_DIR: return 15
        if folder == config.STANDART_MEME_DIR: return 30
        if folder == config.VIDEO_MEME_DIR: return 8
        if folder == config.VIDEO_ERO_DIR: return 4
        if folder == config.VIDEO_AUTO_DIR: return 12
        return 0
    mock_count_files.side_effect = count_side_effect
    mock_count_anecdotes.return_value = 50
    
    stats = get_available_stats()
    
    expected_stats = {
        'ero-anime': 10,
        'ero-real': 5,
        'single-meme': 20,
        'standart-art': 15,
        'standart-meme': 30,
        'video-meme': 8,
        'video-ero': 4,
        'video-auto': 12,
        'anecdotes': 50,
    }
    assert stats == expected_stats
    assert mock_count_files.call_count == 8 # Проверяем вызовы для всех 8 папок
    mock_count_anecdotes.assert_called_once()

# --- Тесты для функций предсказания ---

def test_predict_10pics_posts():
    stats = {
        'ero-anime': 12, 'ero-real': 8, 'single-meme': 5,
        'standart-art': 25, 'standart-meme': 31,
        'anecdotes': 100  # Добавляем анекдоты
        # Другие не важны для этого теста
    }
    # Ожидаем: ero = min(12, 8) = 8; art = 25; meme = 31+5 = 36
    # 10pics = ero*1 + art*3 + meme*6 = 8*1 + 25*3 + 36*6 = 8 + 75 + 216 = 299
    # Всего постов = floor(299 / 10) = 29
    assert predict_10pics_posts(stats) == 29

def test_predict_3videos_posts():
    stats = {
        'video-meme': 10, 'video-ero': 5, 'video-auto': 20,
        'anecdotes': 100  # Добавляем анекдоты
        # Другие не важны
    }
    # Ожидаем: meme = 10; ero = 5; auto = 20
    # 3videos = meme*1 + ero*1 + auto*1 = 10 + 5 + 20 = 35
    # Всего постов = floor(35 / 3) = 11
    assert predict_3videos_posts(stats) == 11

def test_predict_full_days():
    stats = {
        'ero-anime': 12, 'ero-real': 8, 'single-meme': 5,
        'standart-art': 25, 'standart-meme': 31,
        'video-meme': 10, 'video-ero': 5, 'video-auto': 20,
        'anecdotes': 50,
    }
    # Из предыдущих тестов: pics_posts = 29, video_posts = 11
    # Анекдотов 50
    # Постов в день: 2 картинки + 1 видео + 1 анекдот = 4
    # Ограничивающие факторы:
    # Картинки: 29 постов / 2 поста в день = 14.5 дней
    # Видео: 11 постов / 1 пост в день = 11 дней
    # Анекдоты: 50 постов / 1 пост в день = 50 дней
    # Минимальное = 11 дней
    assert predict_full_days(stats) == 11

def test_predict_full_days_limited_by_pics():
     stats = {
        'ero-anime': 1, 'ero-real': 1, 'single-meme': 1,
        'standart-art': 1, 'standart-meme': 1, # Мало картинок
        'video-meme': 100, 'video-ero': 100, 'video-auto': 100,
        'anecdotes': 100,
    }
     # pics_posts = floor((1*1 + 1*3 + (1+1)*6)/10) = floor(16/10)=1
     # video_posts = floor((100+100+100)/3) = 100
     # anecdotes = 100
     # Лимит по картинкам: 1 пост / 2 в день = 0.5 дня
     # Лимит по видео: 100 / 1 = 100 дней
     # Лимит по анекдотам: 100 / 1 = 100 дней
     # Минимум = 0 дней
     assert predict_full_days(stats) == 0 