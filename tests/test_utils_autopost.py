import pytest
import os
import random
import shutil
import time
import json
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
        predict_4videos_posts,
        predict_full_days,
        SEPARATOR, # Импортируем разделитель для тестов анекдотов
    )
    # Импортируем config для доступа к путям, которые используются в моках
    import config 
except ImportError as e:
    pytest.skip(f"Пропуск тестов utils_autopost: не удалось импортировать модуль utils_autopost или его зависимости ({e}).", allow_module_level=True)

# --- Тесты для is_valid_file ---

@patch('utils_autopost.os.path.exists', return_value=True)
@patch('utils_autopost.os.path.getsize')
@patch('utils_autopost.os.access', return_value=True)
@patch('utils_autopost.logger') # Мок логгера
def test_is_valid_file_success(mock_logger, mock_access, mock_getsize, mock_exists):
    """Тест успешной валидации файла."""
    filepath = "/path/to/valid_image.jpg"
    mock_getsize.return_value = 10 * 1024  # 10 KB
    
    assert is_valid_file(filepath) is True
    mock_exists.assert_called_once_with(filepath)
    mock_getsize.assert_any_call(filepath)
    mock_access.assert_called_once_with(filepath, os.R_OK)
    mock_logger.warning.assert_not_called()

@patch('utils_autopost.logger')
def test_is_valid_file_gitkeep(mock_logger):
    """Тест с файлом .gitkeep."""
    filepath = "/path/to/.gitkeep"
    assert is_valid_file(filepath) is False
    mock_logger.warning.assert_called_once()

@patch('utils_autopost.os.path.exists', return_value=False)
@patch('utils_autopost.logger')
def test_is_valid_file_not_exists(mock_logger, mock_exists):
    """Тест с несуществующим файлом."""
    filepath = "/path/to/missing.jpg"
    assert is_valid_file(filepath) is False
    mock_exists.assert_called_once_with(filepath)
    mock_logger.warning.assert_called_once()

@patch('utils_autopost.os.path.exists', return_value=True)
@patch('utils_autopost.os.path.getsize', return_value=0)
@patch('utils_autopost.logger')
def test_is_valid_file_empty(mock_logger, mock_getsize, mock_exists):
    """Тест с пустым файлом."""
    filepath = "/path/to/empty.jpg"
    assert is_valid_file(filepath) is False
    mock_exists.assert_called_once_with(filepath)
    mock_getsize.assert_called_once_with(filepath)
    mock_logger.warning.assert_called_once()

@patch('utils_autopost.os.path.exists', return_value=True)
@patch('utils_autopost.os.path.getsize', return_value=1024)
@patch('utils_autopost.os.access', return_value=False)
@patch('utils_autopost.logger')
def test_is_valid_file_not_readable(mock_logger, mock_access, mock_getsize, mock_exists):
    """Тест с недоступным для чтения файлом."""
    filepath = "/path/to/protected.jpg"
    assert is_valid_file(filepath) is False
    mock_exists.assert_called_once_with(filepath)
    mock_getsize.assert_called_once_with(filepath)
    mock_access.assert_called_once_with(filepath, os.R_OK)
    mock_logger.warning.assert_called_once()

@patch('utils_autopost.os.path.exists', return_value=True)
@patch('utils_autopost.os.path.getsize', return_value=60 * 1024 * 1024) # 60 MB
@patch('utils_autopost.os.access', return_value=True)
@patch('utils_autopost.logger')
def test_is_valid_file_too_large(mock_logger, mock_access, mock_getsize, mock_exists):
    """Тест со слишком большим файлом."""
    filepath = "/path/to/large.mp4"
    assert is_valid_file(filepath) is False
    mock_exists.assert_called_once_with(filepath)
    mock_getsize.assert_called_with(filepath)
    mock_logger.warning.assert_called_once()

@patch('utils_autopost.os.path.exists', return_value=True)
@patch('utils_autopost.os.path.getsize', return_value=1024)
@patch('utils_autopost.os.access', return_value=True)
@patch('utils_autopost.logger')
def test_is_valid_file_invalid_extension(mock_logger, mock_access, mock_getsize, mock_exists):
    """Тест с недопустимым расширением файла."""
    filepath = "/path/to/document.txt"
    assert is_valid_file(filepath) is False
    mock_logger.warning.assert_called_once()

