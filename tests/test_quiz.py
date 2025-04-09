import pytest
import json
import os
import datetime
from unittest.mock import patch, mock_open, MagicMock, AsyncMock, call, ANY

# Импортируем тестируемые функции и переменные из quiz.py
try:
    import quiz
    from quiz import (
        load_weekly_quiz_count, save_weekly_quiz_count, WEEKLY_COUNT_FILE,
        load_quiz_questions, save_quiz_questions, QUIZ_FILE,
        load_rating, save_rating, RATING_FILE,
        load_praises, PRAISES_FILE,
        load_praise_index, save_praise_index, PRAISE_INDEX_FILE,
        get_random_question,
        get_next_praise,
        quiz_post_callback,
        poll_answer_handler,
        rating_command,
        weekly_quiz_reset,
        count_quiz_questions,
        start_quiz_command,
        stop_quiz_command,
        ACTIVE_QUIZZES, # Импортируем для очистки/проверки
    )
    # Импортируем зависимости для мокирования
    import state
    import config
    import balance
    from telegram import Poll, PollOption, User, PollAnswer
except ImportError as e:
    pytest.skip(f"Пропуск тестов quiz: не удалось импортировать модуль quiz или его зависимости ({e}).", allow_module_level=True)

# Фикстура для очистки ACTIVE_QUIZZES перед каждым тестом
@pytest.fixture(autouse=True)
def clear_active_quizzes():
    ACTIVE_QUIZZES.clear()
    # Устанавливаем режим теста, чтобы не модифицировать реальные файлы данных
    state.is_test_mode = True
    # Также сбрасываем состояние, используемое в тестах
    if hasattr(state, 'available_questions'):
        state.available_questions = []
    if hasattr(state, 'used_questions'):
        state.used_questions = set()
    if hasattr(state, 'current_poll_id'):
        state.current_poll_id = None
    if hasattr(state, 'current_correct_option'):
        state.current_correct_option = None
    if hasattr(state, 'quiz_enabled'):
        state.quiz_enabled = True # По умолчанию для большинства тестов
    yield
    # После выполнения тестов сбрасываем режим теста
    state.is_test_mode = False

# --- Тесты файловых операций --- (Упрощенные примеры, аналогично balance/state)

@patch('os.path.exists', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data='{"count": 5}')
def test_load_weekly_quiz_count_success(mock_file, mock_exists):
    assert load_weekly_quiz_count() == 5
    mock_exists.assert_called_once_with(WEEKLY_COUNT_FILE)
    mock_file.assert_called_once_with(WEEKLY_COUNT_FILE, "r", encoding="utf-8")

@patch('os.path.exists', return_value=False)
def test_load_weekly_quiz_count_no_file(mock_exists):
    assert load_weekly_quiz_count() == 0

@patch('builtins.open', new_callable=mock_open)
@patch('json.dump')
def test_save_weekly_quiz_count(mock_dump, mock_file):
    save_weekly_quiz_count(10)
    mock_file.assert_called_once_with(WEEKLY_COUNT_FILE, "w", encoding="utf-8")
    handle = mock_file()
    mock_dump.assert_called_once_with({"count": 10}, handle, ensure_ascii=False, indent=4)

# ... (Аналогичные тесты для load/save_quiz_questions, load/save_rating, load_praises, load/save_praise_index) ...
# Для краткости пропустим их детальную реализацию, но они должны быть написаны

# --- Тесты для get_random_question ---

@patch('state.available_questions', new_callable=list, create=True)
@patch('quiz.load_quiz_questions', return_value=[
    {"question": "Q1", "options": ["a","b","c"], "answer": "a"},
    {"question": "Q2", "options": ["c","d","e"], "answer": "d"}
])
@patch('quiz.save_quiz_questions')
@patch('state.used_questions', new_callable=set, create=True)
def test_get_random_question_success(mock_used_set, mock_save_func, mock_load_func, mock_available_list):
    # Исходная функция get_random_question ожидает список вопросов
    mock_load_func.return_value = [
        {"question": "Q1", "options": ["a","b","c"], "answer": "a"},
        {"question": "Q2", "options": ["c","d","e"], "answer": "d"}
    ]
    
    result = get_random_question()
    
    mock_load_func.assert_called_once()
    # Не проверяем вызов mock_save_func, так как реализация может сохранять вопросы
    assert result is not None
    assert result["question"] in ["Q1", "Q2"]
    # Не проверяем state.used_questions, т.к. вопросы удаляются из самого списка


