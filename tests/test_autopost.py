import pytest
import os
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock, AsyncMock, call, ANY

# Импортируем тестируемый модуль и его функции/переменные
try:
    import autopost
    from autopost import (
        _get_folder_by_category, # Хотя она внутренняя, протестируем её отдельно
        autopost_10_pics_callback,
        autopost_4_videos_callback,
        stop_autopost_command,
        start_autopost_command,
        stats_command,
        next_posts_command
    )
    # Импортируем зависимости для мокирования
    import state
    import config
    import utils_autopost
    import quiz
    import wisdom
    from telegram import InputMediaPhoto, InputMediaVideo
except ImportError as e:
    pytest.skip(f"Пропуск тестов autopost: не удалось импортировать модуль autopost или его зависимости ({e}).", allow_module_level=True)

# --- Тесты для _get_folder_by_category ---

# Мокаем пути в config перед всеми тестами этого файла
@pytest.fixture(autouse=True)
def mock_config_paths():
    with patch('config.ERO_ANIME_DIR', Path("/mock/ero-anime")), \
         patch('config.ERO_REAL_DIR', Path("/mock/ero-real")), \
         patch('config.SINGLE_MEME_DIR', Path("/mock/single-meme")), \
         patch('config.STANDART_ART_DIR', Path("/mock/standart-art")), \
         patch('config.STANDART_MEME_DIR', Path("/mock/standart-meme")), \
         patch('config.VIDEO_MEME_DIR', Path("/mock/video-meme")), \
         patch('config.VIDEO_ERO_DIR', Path("/mock/video-ero")), \
         patch('config.VIDEO_AUTO_DIR', Path("/mock/video-auto")), \
         patch('config.POST_CHAT_ID', -4737984792): # Мок ID чата для постов
        yield

def test_get_folder_by_category_known():
    assert _get_folder_by_category("ero-anime") == Path("/mock/ero-anime")
    assert _get_folder_by_category("standart-meme") == Path("/mock/standart-meme")
    assert _get_folder_by_category("video-auto") == Path("/mock/video-auto")

def test_get_folder_by_category_unknown():
    assert _get_folder_by_category("unknown-category") is None

# --- Тесты для autopost_10_pics_callback ---

@pytest.mark.asyncio
@patch('autopost.state.autopost_enabled', True)
@patch('autopost.get_top_anecdote_and_remove')
@patch('autopost.get_random_file_from_folder')
@patch('autopost.is_valid_file', return_value=True) # По умолчанию файлы валидны
@patch('builtins.open', new_callable=mock_open, read_data=b'test data') # Мок для открытия файлов
@patch('autopost.move_file_to_archive')
async def test_autopost_10_pics_success(mock_move, mock_open_file, mock_is_valid, mock_get_random, mock_get_anecdote):
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_media_group = AsyncMock()
    context.bot.send_message = AsyncMock()
    
    mock_get_anecdote.return_value = "Тестовый анекдот"
    # Настроим get_random_file_from_folder, чтобы он возвращал разные пути
    file_paths = [f"/mock/path/img{i}.jpg" for i in range(10)]
    mock_get_random.side_effect = file_paths
    
    await autopost_10_pics_callback(context)
    
    # Проверки
    mock_get_anecdote.assert_called_once()
    assert mock_get_random.call_count == 10 # Должны были запросить 10 файлов
    assert mock_open_file.call_count == 10 # 10 раз открыть файлы для InputMediaPhoto
    assert mock_is_valid.call_count == 10 # 10 раз проверить валидность
    
    # Проверка отправки медиагруппы
    context.bot.send_media_group.assert_awaited_once()
    args, kwargs = context.bot.send_media_group.call_args
    assert kwargs['chat_id'] == -4737984792
    assert len(kwargs['media']) == 10
    assert all(isinstance(m, InputMediaPhoto) for m in kwargs['media'])
    
    # Проверка отправки анекдота
    context.bot.send_message.assert_awaited_once_with(chat_id=-4737984792, text="Тестовый анекдот", read_timeout=180)
    
    # Проверка перемещения в архив
    assert mock_move.call_count == 10
    # Проверим несколько вызовов move_file_to_archive с правильными категориями
    # Категории берутся из списка `categories` в функции
    mock_move.assert_any_call(file_paths[0], "ero-real")
    mock_move.assert_any_call(file_paths[1], "standart-art") # Первая часть 'standart-art/standart-meme'
    mock_move.assert_any_call(file_paths[2], "ero-anime")
    # ... и так далее для всех 10