# --- Тесты для get_top_anecdote_and_remove ---

@patch('utils_autopost.os.path.exists')
@patch('utils_autopost.open', new_callable=mock_open)
@patch('utils_autopost.random.randint') # Мок нужен, т.к. используется randint
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
    
    # Патчим путь к файлу анекдотов, чтобы использовать реальный путь из конфигурации
    with patch('utils_autopost.config.ANECDOTES_FILE', Path('post_materials/anecdotes.txt')):
        anecdote = get_top_anecdote_and_remove()
        
        assert anecdote == anec2
        mock_exists.assert_called_once_with(Path('post_materials/anecdotes.txt'))
        # Проверяем чтение
        mock_file.assert_any_call(Path('post_materials/anecdotes.txt'), "r", encoding="utf-8")
        # Проверяем запись оставшихся анекдотов
        expected_remaining = f"{anec1}\n{SEPARATOR}\n{anec3}"
        mock_file.assert_any_call(Path('post_materials/anecdotes.txt'), "w", encoding="utf-8")
        # Получаем хэндл записи и проверяем, что было записано
        write_handle = mock_file() 
        write_handle.write.assert_called_once_with(expected_remaining)
        mock_randint.assert_called_once_with(0, 2) # Был выбор из 3 элементов (индексы 0, 1, 2)
        mock_logger.error.assert_not_called()

@patch('utils_autopost.os.path.exists', return_value=False)
@patch('utils_autopost.logger')
def test_get_top_anecdote_file_not_exists(mock_logger, mock_exists):
    # Патчим путь к файлу анекдотов
    with patch('utils_autopost.config.ANECDOTES_FILE', Path('post_materials/anecdotes.txt')):
        assert get_top_anecdote_and_remove() is None
        mock_exists.assert_called_once_with(Path('post_materials/anecdotes.txt'))
        mock_logger.warning.assert_called_once()

@patch('utils_autopost.os.path.exists', return_value=True)
@patch('utils_autopost.open', new_callable=mock_open, read_data="") # Пустой файл
@patch('utils_autopost.logger')
def test_get_top_anecdote_empty_file(mock_logger, mock_file, mock_exists):
    # Патчим путь к файлу анекдотов
    with patch('utils_autopost.config.ANECDOTES_FILE', Path('post_materials/anecdotes.txt')):
        assert get_top_anecdote_and_remove() is None
        mock_file.assert_called_once_with(Path('post_materials/anecdotes.txt'), "r", encoding="utf-8")
        mock_logger.warning.assert_called_once()

# --- Тесты для count_anecdotes ---

@patch('utils_autopost.os.path.exists')
@patch('utils_autopost.open', new_callable=mock_open)
def test_count_anecdotes_success(mock_file, mock_exists):
    mock_exists.return_value = True
    file_content = f"Anecdote 1\n{SEPARATOR}\nAnecdote 2"
    mock_file.return_value.read.return_value = file_content
    
    # Патчим путь к файлу анекдотов
    with patch('utils_autopost.config.ANECDOTES_FILE', Path('post_materials/anecdotes.txt')):
        assert count_anecdotes() == 2
        mock_file.assert_called_once_with(Path('post_materials/anecdotes.txt'), "r", encoding="utf-8")

@patch('utils_autopost.os.path.exists', return_value=False)
def test_count_anecdotes_no_file(mock_exists):
    assert count_anecdotes() == 0

@patch('utils_autopost.os.path.exists', return_value=True)
@patch('utils_autopost.open', new_callable=mock_open, read_data="")
def test_count_anecdotes_empty_file(mock_file, mock_exists):
    assert count_anecdotes() == 0

# --- Тесты для get_random_file_from_folder ---

@patch('utils_autopost.os.path.exists')
@patch('utils_autopost.os.path.isdir')
@patch('utils_autopost.os.listdir')
@patch('utils_autopost.os.path.isfile')
@patch('utils_autopost.is_valid_file') # Мокаем нашу же функцию проверки
@patch('utils_autopost.random.choice')
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

@patch('utils_autopost.os.path.exists', return_value=False)
@patch('utils_autopost.logger')
def test_get_random_file_folder_not_exists(mock_logger, mock_exists):
    assert get_random_file_from_folder("/no/such/folder") is None
    mock_logger.warning.assert_called_once()

