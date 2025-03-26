# utils_autopost.py
import os
import random
import shutil

SEPARATOR = "=================================================="

from config import (
    ANECDOTES_FILE,
    ERO_ANIME_DIR,
    ERO_REAL_DIR,
    SINGLE_MEME_DIR,
    STANDART_ART_DIR,
    STANDART_MEME_DIR,
    VIDEO_MEME_DIR,
    ARCHIVE_ERO_ANIME_DIR,
    ARCHIVE_ERO_REAL_DIR,
    ARCHIVE_SINGLE_MEME_DIR,
    ARCHIVE_STANDART_ART_DIR,
    ARCHIVE_STANDART_MEME_DIR,
    ARCHIVE_VIDEO_MEME_DIR,
)

def is_valid_file(file_path):
    """
    Проверяет, что файл подходит для отправки в Telegram.
    
    Файл должен:
    - Не быть .gitkeep
    - Не быть пустым
    - Иметь допустимое расширение
    """
    # Проверка, что это не .gitkeep
    if file_path.endswith('.gitkeep'):
        return False
    
    # Проверка, что файл существует
    if not os.path.exists(file_path):
        return False
    
    # Проверка, что файл не пустой
    if os.path.getsize(file_path) == 0:
        return False
    
    # Проверка расширения
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.webp']
    ext = os.path.splitext(file_path)[1].lower()
    return ext in valid_extensions

def get_top_anecdote_and_remove():
    """Возвращает случайный анекдот из файла и удаляет его из файла."""
    if not os.path.exists(ANECDOTES_FILE):
        return None

    with open(ANECDOTES_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        return None

    # Разбиваем контент на отдельные анекдоты по разделителю
    parts = [x.strip() for x in content.split(SEPARATOR) if x.strip()]
    if not parts:
        return None

    # Выбираем случайный индекс
    idx = random.randint(0, len(parts) - 1)
    anecdote = parts.pop(idx)

    # Сохраняем оставшиеся анекдоты обратно в файл
    remaining_str = f"\n{SEPARATOR}\n".join(parts)
    with open(ANECDOTES_FILE, "w", encoding="utf-8") as f:
        f.write(remaining_str.strip())

    return anecdote


def count_anecdotes():
    """Подсчитать количество оставшихся анекдотов."""
    if not os.path.exists(ANECDOTES_FILE):
        return 0
    with open(ANECDOTES_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        return 0
    parts = [x.strip() for x in content.split(SEPARATOR) if x.strip()]
    return len(parts)

def get_random_file_from_folder(folder):
    """Вернуть путь к случайному файлу из папки."""
    if not os.path.exists(folder):
        return None
    
    # Получаем список файлов и фильтруем только валидные
    all_files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    valid_files = [os.path.join(folder, f) for f in all_files if is_valid_file(os.path.join(folder, f))]
    
    if not valid_files:
        return None
    
    return random.choice(valid_files)

def move_file_to_archive(filepath, category):
    """Перенести файл в архивную папку соответствующей категории."""
    if category == "ero-anime":
        archive_dir = ARCHIVE_ERO_ANIME_DIR
    elif category == "ero-real":
        archive_dir = ARCHIVE_ERO_REAL_DIR
    elif category == "single-meme":
        archive_dir = ARCHIVE_SINGLE_MEME_DIR
    elif category == "standart-art":
        archive_dir = ARCHIVE_STANDART_ART_DIR
    elif category == "standart-meme":
        archive_dir = ARCHIVE_STANDART_MEME_DIR
    elif category == "video-meme":
        archive_dir = ARCHIVE_VIDEO_MEME_DIR
    else:
        # Для прочих категорий, если появятся
        archive_dir = os.path.join("archive", category)

    os.makedirs(archive_dir, exist_ok=True)

    basename = os.path.basename(filepath)
    new_path = os.path.join(archive_dir, basename)
    shutil.move(filepath, new_path)

def count_files_in_folder(folder):
    """Подсчитать число файлов (только файлы) в папке."""
    if not os.path.exists(folder):
        return 0
    return sum(1 for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)))

def get_available_stats():
    """
    Возвращает словарь с информацией о количестве файлов в каждой категории + анекдоты.
    """
    stats = {
        "ero-anime": count_files_in_folder(ERO_ANIME_DIR),
        "ero-real": count_files_in_folder(ERO_REAL_DIR),
        "single-meme": count_files_in_folder(SINGLE_MEME_DIR),
        "standart-art": count_files_in_folder(STANDART_ART_DIR),
        "standart-meme": count_files_in_folder(STANDART_MEME_DIR),
        "video-meme": count_files_in_folder(VIDEO_MEME_DIR),
        "anecdotes": count_anecdotes()
    }
    return stats

