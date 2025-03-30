# quiz.py
"""
Модуль для проведения викторин (квизов) в Telegram-чате.
Обеспечивает:
- Загрузку и сохранение вопросов
- Генерацию случайных вопросов
- Отслеживание рейтинга участников
- Еженедельное обновление викторин
"""

import os
import json
import random
import datetime

from telegram import Poll
from telegram.ext import ContextTypes

from config import POST_CHAT_ID, MATERIALS_DIR

from balance import update_balance

import state


# Пути к файлам
QUIZ_FILE = os.path.join(MATERIALS_DIR, "quiz.json")  # исходные вопросы
RATING_FILE = "state_data/rating.json"                           # для хранения звёзд
PRAISES_FILE = "phrases/praises_rating.txt"  # тексты похвал
PRAISE_INDEX_FILE = "state_data/praise_state.json"

# Глобальная структура, чтобы запоминать правильный ответ
# key = poll_id (str), value = correct_option_id (int)
ACTIVE_QUIZZES = {}

WEEKLY_COUNT_FILE = "state_data/weekly_quiz_count.json"

def load_weekly_quiz_count() -> int:
    """
    Загружает количество вопросов викторины за неделю из WEEKLY_COUNT_FILE.
    Если файла нет или он некорректный, возвращает 0.
    
    Returns:
        int: Количество вопросов за текущую неделю
    """
    if not os.path.exists(WEEKLY_COUNT_FILE):
        return 0
    try:
        with open(WEEKLY_COUNT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "count" in data:
                return data["count"]
    except Exception as e:
        pass
    return 0

def save_weekly_quiz_count(count: int):
    """
    Сохраняет количество вопросов викторины за неделю в WEEKLY_COUNT_FILE.
    
    Args:
        count: Количество вопросов для сохранения
    """
    with open(WEEKLY_COUNT_FILE, "w", encoding="utf-8") as f:
        json.dump({"count": count}, f, ensure_ascii=False, indent=4)


def load_quiz_questions() -> list[dict]:
    """
    Считывает вопросы из quiz.json. Формат:
    [
        {
            "question": "Какая планета ближе всего к Солнцу?",
            "options": ["Венера", "Земля", "Меркурий", "Марс"],
            "answer": "Меркурий"
        },
        ...
    ]
    
    Returns:
        list[dict]: Список словарей с вопросами, вариантами ответов и правильным ответом
    """
    if not os.path.exists(QUIZ_FILE):
        return []
    with open(QUIZ_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            return []
    return []


def save_quiz_questions(questions: list[dict]):
    """
    Перезаписывает файл quiz.json.
    
    Args:
        questions: Список словарей с вопросами для сохранения
    """
    with open(QUIZ_FILE, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=4)


def get_random_question() -> dict | None:
    """
    Возвращает случайный вопрос из quiz.json и удаляет его из файла,
    чтобы не повторялся.
    
    Returns:
        dict|None: Словарь с вопросом или None, если вопросов нет
    """
    questions = load_quiz_questions()
    if not questions:
        return None
    question = random.choice(questions)
    questions.remove(question)
    save_quiz_questions(questions)
    return question


def load_rating() -> dict:
    """
    Загружает рейтинг участников викторины.
    
    Returns:
        dict: Словарь вида:
          {
             "123456789": { "stars": 3, "name": "username_или_имя" },
             "987654321": { "stars": 1, "name": "другое_имя" }
          }
        Если файл пуст или отсутствует — вернёт пустой словарь.
    """
    if not os.path.exists(RATING_FILE):
        return {}
    try:
        with open(RATING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception as e:
        return {}

def save_rating(rating: dict):
    """
    Сохраняет рейтинг в JSON-файл.
    
    Args:
        rating: Словарь вида:
            dict[user_id_str] = { "stars": int, "name": str }
    """
    try:
        with open(RATING_FILE, "w", encoding="utf-8") as f:
            json.dump(rating, f, ensure_ascii=False, indent=4)
    except Exception as e:
        pass



def load_praises() -> list[str]:
    """
    Считывает фразы похвалы из файла.
    
    Returns:
        list[str]: Список строк с фразами похвалы
    """
    if not os.path.exists(PRAISES_FILE):
        return ["Поздравляем! Ты великолепен!", "Блестящая победа!"]
    with open(PRAISES_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
        return lines if lines else ["Молодец!", "Отличный результат!"]
    

def load_praise_index() -> int:
    """
    Загружает текущий индекс для циклического выбора фраз похвалы.
    
    Returns:
        int: Текущий индекс или 0, если файла нет
    """
    if not os.path.exists(PRAISE_INDEX_FILE):
        return 0
    try:
        with open(PRAISE_INDEX_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "praise_index" in data:
                return data["praise_index"]
    except:
        pass
    return 0

def save_praise_index(index: int):
    """
    Сохраняет текущий индекс фразы похвалы.
    
    Args:
        index: Индекс последней использованной фразы
    """
    with open(PRAISE_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump({"praise_index": index}, f, ensure_ascii=False, indent=4)

def get_next_praise(praises: list[str]) -> str:
    """
    Возвращает очередную фразу из списка `praises` по циклу.
    Состояние (индекс) хранится в praise_state.json.
    
    Args:
        praises: Список фраз похвалы
    
    Returns:
        str: Следующая фраза похвалы
    """
    if not praises:
        return "Поздравляем! (нет фраз в praises)"

    current_index = load_praise_index()
    phrase = praises[current_index % len(praises)]
    # Увеличиваем индекс и сохраняем
    current_index += 1
    save_praise_index(current_index)
    return phrase


async def quiz_post_callback(context: ContextTypes.DEFAULT_TYPE):
    """
    Callback-функция для публикации нового вопроса викторины.
    Вызывается по расписанию.
    
    Args:
        context: Контекст от планировщика задач Telegram
    """
    # Добавляем проверку флага викторины:
    if not state.quiz_enabled:
        return

    question_data = get_random_question()
    if not question_data:
        await context.bot.send_message(
            chat_id=POST_CHAT_ID,
            text="Вопросы для викторины закончились 😢"
        )
        return

    question_text = question_data["question"]
    original_options = question_data["options"]
    correct_answer = question_data["answer"]

    # Перемешиваем варианты ответов для непредсказуемости
    shuffled_options = original_options[:]
    random.shuffle(shuffled_options)
    try:
        correct_index = shuffled_options.index(correct_answer)
    except ValueError:
        correct_index = 0

    message = await context.bot.send_poll(
        chat_id=POST_CHAT_ID,
        question=question_text,
        options=shuffled_options,
        type=Poll.QUIZ,
        correct_option_id=correct_index,
        is_anonymous=False,
        allows_multiple_answers=False
    )

    # Сохраняем правильный ответ для данного опроса:
    ACTIVE_QUIZZES[message.poll.id] = correct_index

    # Увеличиваем количество вопросов викторины за неделю:
    current_count = load_weekly_quiz_count()
    current_count += 1
    save_weekly_quiz_count(current_count)



async def poll_answer_handler(update, context):
    """
    Обработчик ответа пользователя на викторину.
    Начисляем монеты, если выбран правильный вариант.
    """
    poll_answer = update.poll_answer
    poll_id = poll_answer.poll_id
    user_id = poll_answer.user.id
    chosen_ids = poll_answer.option_ids  # выбранные индексы
    if poll_id not in ACTIVE_QUIZZES:
        return

    correct_index = ACTIVE_QUIZZES[poll_id]

    # Если пользователь выбрал правильный вариант (совпал индекс)
    if correct_index in chosen_ids:
        rating = load_rating()
        user_id_str = str(user_id)

        # Получаем текущие данные пользователя из рейтинга
        old_data = rating.get(user_id_str, {"stars": 0, "name": None})
        old_data["stars"] = old_data.get("stars", 0) + 1  # увеличиваем звезды

        # Запоминаем имя пользователя
        tg_user = poll_answer.user
        name_candidate = tg_user.username if tg_user.username else tg_user.first_name
        if not name_candidate:
            name_candidate = f"User_{user_id_str}"  # на случай, если ничего нет

        old_data["name"] = name_candidate

        rating[user_id_str] = old_data
        save_rating(rating)

        # Начисляем 5 монет за правильный ответ
        update_balance(user_id, 5)  # Награда за правильный ответ




async def rating_command(update, context):
    """
    /rating — показать текущий рейтинг (сортируем по убыванию звёзд),
    а также в первой строке указывается, из скольки максимальных звезд (количество вопросов за неделю).
    """
    rating = load_rating()
    weekly_count = load_weekly_quiz_count()  # максимальное число звезд, если бы все ответы были верными

    if not rating:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Рейтинг пока пуст.")
        return

    # Сортируем по количеству звезд
    items = sorted(rating.items(), key=lambda x: x[1]["stars"], reverse=True)

    lines = [f"<b>Звездный рейтинг (максимум {weekly_count} ⭐)</b>:"]
    for user_id_str, data in items:
        stars = data["stars"]
        name = data["name"] or user_id_str
        lines.append(f"• {name}: {stars} ⭐")

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="\n".join(lines),
        parse_mode="HTML"
    )



async def weekly_quiz_reset(context: ContextTypes.DEFAULT_TYPE):
    if not state.quiz_enabled:
        return

    rating = load_rating()
    if not rating:
        await context.bot.send_message(
            chat_id=POST_CHAT_ID,
            text="На этой неделе никто не набрал звёздочек 😢"
        )
        return

    max_stars = max(x["stars"] for x in rating.values())
    winners = [uid for (uid, val) in rating.items() if val["stars"] == max_stars]

    praises = load_praises()
    random_praise = get_next_praise(praises)

    lines = ["<b>Итоги недели!</b>"]
    lines.append(f"Победитель с результатом {max_stars} ⭐:")
    for w in winners:
        name = rating[w]["name"] or "Безымянный"
        lines.append(f"• {name}")
    lines.append("")
    lines.append(random_praise)
    lines.append("")
    lines.append("Звездный рейтинг за неделю:")

    all_sorted = sorted(rating.items(), key=lambda x: x[1]["stars"], reverse=True)
    for _, val in all_sorted:
        stars = val["stars"]
        name = val["name"] or "Безымянный"
        lines.append(f"• {name}: {stars} ⭐")

    await context.bot.send_message(
        chat_id=POST_CHAT_ID,
        text="\n".join(lines),
        parse_mode="HTML"
    )

    # Сбрасываем звёзды пользователей:
    for k in rating.keys():
        rating[k]["stars"] = 0
    save_rating(rating)

    # Сбрасываем количество вопросов викторины за неделю:
    save_weekly_quiz_count(0)



#
# === Подсчёт оставшихся вопросов ===
#

def count_quiz_questions() -> int:
    """Просто возвращаем, сколько осталось вопросов в quiz.json."""
    questions = load_quiz_questions()
    return len(questions)

#
# Новые команды для включения/выключения викторины
#
async def start_quiz_command(update, context):
    state.quiz_enabled = True
    # Передаём текущее значение глобальных переменных явно
    state.save_state(state.autopost_enabled, state.quiz_enabled)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Викторина и еженедельные итоги включены!"
    )

async def stop_quiz_command(update, context):
    state.quiz_enabled = False
    print("DEBUG: quiz_enabled =", state.quiz_enabled)
    state.save_state(state.autopost_enabled, state.quiz_enabled)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Викторина и еженедельные итоги выключены!"
    )