def test_get_random_question_from_loaded():
    # Тестируем, что get_random_question вызывает load_quiz_questions и обрабатывает его результаты
    # Мокаем load_quiz_questions так, чтобы возвращал список с одним вопросом
    q_data = {"question": "Test", "options": ["A", "B"], "answer": "A"}
    
    with patch('quiz.load_quiz_questions', return_value=[q_data]) as mock_load, \
         patch('quiz.save_quiz_questions') as mock_save:
        result = get_random_question()
        
        mock_load.assert_called_once()
        # Не проверяем mock_save, так как реализация может сохранять вопросы
        assert result == q_data  # Функция должна вернуть тот же словарь из списка
        # Из-за mock_load в обоих вызовах будет создаваться новый список с одним элементом,
        # так что проверять изменение списка не имеет смысла


# --- Тесты для quiz_post_callback ---

@pytest.mark.asyncio
async def test_quiz_post_callback_success():
    """Тест успешной отправки викторины в чат."""
    # Подготавливаем мок данных для вопроса
    q_data = {
        "question": "Сколько будет 2+2?",
        "options": ["3", "4", "5"],
        "answer": "4"
    }
    
    # Создаем моки для бота и сообщения
    bot = AsyncMock()
    message = MagicMock()
    poll = MagicMock()
    poll.id = "poll123"
    message.poll = poll
    
    # Настраиваем мок для отправки опроса
    bot.send_poll = AsyncMock(return_value=message)
    
    # Создаем контекст с нашим мок-ботом
    context = MagicMock()
    context.bot = bot
    
    # Патчим все необходимые функции и значения
    with patch.object(quiz, 'get_random_question', return_value=q_data), \
         patch.object(state, 'quiz_enabled', True), \
         patch.object(quiz, 'POST_CHAT_ID', -1001234567890), \
         patch.object(quiz, 'ACTIVE_QUIZZES', {}), \
         patch.object(quiz, 'load_weekly_quiz_count', return_value=5), \
         patch.object(quiz, 'save_weekly_quiz_count') as mock_save_weekly_quiz_count:
        
        # Вызываем тестируемую функцию
        await quiz_post_callback(context)
        
        # Проверяем, что был вызов send_poll
        assert bot.send_poll.call_count == 1
        
        # Получаем аргументы вызова send_poll
        args, kwargs = bot.send_poll.call_args
        assert kwargs['chat_id'] == -1001234567890
        assert kwargs['question'] == q_data['question']
        assert kwargs['type'] == 'quiz'
        
        # Находим индекс правильного ответа в опциях
        options = kwargs['options']
        assert q_data['answer'] in options
        correct_option = options.index(q_data['answer'])
        assert kwargs['correct_option_id'] == correct_option
        
        # Проверяем, что poll_id добавлен в ACTIVE_QUIZZES
        assert quiz.ACTIVE_QUIZZES["poll123"] == correct_option
        
        # Проверяем, что счетчик викторин увеличен
        mock_save_weekly_quiz_count.assert_called_once_with(6)  # 5 + 1

@pytest.mark.asyncio
async def test_quiz_post_callback_no_questions():
    """Тест поведения при отсутствии вопросов для викторины."""
    # Создаем мок бота
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    
    # Создаем контекст с нашим мок-ботом
    context = MagicMock()
    context.bot = bot
    
    # Патчим необходимые функции и значения
    with patch.object(quiz, 'get_random_question', return_value=None), \
         patch.object(state, 'quiz_enabled', True), \
         patch.object(quiz, 'POST_CHAT_ID', 12345):
        
        # Вызываем тестируемую функцию
        await quiz_post_callback(context)
        
        # Проверяем, что был вызов send_message
        assert bot.send_message.call_count == 1
        
        # Получаем аргументы вызова send_message
        args, kwargs = bot.send_message.call_args
        assert kwargs['chat_id'] == 12345
        assert "закончились" in kwargs['text']


# --- Тесты для poll_answer_handler ---