def predict_10pics_posts(stats):
    """
    Считает, сколько раз мы можем сделать пост с 10 картинками, учитывая текущие остатки stats.
    Конфигурация:
        1 - ero-real
        2 - standart-art/standart-meme
        3 - ero-anime
        4 - single-meme/standart-meme
        5 - ero-real
        6 - standart-meme
        7 - ero-anime
        8 - standart-meme
        9 - ero-real
        10 - standart-meme
    Каждый такой пост требует 1 анекдот.
    """
    # Будем копировать словарь, чтобы не портить оригинал
    st = stats.copy()

    count_posts = 0
    while True:
        # Нужно 1 анекдот
        if st["anecdotes"] < 1:
            break

        # Нужно 3 ero-real (пункты 1,5,9)
        if st["ero-real"] < 3:
            break

        # Нужно 2 ero-anime (пункты 3,7)
        if st["ero-anime"] < 2:
            break

        # Нужно минимум 3 "standart-meme" (пункты 6,8,10) — это без учёта фолбэка
        if st["standart-meme"] < 3:
            break

        # Позиция 2: standart-art, а если нет — standart-meme
        need_art_for_2 = 1
        # Позиция 4: single-meme, а если нет — standart-meme
        need_single_for_4 = 1

        # Посчитаем, сколько *дополнительно* может понадобиться "standart-meme", если нет арт или single
        additional_meme_needed = 0

        # Есть ли standart-art для позиции 2?
        if st["standart-art"] >= need_art_for_2:
            # используем 1 шт. standart-art
            pass
        else:
            # fallback в stand-meme
            additional_meme_needed += need_art_for_2

        # Есть ли single-meme для позиции 4?
        if st["single-meme"] >= need_single_for_4:
            # используем 1 шт. single-meme
            pass
        else:
            # fallback в stand-meme
            additional_meme_needed += need_single_for_4

        # Проверим, хватит ли "standart-meme" на fallback + 3 обязательных
        total_meme_needed = 3 + additional_meme_needed
        if st["standart-meme"] < total_meme_needed:
            break

        # Если мы дошли сюда, значит можем сформировать пост
        # "Списываем" ресурсы:
        st["anecdotes"] -= 1
        st["ero-real"] -= 3
        st["ero-anime"] -= 2
        st["standart-meme"] -= 3  # обязательная часть

        # Позиция 2:
        if st["standart-art"] >= 1:
            st["standart-art"] -= 1
        else:
            st["standart-meme"] -= 1  # fallback

        # Позиция 4:
        if st["single-meme"] >= 1:
            st["single-meme"] -= 1
        else:
            st["standart-meme"] -= 1  # fallback

        count_posts += 1

    return count_posts

def predict_3videos_posts(stats):
    """
    Считает, сколько раз мы можем сделать пост с 3 видео из "video-meme" + 1 анекдот.
    """
    st = stats.copy()
    count_posts = 0
    while True:
        # Нужно 1 анекдот
        if st["anecdotes"] < 1:
            break
        # Нужно 3 video-meme
        if st["video-meme"] < 3:
            break

        st["anecdotes"] -= 1
        st["video-meme"] -= 3
        count_posts += 1

    return count_posts

def predict_full_days(stats):
    """
    Считает, сколько "полных дней" по схеме:
    - 2 поста "10 картинок"
    - 1 пост "3 видео"
    в сутки
    (т.е. всего 3 анекдота в день и соответствующие файлы).
    """
    st = stats.copy()
    days = 0
    while True:
        # За 1 день нужно 2 поста с 10 картинками + 1 пост с 3 видео.
        # Суммарно 3 анекдота.
        if st["anecdotes"] < 4:
            break

        # Для 2 постов "10 картинок" по описанной схеме (см. predict_10pics_posts — но нам нужно сделать это 2 раза подряд)
        # Упростим: 2 * (3 ero-real, 2 ero-anime, ...). Но нужно учесть fallback на stand-meme и т.д.

        # Проверим сразу, хватит ли ero-real и ero-anime:
        if st["ero-real"] < 9:   # 3*2
            break
        if st["ero-anime"] < 6: # 2*2
            break

        # stand-meme: минимум 2*3 = 6 на гарантированные позиции (6,8,10) в каждом посте.
        # Но также нужно учесть fallback:
        # Позиция 2 (в каждом посте): всего 2шт. -> при нехватке stand-art => fallback stand-meme
        # Позиция 4 (в каждом посте): всего 2шт. -> при нехватке single-meme => fallback stand-meme
        # То есть потенциально ещё +2 (если stand-art=0) +2 (если single-meme=0) = +4. Итого максимум 10.

        # Посчитаем, сколько у нас stand-art и single-meme
        # Для 2 постов нужно 2 stand-art (позиция 2) и 2 single-meme (позиция 4), если хотим без fallback.
        fallback_meme_needed = 0

        # Позиция 2: нужно 2 stand-art
        needed_art = 2
        if st["standart-art"] < needed_art:
            fallback_meme_needed += (needed_art - st["standart-art"])

        # Позиция 4: нужно 2 single-meme
        needed_single = 2
        if st["single-meme"] < needed_single:
            fallback_meme_needed += (needed_single - st["single-meme"])

        total_meme_needed = 9 + fallback_meme_needed
        if st["standart-meme"] < total_meme_needed:
            break

        # Для 1 поста "3 видео" нужно 3 video-meme
        if st["video-meme"] < 3:
            break

        # Если все проверки пройдены, то "списываем" ресурсы на 2*10pics + 1*3videos
        st["anecdotes"] -= 4
        st["ero-real"] -= 9
        st["ero-anime"] -= 8

        # stand-meme - списываем 6 «обязательных»
        st["standart-meme"] -= 9

        # stand-art:
        if st["standart-art"] >= 3:
            st["standart-art"] -= 3
        else:
            # используем, что есть
            used_art = st["standart-art"]
            st["standart-art"] = 0
            # оставшиеся идут в fallback
            fallback_for_art = 3 - used_art
            st["standart-meme"] -= fallback_for_art

        # single-meme:
        if st["single-meme"] >= 3:
            st["single-meme"] -= 3
        else:
            used_single = st["single-meme"]
            st["single-meme"] = 0
            fallback_for_single = 3 - used_single
            st["standart-meme"] -= fallback_for_single

        # video-meme на 3 видео
        st["video-meme"] -= 3

        days += 1

    return days