@pytest.mark.asyncio
@patch('autopost.state.autopost_enabled', False)
@patch('autopost.get_top_anecdote_and_remove')
async def test_autopost_10_pics_disabled(mock_get_anecdote):
    context = MagicMock()
    context.bot = AsyncMock()
    await autopost_10_pics_callback(context)
    mock_get_anecdote.assert_not_called()
    context.bot.send_media_group.assert_not_awaited()
    context.bot.send_message.assert_not_awaited()

@pytest.mark.asyncio
@patch('autopost.state.autopost_enabled', True)
@patch('autopost.get_top_anecdote_and_remove', return_value=None) # Анекдоты закончились
async def test_autopost_10_pics_no_anecdote(mock_get_anecdote):
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    
    await autopost_10_pics_callback(context)
    
    mock_get_anecdote.assert_called_once()
    context.bot.send_message.assert_awaited_once_with(chat_id=-4737984792, text="Анекдоты закончились 😭")
    context.bot.send_media_group.assert_not_awaited()

@pytest.mark.asyncio
@patch('autopost.state.autopost_enabled', True)
@patch('autopost.get_top_anecdote_and_remove', return_value="Анекдот есть")
@patch('autopost.get_random_file_from_folder', return_value=None) # Файлы закончились
async def test_autopost_10_pics_no_file(mock_get_random, mock_get_anecdote):
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    
    await autopost_10_pics_callback(context)
    
    mock_get_anecdote.assert_called_once()
    mock_get_random.assert_called() # Пытались получить файл
    # Ожидаем сообщение об ошибке для первой же категории 'ero-real'
    context.bot.send_message.assert_awaited_with(
        chat_id=-4737984792,
        text="У нас закончились ero-real 😭"
    )
    context.bot.send_media_group.assert_not_awaited()

@pytest.mark.asyncio
@patch('autopost.state.autopost_enabled', True)
@patch('autopost.get_top_anecdote_and_remove', return_value="Анекдот есть")
@patch('autopost.get_random_file_from_folder')
@patch('autopost.is_valid_file', return_value=False) # Файл невалиден
@patch('autopost.logger')
async def test_autopost_10_pics_invalid_file(mock_logger, mock_is_valid, mock_get_random, mock_get_anecdote):
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    mock_get_random.return_value = "/path/to/invalid.jpg"

    await autopost_10_pics_callback(context)
    
    mock_get_anecdote.assert_called_once()
    mock_get_random.assert_called() # Пытались получить файл
    mock_is_valid.assert_called_with("/path/to/invalid.jpg")
    mock_logger.error.assert_called_once()
    context.bot.send_message.assert_awaited_with(
        chat_id=-4737984792,
        text=f"Файл для категории ero-real не прошел проверку: /path/to/invalid.jpg" # Первая категория
    )
    context.bot.send_media_group.assert_not_awaited()

@pytest.mark.asyncio
@patch('autopost.state.autopost_enabled', True)
@patch('autopost.get_top_anecdote_and_remove', return_value="Анекдот")
@patch('autopost.get_random_file_from_folder')
@patch('autopost.is_valid_file', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data=b'data')
@patch('autopost.logger')
async def test_autopost_10_pics_send_error(mock_logger, mock_open_file, mock_is_valid, mock_get_random, mock_get_anecdote):
    context = MagicMock()
    context.bot = AsyncMock()
    # Имитируем ошибку при отправке
    send_error = Exception("Telegram API error")
    context.bot.send_media_group.side_effect = send_error
    context.bot.send_message = AsyncMock() # Для сообщения об ошибке
    
    file_paths = [f"/mock/path/img{i}.jpg" for i in range(10)]
    mock_get_random.side_effect = file_paths

    await autopost_10_pics_callback(context)

    context.bot.send_media_group.assert_awaited_once() # Была попытка отправки
    # Должно быть залогировано и отправлено сообщение об ошибке
    mock_logger.error.assert_called_once()
    context.bot.send_message.assert_awaited_with(chat_id=-4737984792, text=f"Ошибка при отправке поста: {send_error}")

# --- Тесты для autopost_4_videos_callback ---
# (Аналогично autopost_10_pics_callback, но с InputMediaVideo и логикой фолбека)

