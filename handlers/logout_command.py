import asyncio
import logging
import random
import string
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from config import file_ids

logger = logging.getLogger(__name__)

def generate_random_hex(length: int) -> str:
    """Генерирует случайную шестнадцатеричную строку указанной длины."""
    return ''.join(random.choices('0123456789ABCDEF', k=length))

def generate_random_hex_bytes(count: int) -> str:
    """Генерирует последовательность из count байт в шестнадцатеричном виде через пробел."""
    return ' '.join(generate_random_hex(2) for _ in range(count))

def generate_random_binary(length: int) -> str:
    """Генерирует случайную бинарную строку указанной длины."""
    return ''.join(random.choice('01') for _ in range(length))

def generate_noise(length: int) -> str:
    """Генерирует строку «шума» из случайных символов указанной длины."""
    noise_chars = string.punctuation + string.ascii_letters + string.digits
    return ''.join(random.choices(noise_chars, k=length))

async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Список для хранения ID сообщений от бота
    sent_messages = []
    
    # Отправляем гифку с подписью
    logout_id = file_ids['animations']['logout']
    if logout_id:
        sent_animation = await context.bot.send_animation(
            chat_id=update.effective_chat.id,
            animation=logout_id,
            caption="Начинаю сканирование беседы..."
        )
    else:
        with open("pictures/hacker_logout.gif", "rb") as gif_file:
            sent_animation = await context.bot.send_animation(
                chat_id=update.effective_chat.id,
                animation=gif_file,
                caption="Начинаю сканирование беседы..."
            )
    
    sent_messages.append(sent_animation.message_id)
    
    # Эффект: бот «печатает»
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await asyncio.sleep(2.5)
    
    # Отправляем два начальных сообщения:
    # 1. Прогресс-бар с шумом
    progress_message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="> Инициализация системы очистки...\n[░░░░░░░░░░]"
    )
    sent_messages.append(progress_message.message_id)
    
    # 2. Хакерский текст
    hacker_message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="[ОБНАРУЖЕНО НЕДОПУСТИМОЕ ПОВЕДЕНИЕ]\nПодготовка..."
    )
    sent_messages.append(hacker_message.message_id)
    
    # Список стадий прогресс-бара
    progress_stages = [
        "[░░░░░░░░░░]",
        "[██░░░░░░░░]",
        "[████░░░░░░]",
        "[██████░░░░]",
        "[████████░░]",
        "[██████████]"
    ]
    
    # Возможные цели для сканирования
    targets = ["системы", "базы данных", "чатовых потоков", "сетевых узлов", "токсичных сообщений"]
    
    # Динамическое обновление сообщений
    for stage in progress_stages:
        # Генерируем динамические части для хакерского текста
        target = random.choice(targets)
        code = generate_random_hex(10)
        algo = generate_random_hex_bytes(8)
        encryption = generate_random_binary(32)
        noise_line = generate_noise(random.randint(10, 30))
        
        dynamic_hacker_text = (
            "[ОБНАРУЖЕНО НЕДОПУСТИМОЕ ПОВЕДЕНИЕ]\n"
            f"Сканирование {target}...\n"
            f"Обнаружен код: 0x{code}\n"
            f"Запуск алгоритма очистки: [{algo}]\n"
            f"Применение шифрования: {encryption}\n"
            f"{noise_line}"
        )
        # Обновляем прогресс-бар с дополнительным шумом
        progress_text = f"> Инициализация системы очистки...\n{stage}\n{generate_noise(20)}"
        
        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=progress_message.message_id,
                text=progress_text
            )
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=hacker_message.message_id,
                text=dynamic_hacker_text
            )
            await asyncio.sleep(1.5)
        except Exception as e:
            logger.error(f"Error updating messages: {e}")
            break
    
    # Финальное сообщение
    final_message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="[СИСТЕМА ОЧИСТКИ АКТИВИРОВАНА]\nВсе токсичные сообщения будут удалены."
    )
    sent_messages.append(final_message.message_id)
    
    # Удаляем все сообщения через 5 секунд
    await asyncio.sleep(5)
    for message_id in sent_messages:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=message_id
            )
        except Exception as e:
            logger.error(f"Error deleting message {message_id}: {e}")