@patch('utils_autopost.os.path.exists', return_value=True)
@patch('utils_autopost.os.path.isdir', return_value=True)
@patch('utils_autopost.os.listdir', return_value=["invalid.txt", ".gitkeep"])
@patch('utils_autopost.os.path.isfile', return_value=True)
@patch('utils_autopost.is_valid_file', return_value=False) # Все файлы невалидны
@patch('utils_autopost.logger')
def test_get_random_file_no_valid_files(mock_logger, mock_is_valid, mock_isfile, mock_listdir, mock_isdir, mock_exists):
    folder = "/path/to/empty_valid"
    assert get_random_file_from_folder(folder) is None
    mock_listdir.assert_called_once_with(folder)
    assert mock_is_valid.call_count == 2
    mock_logger.warning.assert_called_once()

# --- Тесты для move_file_to_archive ---

@patch('utils_autopost.os.path.exists')
@patch('utils_autopost.os.makedirs')
@patch('utils_autopost.shutil.move')
@patch('utils_autopost.time.time', return_value=12345) # Мок времени для конфликта имен
@patch('utils_autopost.logger')
def test_move_file_to_archive_success(mock_logger, mock_time, mock_move, mock_makedirs, mock_exists):
    filepath = "/path/content/meme.jpg"
    category = "standart-meme"
    archive_dir = os.path.join("post_archive", "standart-meme")
    expected_new_path = os.path.join(archive_dir, "meme.jpg")
    
    # Первый exists проверяет исходный файл, второй - файл в архиве (нет конфликта)
    mock_exists.side_effect = [True, False]
    
    # Патчим константы конфигурации
    with patch('utils_autopost.config.ARCHIVE_STANDART_MEME_DIR', Path(archive_dir)):
        result = move_file_to_archive(filepath, category)
        
        assert result is True
        mock_exists.assert_has_calls([call(filepath), call(expected_new_path)])
        mock_makedirs.assert_called_once_with(Path(archive_dir), exist_ok=True)
        mock_move.assert_called_once_with(filepath, expected_new_path)
        mock_logger.info.assert_called_once()
        mock_logger.error.assert_not_called()
        mock_time.assert_not_called() # Время не использовалось

@patch('utils_autopost.os.path.exists')
@patch('utils_autopost.os.makedirs')
@patch('utils_autopost.shutil.move')
@patch('utils_autopost.time.time', return_value=12345)
@patch('utils_autopost.logger')
def test_move_file_to_archive_name_conflict(mock_logger, mock_time, mock_move, mock_makedirs, mock_exists):
    filepath = "/path/content/video.mp4"
    category = "video-meme"
    archive_dir = os.path.join("post_archive", "video-meme")
    original_archive_path = os.path.join(archive_dir, "video.mp4")
    expected_new_path_with_ts = os.path.join(archive_dir, "video_12345.mp4")
    
    # Первый exists проверяет исходный файл, второй - файл в архиве (конфликт)
    mock_exists.side_effect = [True, True]
    
    # Патчим константы конфигурации
    with patch('utils_autopost.config.ARCHIVE_VIDEO_MEME_DIR', Path(archive_dir)):
        result = move_file_to_archive(filepath, category)
        
        assert result is True
        mock_exists.assert_has_calls([call(filepath), call(original_archive_path)])
        mock_makedirs.assert_called_once_with(Path(archive_dir), exist_ok=True)
        mock_time.assert_called_once() # Время использовалось для генерации имени
        mock_move.assert_called_once_with(filepath, expected_new_path_with_ts)
        mock_logger.info.assert_called_once()
        mock_logger.error.assert_not_called()

@patch('utils_autopost.os.path.exists', return_value=False) # Файл не существует
@patch('utils_autopost.logger')
def test_move_file_to_archive_source_not_found(mock_logger, mock_exists):
    filepath = "/gone/file.png"
    category = "ero-anime"
    result = move_file_to_archive(filepath, category)
    assert result is False
    mock_exists.assert_called_once_with(filepath)
    mock_logger.warning.assert_called_once()
    mock_logger.error.assert_not_called()