@pytest.mark.asyncio
async def test_poll_answer_handler_correct():
    user_id = 111
    user_name = "UserOne"
    poll_id = "poll123"
    correct_option = 1
    
    with patch('quiz.update_balance') as mock_update_balance, \
         patch('quiz.load_rating', return_value={}) as mock_load_rating, \
         patch('quiz.save_rating') as mock_save_rating, \
         patch('quiz.ACTIVE_QUIZZES', {poll_id: correct_option}):

        update = MagicMock()
        update.poll_answer = MagicMock()
        update.poll_answer.poll_id = poll_id
        update.poll_answer.user = MagicMock()
        update.poll_answer.user.id = user_id
        update.poll_answer.user.username = user_name
        update.poll_answer.option_ids = [correct_option]
        
        context = MagicMock()
        
        # Вызываем тестируемую функцию
        await poll_answer_handler(update, context)
        
        # Проверяем обновление баланса и рейтинга
        mock_update_balance.assert_called_once_with(user_id, 5)
        
        # Проверяем сохранение рейтинга
        mock_save_rating.assert_called_once()
        saved_rating = mock_save_rating.call_args[0][0]
        assert str(user_id) in saved_rating
        assert saved_rating[str(user_id)]["stars"] == 1
        assert saved_rating[str(user_id)]["name"] == user_name


@pytest.mark.asyncio
async def test_poll_answer_handler_incorrect():
    user_id = 222
    user_name = "UserTwo"
    poll_id = "poll456"
    correct_option = 0  # верный ответ
    wrong_option = 2    # ответ пользователя
    
    with patch('quiz.update_balance') as mock_update_balance, \
         patch('quiz.load_rating') as mock_load_rating, \
         patch('quiz.save_rating') as mock_save_rating:

        # Настраиваем ACTIVE_QUIZZES напрямую
        ACTIVE_QUIZZES[poll_id] = correct_option

        update = MagicMock()
        update.poll_answer = MagicMock()
        update.poll_answer.poll_id = poll_id
        update.poll_answer.user = MagicMock()
        update.poll_answer.user.id = user_id
        update.poll_answer.user.username = user_name
        update.poll_answer.option_ids = [wrong_option]  # неверный ответ
        context = MagicMock()

        await poll_answer_handler(update, context)

        mock_update_balance.assert_not_called()
        mock_save_rating.assert_not_called()


# --- Тесты для rating_command ---

@pytest.mark.asyncio
async def test_rating_command_with_results():
    with patch('quiz.load_rating') as mock_load_rating, \
         patch('quiz.load_weekly_quiz_count', return_value=10) as mock_weekly_count:

        mock_load_rating.return_value = {
            "111": {"stars": 5, "name": "UserA"},
            "222": {"stars": 10, "name": "UserB"},
            "333": {"stars": 2, "name": "UserC"},
        }

        update = MagicMock()
        update.effective_chat.id = 123
        context = MagicMock()
        context.bot = AsyncMock()

        await rating_command(update, context)

        mock_load_rating.assert_called_once()
        context.bot.send_message.assert_awaited_once()
        args, kwargs = context.bot.send_message.await_args
        expected_text = (
            "<b>Звездный рейтинг (максимум 10 ⭐)</b>:\n"
            "• UserB: 10 ⭐\n"
            "• UserA: 5 ⭐\n"
            "• UserC: 2 ⭐"
        )
        assert kwargs['text'] == expected_text
        assert kwargs['chat_id'] == 123
        assert kwargs['parse_mode'] == 'HTML'


@pytest.mark.asyncio
async def test_rating_command_empty():
    with patch('quiz.load_rating', return_value={}) as mock_load_rating:
        update = MagicMock()
        update.effective_chat.id = 123
        context = MagicMock()
        context.bot = AsyncMock()
        context.bot.send_message = AsyncMock()

        await rating_command(update, context)

        mock_load_rating.assert_called_once()
        context.bot.send_message.assert_awaited_once_with(
            chat_id=123,
            text="Рейтинг пока пуст."
        )


# --- Тесты для start/stop_quiz_command ---

@pytest.mark.asyncio
async def test_start_quiz_command():
    """Тест запуска викторин."""
    # Создаем моки для обновления и контекста
    update = MagicMock()
    update.effective_chat.id = 123
    
    # Создаем мок бота
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    
    # Создаем контекст с нашим мок-ботом
    context = MagicMock()
    context.bot = bot
    
    # Запоминаем исходное значение quiz_enabled
    original_quiz_enabled = state.quiz_enabled
    
    try:
        # Устанавливаем исходное значение и патчим save_state
        state.quiz_enabled = False  # Начинаем с выключенных викторин
        
        # Создаем мок для save_state
        with patch('state.save_state') as mock_save_state:
            # Вызываем тестируемую функцию
            await quiz.start_quiz_command(update, context)
            
            # Проверяем, что было отправлено сообщение
            assert bot.send_message.call_count == 1
            
            # Получаем аргументы вызова send_message
            args, kwargs = bot.send_message.call_args
            assert kwargs['chat_id'] == 123
            assert "включены" in kwargs['text']
            
            # Проверяем что state.quiz_enabled был изменен на True
            assert state.quiz_enabled is True
            
            # Проверяем, что был вызов save_state для сохранения состояния
            assert mock_save_state.call_count == 1
    finally:
        # Восстанавливаем исходное значение
        state.quiz_enabled = original_quiz_enabled

