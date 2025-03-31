import pytest
from unittest.mock import patch, mock_open, MagicMock, AsyncMock
import json
import os

# Импортируем тестируемые функции
try:
    from handlers.sound import load_sound_config, sound_command, sound_callback
except ImportError as e:
    pytest.skip(f"Пропуск тестов sound: не удалось импортировать модуль sound ({e}).", allow_module_level=True)

# Тесты для функции load_sound_config
@patch('builtins.open', new_callable=mock_open, read_data='{"sound.mp3": "Звук 1", "beep.mp3": "Звук 2"}')
def test_load_sound_config_success(mock_file):
    """Тест успешной загрузки конфигурации звуков"""
    result = load_sound_config()
    
    assert isinstance(result, dict)
    assert result == {"sound.mp3": "Звук 1", "beep.mp3": "Звук 2"}
    mock_file.assert_called_once_with("config/sound_config.json", "r", encoding="utf-8")

@patch('builtins.open', side_effect=Exception("Ошибка чтения файла"))
def test_load_sound_config_error(mock_file):
    """Тест обработки ошибки при чтении конфигурации звуков"""
    # Нет необходимости мокать логгер, так как сообщение об ошибке
    # будет записано в реальный логгер
    
    result = load_sound_config()
    
    assert result == {}
    mock_file.assert_called_once_with("config/sound_config.json", "r", encoding="utf-8")

# Тесты для функции sound_command
@pytest.mark.asyncio
@patch('handlers.sound.load_sound_config')
async def test_sound_command_success(mock_load_config):
    """Тест успешного отображения звуковой панели"""
    mock_load_config.return_value = {"sound.mp3": "Звук 1", "beep.mp3": "Звук 2"}
    
    # Создаем моки для Update и Context
    mock_update = MagicMock()
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    mock_update.effective_chat.id = 123456
    
    await sound_command(mock_update, mock_context)
    
    # Проверяем, что был вызван метод send_message
    mock_context.bot.send_message.assert_called_once()
    # Проверяем аргументы вызова
    call_args = mock_context.bot.send_message.call_args[1]
    assert call_args['chat_id'] == 123456
    assert call_args['text'] == "Выберите звук:"
    # Проверяем наличие reply_markup с кнопками
    assert 'reply_markup' in call_args
    # Проверяем, что в SOUND_MAPPING теперь есть записи
    from handlers.sound import SOUND_MAPPING
    assert len(SOUND_MAPPING) == 2
    assert "sound:1" in SOUND_MAPPING
    assert "sound:2" in SOUND_MAPPING

@pytest.mark.asyncio
@patch('handlers.sound.load_sound_config')
async def test_sound_command_no_config(mock_load_config):
    """Тест обработки отсутствия конфигурации звуков"""
    mock_load_config.return_value = {}
    
    mock_update = MagicMock()
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    mock_update.effective_chat.id = 123456
    
    await sound_command(mock_update, mock_context)
    
    mock_context.bot.send_message.assert_called_once_with(
        chat_id=123456,
        text="Конфигурация звуков не найдена."
    )

# Тесты для функции sound_callback
@pytest.mark.asyncio
async def test_sound_callback_success():
    """Тест успешного воспроизведения звука"""
    # Настраиваем SOUND_MAPPING
    from handlers.sound import SOUND_MAPPING
    SOUND_MAPPING.clear()
    SOUND_MAPPING["sound:1"] = "test_sound.mp3"
    
    # Создаем моки
    mock_update = MagicMock()
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    mock_update.effective_chat.id = 123456
    mock_update.callback_query = AsyncMock()
    mock_update.callback_query.data = "sound:1"
    
    # Патчим os.path.exists и open
    with patch('os.path.exists', return_value=True), \
         patch('builtins.open', mock_open(read_data=b'audio data')):
        await sound_callback(mock_update, mock_context)
    
    # Проверяем, что вызваны все необходимые методы
    mock_update.callback_query.answer.assert_called_once()
    mock_context.bot.send_audio.assert_called_once()
    mock_update.callback_query.delete_message.assert_called_once()

@pytest.mark.asyncio
async def test_sound_callback_file_not_found():
    """Тест обработки отсутствующего аудиофайла"""
    # Настраиваем SOUND_MAPPING
    from handlers.sound import SOUND_MAPPING
    SOUND_MAPPING.clear()
    SOUND_MAPPING["sound:1"] = "nonexistent.mp3"
    
    mock_update = MagicMock()
    mock_context = MagicMock()
    mock_update.effective_chat.id = 123456
    mock_update.callback_query = AsyncMock()
    mock_update.callback_query.data = "sound:1"
    
    with patch('os.path.exists', return_value=False):
        await sound_callback(mock_update, mock_context)
    
    mock_update.callback_query.answer.assert_called_once()
    mock_update.callback_query.edit_message_text.assert_called_once_with("Аудиофайл не найден.")

@pytest.mark.asyncio
async def test_sound_callback_invalid_id():
    """Тест обработки недействительного ID звука"""
    # Очищаем SOUND_MAPPING
    from handlers.sound import SOUND_MAPPING
    SOUND_MAPPING.clear()
    
    mock_update = MagicMock()
    mock_context = MagicMock()
    mock_update.callback_query = AsyncMock()
    mock_update.callback_query.data = "sound:999"  # ID, которого нет в маппинге
    
    await sound_callback(mock_update, mock_context)
    
    mock_update.callback_query.answer.assert_called_once()
    mock_update.callback_query.edit_message_text.assert_called_once_with("Аудиофайл не найден.")

@pytest.mark.asyncio
async def test_sound_callback_send_error():
    """Тест обработки ошибки при отправке аудиофайла"""
    # Настраиваем SOUND_MAPPING
    from handlers.sound import SOUND_MAPPING
    SOUND_MAPPING.clear()
    SOUND_MAPPING["sound:1"] = "test_sound.mp3"
    
    mock_update = MagicMock()
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    mock_context.bot.send_audio.side_effect = Exception("Ошибка отправки")
    mock_update.effective_chat.id = 123456
    mock_update.callback_query = AsyncMock()
    mock_update.callback_query.data = "sound:1"
    
    # Мы не будем мокать логгер, так как сообщение записывается в реальный логгер
    with patch('os.path.exists', return_value=True), \
         patch('builtins.open', mock_open(read_data=b'audio data')):
        await sound_callback(mock_update, mock_context)
    
    mock_update.callback_query.answer.assert_called_once()
    mock_context.bot.send_audio.assert_called_once()
    mock_update.callback_query.edit_message_text.assert_called_once_with("Ошибка при воспроизведении звука.") 