@patch('utils_autopost.os.path.exists', return_value=True)
@patch('utils_autopost.os.makedirs')
@patch('utils_autopost.shutil.move', side_effect=OSError("Move failed")) # Ошибка при перемещении
@patch('utils_autopost.logger')
def test_move_file_to_archive_move_error(mock_logger, mock_move, mock_makedirs, mock_exists):
    filepath = "/path/content/art.png"
    category = "standart-art"
    archive_dir = os.path.join("post_archive", "standart-art")
    expected_new_path = os.path.join(archive_dir, "art.png")
    mock_exists.side_effect = [True, False]
    
    # Патчим константы конфигурации
    with patch('utils_autopost.config.ARCHIVE_STANDART_ART_DIR', Path(archive_dir)):
        result = move_file_to_archive(filepath, category)
        
        assert result is False
        mock_move.assert_called_once_with(filepath, expected_new_path)
        mock_makedirs.assert_called_once_with(Path(archive_dir), exist_ok=True)
        mock_logger.error.assert_called_once()

@patch('utils_autopost.os.path.exists', return_value=True)
@patch('utils_autopost.logger')
def test_move_file_to_archive_invalid_category(mock_logger, mock_exists):
    """Тест с недопустимой категорией контента."""
    filepath = "/path/content/file.jpg"
    category = "invalid-category"
    result = move_file_to_archive(filepath, category)
    assert result is False
    mock_exists.assert_called_once_with(filepath)
    mock_logger.warning.assert_called_once()

# --- Тесты для get_available_stats ---

@patch('utils_autopost.count_files_in_folder')
@patch('utils_autopost.count_anecdotes')
def test_get_available_stats(mock_count_anecdotes, mock_count_files):
    # Настройка возвращаемых значений для каждой папки и анекдотов
    def count_side_effect(folder):
        if isinstance(folder, Path):
            folder_str = str(folder)
            if 'ero-anime' in folder_str: return 10
            if 'ero-real' in folder_str: return 5
            if 'single-meme' in folder_str: return 20
            if 'standart-art' in folder_str: return 15
            if 'standart-meme' in folder_str: return 30
            if 'video-meme' in folder_str: return 8
            if 'video-ero' in folder_str: return 4
            if 'video-auto' in folder_str: return 12
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
    assert mock_count_files.call_count == 8
    mock_count_anecdotes.assert_called_once()

# --- Тесты для функций предсказания ---

def test_predict_10pics_posts():
    stats = {
        'ero-anime': 50,
        'ero-real': 40,
        'single-meme': 30,
        'standart-art': 60,
        'standart-meme': 70,
        'video-meme': 20,
        'video-ero': 10,
        'video-auto': 15,
        'anecdotes': 100,
    }
    predictions = predict_10pics_posts(stats)
    assert 'ero-anime' in predictions
    assert 'ero-real' in predictions
    assert 'single-meme' in predictions
    assert 'standart-art' in predictions
    assert 'standart-meme' in predictions
    assert predictions['ero-anime'] == 5 # 50 / 10
    assert predictions['standart-meme'] == 7 # 70 / 10
    assert sum(predictions.values()) == 25 # Сумма всех предсказаний для картинок

def test_predict_full_days():
    stats = {
        'ero-anime': 50,
        'ero-real': 40,
        'single-meme': 30,
        'standart-art': 60,
        'standart-meme': 70,
        'video-meme': 20,
        'video-ero': 10,
        'video-auto': 15,
        'anecdotes': 35,
    }
    # Ограничивающим фактором будут видео
    days = predict_full_days(stats)
    assert days['limiting_factor'] == 'videos'
    assert days['days'] == 7  # 10 video-ero видео дают нам 10 постов или 10 дней при 1 посте в день,
                              # но анекдотов 35, что даёт 35/4 = 8 дней (ограничено 7 в логике функции)

def test_predict_full_days_limited_by_pics():
    stats = {
        'ero-anime': 5,
        'ero-real': 40,
        'single-meme': 0,
        'standart-art': 0,
        'standart-meme': 0,
        'video-meme': 20,
        'video-ero': 10,
        'video-auto': 15,
        'anecdotes': 35,
    }
    # Ограничивающий фактор - ero-anime (всего 5 картинок)
    days = predict_full_days(stats)
    assert days['limiting_factor'] == 'ero-anime'
    assert days['days'] == 1  # 5/10 = 0.5 постов, округляется до 1 в функции 