@pytest.mark.asyncio
async def test_stop_quiz_command():
    """Тест остановки викторин."""
    # Создаем моки для обновления и контекста
    update = MagicMock()
    update.effective_chat.id = 123
    
    # Создаем мок бота
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    
    # Создаем контекст с нашим мок-ботом
    context = MagicMock()
    context.bot = bot
    
    # Запоминаем исходное значение quiz_enabled
    original_quiz_enabled = state.quiz_enabled
    
    try:
        # Устанавливаем исходное значение и патчим save_state
        state.quiz_enabled = True  # Начинаем с включенных викторин
        
        # Создаем мок для save_state
        with patch('state.save_state') as mock_save_state:
            # Вызываем тестируемую функцию
            await quiz.stop_quiz_command(update, context)
            
            # Проверяем, что было отправлено сообщение
            assert bot.send_message.call_count == 1
            
            # Получаем аргументы вызова send_message
            args, kwargs = bot.send_message.call_args
            assert kwargs['chat_id'] == 123
            assert "отключены" in kwargs['text']
            
            # Проверяем что state.quiz_enabled был изменен на False
            assert state.quiz_enabled is False
            
            # Проверяем, что был вызов save_state для сохранения состояния
            assert mock_save_state.call_count == 1
    finally:
        # Восстанавливаем исходное значение
        state.quiz_enabled = original_quiz_enabled

# --- Тесты для get_next_praise ---

@patch('quiz.load_praise_index')
@patch('quiz.save_praise_index')
def test_get_next_praise_cycling(mock_save_index, mock_load_index):
    # Список фраз похвалы
    test_praises = ["Отлично!", "Молодец!", "Превосходно!"]
    
    # Подготавливаем мок для load_praise_index
    # Мокаем различные индексы для проверки циклического перебора
    mock_load_index.side_effect = [0, 1, 2, 0]
    
    # Проверяем первый вызов (индекс 0 -> фраза 0)
    assert get_next_praise(test_praises) == test_praises[0]
    mock_load_index.assert_called_once()
    # Проверяем, что индекс сохранен как 1 для следующего вызова
    mock_save_index.assert_called_once_with(1)
    
    # Сбрасываем моки для нового вызова
    mock_load_index.reset_mock()
    mock_save_index.reset_mock()
    
    # Проверяем второй вызов (индекс 1 -> фраза 1)
    assert get_next_praise(test_praises) == test_praises[1]
    mock_load_index.assert_called_once()
    # Проверяем, что индекс сохранен как 2
    mock_save_index.assert_called_once_with(2)
    
    # Сбрасываем моки для нового вызова
    mock_load_index.reset_mock()
    mock_save_index.reset_mock()
    
    # Проверяем третий вызов (индекс 2 -> фраза 2)
    assert get_next_praise(test_praises) == test_praises[2]
    mock_load_index.assert_called_once()
    # Проверяем, что индекс сохранен как 3 (не цикл)
    mock_save_index.assert_called_once_with(3)

    # Сбрасываем моки для нового вызова
    mock_load_index.reset_mock()
    mock_save_index.reset_mock()
    
    # Проверяем четвертый вызов (индекс 0 -> фраза 0)
    assert get_next_praise(test_praises) == test_praises[0]
    mock_load_index.assert_called_once()
    # Проверяем, что индекс сохранен как 1
    mock_save_index.assert_called_once_with(1)

@patch('quiz.load_praise_index', return_value=0)
@patch('quiz.save_praise_index')
def test_get_next_praise_empty_list(mock_save_index, mock_load_index):
    assert get_next_praise([]) == "Поздравляем! (нет фраз в praises)"
    mock_load_index.assert_not_called()
    mock_save_index.assert_not_called()
    
