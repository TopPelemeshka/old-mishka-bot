import pytest
import time
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, ANY, mock_open, call

# Импортируем тестируемые функции и переменные
try:
    from handlers.roll import roll_command, roll_callback
    # Импортируем зависимости для мокирования
    import utils
    import config
    import state
    from telegram import Update, InlineKeyboardMarkup, User, Message, CallbackQuery, InputMediaPhoto, InputMediaAnimation
except ImportError as e:
    pytest.skip(f"Пропуск тестов roll: не удалось импортировать модуль handlers.roll или его зависимости ({e}).", allow_module_level=True)

# --- Тесты для roll_command ---

@pytest.mark.asyncio
@patch('handlers.roll.check_chat_and_execute')
async def test_roll_command_wrapper_called(mock_check_chat):
    """Проверяем, что основная функция вызывает обертку check_chat_and_execute."""
    mock_check_chat.return_value = None
    update = MagicMock()
    context = MagicMock()
    await roll_command(update, context)
    mock_check_chat.assert_awaited_once_with(update, context, ANY)
    
    # Теперь проверим тесты с основной логикой функции
    # Мы сохраняем переданную функцию для использования в других тестах
    inner_func = mock_check_chat.call_args[0][2]
    return inner_func  # Возвращаем захваченную функцию для использования в других тестах

# Вспомогательная функция для получения внутренней функции roll_command
async def get_inner_roll_command():
    with patch('handlers.roll.check_chat_and_execute') as mock_check:
        mock_check.return_value = None
        update = MagicMock()
        context = MagicMock()
        await roll_command(update, context)
        return mock_check.call_args[0][2]  # Возвращаем захваченную функцию

# Тестируем внутреннюю логику _roll_command
@pytest.mark.asyncio
@patch('time.time')
@patch('asyncio.sleep', return_value=None)
@patch('random.randint', return_value=4) # Фиксированный результат броска
@patch('builtins.open', new_callable=mock_open, read_data=b'imagedata')
@patch('handlers.roll.DICE_GIF_ID', 'test_gif_id') # Мок ID гифки
@patch('handlers.roll.COOLDOWN', 5) # Мок кулдауна
@patch('handlers.roll.last_roll_time', {}) # Чистим словарь кулдауна перед тестом
async def test_roll_command_logic_default(mock_open_file, mock_randint, mock_sleep, mock_time):
    # Получаем внутреннюю функцию
    inner_func = await get_inner_roll_command()
    
    # Теперь тестируем её напрямую
    update = MagicMock(spec=Update)
    message = MagicMock(spec=Message)
    user = MagicMock(spec=User)
    user.id = 123
    update.effective_user = user
    update.effective_chat.id = 987
    context = MagicMock()
    context.args = [] # Нет аргументов, кубик d6
    context.bot = AsyncMock()
    # Мок для send_animation возвращает объект сообщения с ID
    mock_sent_message = MagicMock(spec=Message)
    mock_sent_message.chat_id = 987
    mock_sent_message.message_id = 555
    context.bot.send_animation.return_value = mock_sent_message
    context.bot.edit_message_media = AsyncMock()
    
    mock_time.return_value = 100.0 # Текущее время
    
    # Вызываем захваченную внутреннюю функцию
    await inner_func(update, context)
    
    # Проверка кулдауна (первый вызов)
    from handlers.roll import last_roll_time
    assert last_roll_time[123] == 100.0
    context.bot.send_message.assert_not_called() # Сообщения об ошибке кулдауна нет
    
    # Проверка отправки анимации
    context.bot.send_animation.assert_awaited_once_with(
        chat_id=987, 
        animation='test_gif_id', 
        caption="Кубик катится... 🎲"
    )
    mock_sleep.assert_awaited_once_with(1)
    
    # Проверка генерации результата (d6)
    mock_randint.assert_called_once_with(1, 6)
    
    # Проверка открытия файла картинки
    mock_open_file.assert_called_once_with("pictures/dice_result.png", "rb")
    
    # Проверка редактирования сообщения
    context.bot.edit_message_media.assert_awaited_once()
    call_args = context.bot.edit_message_media.call_args
    assert call_args.kwargs['chat_id'] == 987
    assert call_args.kwargs['message_id'] == 555
    # Проверка медиа (InputMediaPhoto)
    media_arg = call_args.kwargs['media']
    assert isinstance(media_arg, InputMediaPhoto)
    assert "🎲 Результат: 4 (из 6)" in media_arg.caption
    assert "🔄 Количество перебросов: 0" in media_arg.caption
    # Проверка клавиатуры
    reply_markup_arg = call_args.kwargs['reply_markup']
    assert isinstance(reply_markup_arg, InlineKeyboardMarkup)
    button = reply_markup_arg.inline_keyboard[0][0]
    assert button.text == "Перебросить (0)"
    assert button.callback_data == "roll|6|0"

@pytest.mark.asyncio
@patch('time.time')
@patch('handlers.roll.COOLDOWN', 5)
@patch('handlers.roll.last_roll_time', {123: 98.0}) # Последний бросок 2 сек назад
async def test_roll_command_logic_cooldown(mock_time):
    # Получаем внутреннюю функцию
    inner_func = await get_inner_roll_command()
    
    update = MagicMock(spec=Update)
    user = MagicMock(spec=User)
    user.id = 123
    update.effective_user = user
    update.effective_chat.id = 987
    context = MagicMock()
    context.args = []
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    
    mock_time.return_value = 100.0 # Текущее время (100 - 98 = 2 сек < 5 сек)
    
    await inner_func(update, context)
    
    # Проверка сообщения о кулдауне
    context.bot.send_message.assert_awaited_once()
    args = context.bot.send_message.call_args
    assert args.kwargs['chat_id'] == 987
    assert "Слишком быстрый бросок!" in args.kwargs['text']
    assert "Подождите 3.0 секунд." in args.kwargs['text']
    context.bot.send_animation.assert_not_called() # Анимация не должна отправляться
    context.bot.edit_message_media.assert_not_called()