@pytest.mark.asyncio
@patch('autopost.state.autopost_enabled', True)
@patch('autopost.get_top_anecdote_and_remove', return_value="Анекдот Видео")
@patch('autopost.get_random_file_from_folder')
@patch('autopost.is_valid_file', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data=b'video data')
@patch('autopost.move_file_to_archive')
async def test_autopost_4_videos_success(mock_move, mock_open_file, mock_is_valid, mock_get_random, mock_get_anecdote):
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_media_group = AsyncMock()
    context.bot.send_message = AsyncMock()

    # Настройка side_effect для get_random_file_from_folder
    # video-meme, video-ero, video-auto, video-auto
    mock_get_random.side_effect = [
        "/path/meme.mp4",   # для video-meme
        "/path/ero.mp4",    # для video-ero
        "/path/auto1.mp4",  # для первого video-auto
        "/path/auto2.mp4"   # для второго video-auto
    ]

    await autopost_4_videos_callback(context)

    mock_get_anecdote.assert_called_once()
    assert mock_get_random.call_count == 4
    # Проверяем вызовы с правильными папками
    mock_get_random.assert_has_calls([
        call(Path("/mock/video-meme")),
        call(Path("/mock/video-ero")),
        call(Path("/mock/video-auto")),
        call(Path("/mock/video-auto"))
    ])
    assert mock_open_file.call_count == 4
    assert mock_is_valid.call_count == 4

    # Проверка отправки медиагруппы
    context.bot.send_media_group.assert_awaited_once()
    args, kwargs = context.bot.send_media_group.call_args
    assert kwargs['chat_id'] == -4737984792
    assert len(kwargs['media']) == 4
    assert all(isinstance(m, InputMediaVideo) for m in kwargs['media'])

    # Проверка отправки анекдота
    context.bot.send_message.assert_awaited_once_with(chat_id=-4737984792, text="Анекдот Видео", read_timeout=180)

    # Проверка перемещения в архив
    assert mock_move.call_count == 4
    mock_move.assert_has_calls([
        call("/path/auto1.mp4", "video-auto"),
        call("/path/meme.mp4", "video-meme"),
        call("/path/ero.mp4", "video-ero"),
        call("/path/auto2.mp4", "video-auto")
    ], any_order=True)

@pytest.mark.asyncio
@patch('autopost.state.autopost_enabled', True)
@patch('autopost.get_top_anecdote_and_remove', return_value="Анекдот Фоллбэк")
@patch('autopost.get_random_file_from_folder')
@patch('autopost.is_valid_file', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data=b'video data')
@patch('autopost.move_file_to_archive')
async def test_autopost_4_videos_fallback_logic(mock_move, mock_open_file, mock_is_valid, mock_get_random, mock_get_anecdote):
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_media_group = AsyncMock()
    context.bot.send_message = AsyncMock()

    # Имитируем: первый auto есть, meme есть, ero нет, второй auto нет, но есть еще meme для замены
    mock_get_random.side_effect = [
        "/path/auto1.mp4",  # Первый вызов для первого video-auto
        "/path/meme1.mp4",  # Второй вызов для video-meme
        None,               # Третий вызов для video-ero (нет)
        "/path/meme2.mp4",  # Четвертый вызов для video-meme (замена ero)
        None,               # Пятый вызов для второго video-auto (нет)
        "/path/meme3.mp4"   # Шестой вызов для video-meme (замена второго auto)
    ]

    await autopost_4_videos_callback(context)

    assert mock_get_random.call_count == 6
    mock_get_random.assert_has_calls([
        call(Path("/mock/video-auto")),  # Ищем первый auto
        call(Path("/mock/video-meme")),  # Ищем meme
        call(Path("/mock/video-ero")),   # Ищем ero - нет
        call(Path("/mock/video-meme")),  # Ищем meme (замена ero)
        call(Path("/mock/video-auto")),  # Ищем второй auto - нет
        call(Path("/mock/video-meme"))   # Ищем meme (замена второго auto)
    ])
    assert mock_open_file.call_count == 4
    assert mock_is_valid.call_count == 4

    context.bot.send_media_group.assert_awaited_once()
    args, kwargs = context.bot.send_media_group.call_args
    assert len(kwargs['media']) == 4

    context.bot.send_message.assert_awaited_once_with(chat_id=-4737984792, text="Анекдот Фоллбэк", read_timeout=180)

    assert mock_move.call_count == 4
    # Проверяем, что файлы для замены категорий архивируются с правильными категориями
    mock_move.assert_has_calls([
        call("/path/auto1.mp4", "video-auto"),
        call("/path/meme1.mp4", "video-meme"),
        call("/path/meme2.mp4", "video-meme"), # ero заменен на meme
        call("/path/meme3.mp4", "video-meme")  # второй auto заменен на meme
    ], any_order=True)