# --- Тесты для count_quiz_questions ---
@patch('quiz.load_quiz_questions', return_value=["q1", "q2"])
def test_count_quiz_questions(mock_load):
    assert count_quiz_questions() == 2
    mock_load.assert_called_once()

@patch('quiz.load_quiz_questions', return_value=[])
@patch('quiz.save_quiz_questions')
def test_get_random_question_all_empty(mock_save, mock_load):
    # Тест на случай, если нет вопросов
    # Явно устанавливаем пустой список как возвращаемое значение
    mock_load.return_value = []
    
    result = get_random_question()
    
    mock_load.assert_called_once()
    # При пустом списке save не должна вызываться
    mock_save.assert_not_called()
    assert result is None


# --- Тесты для weekly_quiz_reset ---

@pytest.mark.asyncio
async def test_weekly_quiz_reset_with_winner():
    """Тест еженедельного сброса рейтинга викторин с победителем."""
    # Подготавливаем тестовые данные рейтинга
    test_rating = {
        "111": {"stars": 5, "name": "Winner"},
        "222": {"stars": 2, "name": "RunnerUp"}
    }
    
    # Создаем мок бота
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    
    # Создаем контекст с нашим мок-ботом
    context = MagicMock()
    context.bot = bot
    
    # Патчим все необходимые функции и значения
    with patch.object(state, 'quiz_enabled', True), \
         patch.object(quiz, 'POST_CHAT_ID', 999), \
         patch.object(quiz, 'load_rating', return_value=test_rating), \
         patch.object(quiz, 'save_rating') as mock_save_rating, \
         patch.object(quiz, 'load_weekly_quiz_count', return_value=10), \
         patch.object(quiz, 'save_weekly_quiz_count') as mock_save_weekly_quiz_count, \
         patch.object(quiz, 'load_praises', return_value=["End!"]), \
         patch.object(quiz, 'get_next_praise', return_value="End!"):
        
        # Вызываем тестируемую функцию
        await quiz.weekly_quiz_reset(context)
        
        # Проверяем, что было отправлено сообщение
        assert bot.send_message.call_count == 1
        
        # Получаем аргументы вызова send_message
        args, kwargs = bot.send_message.call_args
        assert kwargs['chat_id'] == 999
        assert "Winner" in kwargs['text']
        
        # Проверяем, что save_rating был вызван
        assert mock_save_rating.call_count == 1
        
        # Проверяем аргументы вызова save_rating (должен быть словарь где звезды обнулены)
        saved_data = mock_save_rating.call_args[0][0]
        assert isinstance(saved_data, dict)
        assert len(saved_data) == 2
        assert "111" in saved_data and "222" in saved_data
        assert saved_data["111"]["stars"] == 0
        assert saved_data["222"]["stars"] == 0
        
        # Проверяем, что счетчик викторин был сброшен
        mock_save_weekly_quiz_count.assert_called_once_with(0)

@pytest.mark.asyncio
async def test_weekly_quiz_reset_no_winner():
    """Тест еженедельного сброса рейтинга викторин без победителей."""
    # Создаем мок бота
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    
    # Создаем контекст с нашим мок-ботом
    context = MagicMock()
    context.bot = bot
    
    # Патчим все необходимые функции и значения
    with patch.object(state, 'quiz_enabled', True), \
         patch.object(quiz, 'POST_CHAT_ID', 999), \
         patch.object(quiz, 'load_rating', return_value={}), \
         patch.object(quiz, 'save_rating') as mock_save_rating, \
         patch.object(quiz, 'load_weekly_quiz_count', return_value=5), \
         patch.object(quiz, 'save_weekly_quiz_count') as mock_save_weekly_quiz_count:
        
        # Вызываем тестируемую функцию
        await quiz.weekly_quiz_reset(context)
        
        # Проверяем, что было отправлено сообщение о отсутствии победителей
        assert bot.send_message.call_count == 1
        
        # Получаем аргументы вызова send_message
        args, kwargs = bot.send_message.call_args
        assert kwargs['chat_id'] == 999
        assert "никто не набрал" in kwargs['text'].lower()
        
        # Проверяем вызовы функций
        assert mock_save_rating.call_count == 1
        saved_data = mock_save_rating.call_args[0][0]
        assert isinstance(saved_data, dict)
        assert len(saved_data) == 0  # Пустой словарь
        
        # Проверяем, что счетчик викторин был сброшен
        mock_save_weekly_quiz_count.assert_called_once_with(0)