@pytest.mark.asyncio
@patch('time.time', return_value=100.0)
@patch('asyncio.sleep', return_value=None)
@patch('random.randint', return_value=15)
@patch('builtins.open', new_callable=mock_open, read_data=b'imagedata')
@patch('handlers.roll.DICE_GIF_ID', 'test_gif_id')
@patch('handlers.roll.COOLDOWN', 5)
@patch('handlers.roll.last_roll_time', {}) 
async def test_roll_command_logic_with_arg(mock_open_file, mock_randint, mock_sleep, mock_time):
    # Получаем внутреннюю функцию
    inner_func = await get_inner_roll_command()
    
    update = MagicMock(spec=Update)
    message = MagicMock(spec=Message)
    user = MagicMock(spec=User)
    user.id = 123
    update.effective_user = user
    update.effective_chat.id = 987
    context = MagicMock()
    context.args = ["20"] # Бросок d20
    context.bot = AsyncMock()
    mock_sent_message = MagicMock(spec=Message)
    mock_sent_message.chat_id = 987
    mock_sent_message.message_id = 555
    context.bot.send_animation.return_value = mock_sent_message
    context.bot.edit_message_media = AsyncMock()
    
    await inner_func(update, context)
    
    mock_randint.assert_called_once_with(1, 20) # Проверка диапазона d20
    
    # Проверка редактирования сообщения
    call_args = context.bot.edit_message_media.call_args
    media_arg = call_args.kwargs['media']
    assert "🎲 Результат: 15 (из 20)" in media_arg.caption
    reply_markup_arg = call_args.kwargs['reply_markup']
    button = reply_markup_arg.inline_keyboard[0][0]
    assert button.callback_data == "roll|20|0" # Проверка max_number в callback_data

@pytest.mark.asyncio
@patch('time.time', return_value=100.0)
@patch('handlers.roll.last_roll_time', {}) 
async def test_roll_command_logic_invalid_arg(mock_time):
    # Получаем внутреннюю функцию
    inner_func = await get_inner_roll_command()
    
    update = MagicMock(spec=Update)
    user = MagicMock(spec=User)
    user.id = 123
    update.effective_user = user
    update.effective_chat.id = 987
    context = MagicMock()
    context.args = ["abc"]
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()

    await inner_func(update, context)
    
    context.bot.send_message.assert_awaited_once_with(chat_id=987, text="Некорректное число. Пример: /roll 20")
    context.bot.send_animation.assert_not_called()

# --- Тесты для roll_callback ---

@pytest.mark.asyncio
@patch('time.time', return_value=200.0)
@patch('asyncio.sleep', return_value=None)
@patch('random.randint', return_value=18) # Новый результат
@patch('builtins.open', new_callable=mock_open, read_data=b'imagedata')
@patch('handlers.roll.DICE_GIF_ID', 'test_gif_id') 
@patch('handlers.roll.COOLDOWN', 5) 
@patch('handlers.roll.last_roll_time', {}) 
async def test_roll_callback_logic(mock_open_file, mock_randint, mock_sleep, mock_time):
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.answer = AsyncMock()
    user = MagicMock(spec=User)
    user.id = 456
    query.from_user = user
    query.data = "roll|10|2" # Перебрасываем d10, 3-й бросок (индекс 2)
    query.edit_message_media = AsyncMock()
    update.callback_query = query
    context = MagicMock()
    
    await roll_callback(update, context)
    
    # Проверяем ответ на callback
    query.answer.assert_awaited_once()
    
    # Проверяем кулдаун
    from handlers.roll import last_roll_time
    assert last_roll_time[456] == 200.0
    
    # Проверяем редактирование на анимацию
    query.edit_message_media.assert_awaited()
    media_animation_call = query.edit_message_media.call_args_list[0]
    assert isinstance(media_animation_call.kwargs['media'], InputMediaAnimation)
    assert media_animation_call.kwargs['media'].media == 'test_gif_id'
    
    # Проверяем задержку
    mock_sleep.assert_awaited_once_with(1)
    
    # Проверяем рандом
    mock_randint.assert_called_once_with(1, 10)
    
    # Проверяем редактирование на результат
    media_photo_call = query.edit_message_media.call_args_list[1]
    assert isinstance(media_photo_call.kwargs['media'], InputMediaPhoto)
    assert "🎲 Результат: 18 (из 10)" in media_photo_call.kwargs['media'].caption
    assert "🔄 Количество перебросов: 3" in media_photo_call.kwargs['media'].caption
    
    # Проверка кнопки
    keyboard = media_photo_call.kwargs['reply_markup']
    button = keyboard.inline_keyboard[0][0]
    assert button.text == "Перебросить (3)"
    assert button.callback_data == "roll|10|3"

@pytest.mark.asyncio
@patch('time.time', return_value=200.0)
@patch('handlers.roll.COOLDOWN', 5)
@patch('handlers.roll.last_roll_time', {456: 198.0}) # Переброс 2 сек назад
async def test_roll_callback_logic_cooldown(mock_time):
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.answer = AsyncMock()
    user = MagicMock(spec=User)
    user.id = 456
    query.from_user = user
    query.data = "roll|10|2" 
    update.callback_query = query
    context = MagicMock()
    
    await roll_callback(update, context)
    
    # Проверка сообщения о кулдауне
    query.answer.assert_awaited_with(
        text="Слишком быстро! Подождите 3.0 секунд.",
        show_alert=True
    )
    query.edit_message_media.assert_not_called() 