# ... (Нужно добавить тесты на случаи нехватки видео для фолбека, ошибки отправки и т.д.) ...

# --- Тесты для команд --- 

@pytest.mark.asyncio
@patch('autopost.state.save_state')
async def test_start_autopost_command(mock_save_state):
    update = MagicMock()
    update.effective_chat.id = 987
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    # Мокаем другие флаги состояния
    autopost.state.quiz_enabled = True
    autopost.state.wisdom_enabled = True
    autopost.state.autopost_enabled = False # Начальное состояние

    await start_autopost_command(update, context)

    assert autopost.state.autopost_enabled is True
    mock_save_state.assert_called_once_with(True, True, True) # autopost, quiz, wisdom
    context.bot.send_message.assert_awaited_once_with(chat_id=987, text="Автопостинг включён!")

@pytest.mark.asyncio
@patch('autopost.state.save_state')
async def test_stop_autopost_command(mock_save_state):
    update = MagicMock()
    update.effective_chat.id = 987
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    # Мокаем другие флаги состояния
    autopost.state.quiz_enabled = False
    autopost.state.wisdom_enabled = True
    autopost.state.autopost_enabled = True # Начальное состояние

    await stop_autopost_command(update, context)

    assert autopost.state.autopost_enabled is False
    mock_save_state.assert_called_once_with(False, False, True) # autopost, quiz, wisdom
    context.bot.send_message.assert_awaited_once_with(chat_id=987, text="Автопостинг отключён!")

@pytest.mark.asyncio
@patch('autopost.get_available_stats')
@patch('autopost.count_quiz_questions')
@patch('autopost.count_wisdoms')
async def test_stats_command(mock_count_wisdoms, mock_count_quiz, mock_get_stats):
    mock_count_wisdoms.return_value = 3
    mock_count_quiz.return_value = 15
    
    update = MagicMock()
    update.effective_chat.id = 555
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()

    mock_stats_data = {
        'ero-anime': 10, 'ero-real': 5, 'single-meme': 20,
        'standart-art': 15, 'standart-meme': 30, 'video-meme': 8,
        'video-ero': 4, 'video-auto': 12, 'anecdotes': 50,
    }
    mock_get_stats.return_value = mock_stats_data

    await stats_command(update, context)

    mock_get_stats.assert_called_once()
    mock_count_quiz.assert_called_once()
    mock_count_wisdoms.assert_called_once()

    # Проверяем вызов send_message и содержимое сообщения
    context.bot.send_message.assert_awaited_once()
    args, kwargs = context.bot.send_message.call_args
    assert kwargs['chat_id'] == 555
    assert "Текущие остатки материалов:" in kwargs['text']
    assert "anecdotes: 50" in kwargs['text']
    assert "Вопросов для викторины" in kwargs['text']
    assert "Цитат дня" in kwargs['text']

@pytest.mark.asyncio
@patch('autopost.get_available_stats')
@patch('autopost.predict_10pics_posts')
@patch('autopost.predict_4videos_posts')
@patch('autopost.predict_full_days')
async def test_next_posts_command(mock_predict_days, mock_predict_videos, mock_predict_pics, mock_get_stats):
    mock_predict_days.return_value = 9
    mock_predict_videos.return_value = 10
    mock_predict_pics.return_value = 25
    
    update = MagicMock()
    update.effective_chat.id = 666
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    context.job_queue = MagicMock()
    context.job_queue.jobs = MagicMock(return_value=[])
    
    mock_stats_data = {'some': 'stats'} # Конкретные значения не важны, т.к. predict мокаем
    mock_get_stats.return_value = mock_stats_data

    await next_posts_command(update, context)

    # Эта функция не вызывает get_available_stats
    # mock_get_stats.assert_called_once()

    # Проверяем сообщение
    context.bot.send_message.assert_awaited_once()
    args, kwargs = context.bot.send_message.call_args
    assert kwargs['chat_id'] == 666
    assert "Нет запланированных задач" in kwargs['text'] 