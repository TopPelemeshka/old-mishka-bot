# handlers/start_help.py
"""
Модуль обработчиков команд приветствия и помощи.
Содержит обработчики для команд /start и /help, которые
показывают приветственное сообщение и справку по командам бота.
"""
from telegram import Update
from telegram.ext import ContextTypes
from utils import check_chat_and_execute

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /start - отправляет приветственное сообщение.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "👋 Привет, дружище!\n\n"
            "Я – Мишка, помогу добавить ярких красок в чат!\n"
            "Вызывай <b>/help</b> для полного списка команд.\n\n"
            "ГООООООООООООООООООООООООООООООООЛ! 😄"
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode="HTML"
        )
    await check_chat_and_execute(update, context, _start)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /help - отправляет справку по доступным командам бота.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    async def _help(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "📖 <b>Справка по командам бота</b> 📖\n\n"
            "Вот что я умею:\n\n"
            "• <b>/start</b> – Приветственное сообщение и краткая информация обо мне 💬\n"
            "• <b>/help</b> – Эта справка, чтобы ты всегда знал, что можно сделать 🛠️\n"
            "• <b>/roll [число]</b> – Бросить кубик от 1 до указанного числа 🎲\n"
            "• <b>/roulette варианты, через, запятую</b> – Провести рулетку на выбывание с твоими вариантами 🎰\n"
            "• <b>/all</b> – Массовый призыв 📢\n"
            "• <b>/coffee</b> – Что? ☕\n"
            "• <b>/mishka</b> – Показываю милого себя 🐻\n"
            "• <b>/durka</b> – Пакуем шизоидов 💊\n"
            "• <b>/rating</b> – Показать звездный рейтинг ⭐\n"
            "• <b>/sound</b> – Звуковая панель 🔊\n"
            "• <b>/sleep</b> – Спокойной ночи 🌙\n"
            "• <b>/morning</b> – Доброе утро 🌞\n"
            "• <b>/logout</b> – ╚╝٩(̾●̮̮̃̾•̃̾)۶٩ 👁️\n"
            "• <b>/meme [текст]</b> – Поиск мема по запросу 😂\n\n"
            "• <b>/post [HH:MM]</b> – Запланировать публикацию. Текст поста надо писать со следующей строчки, можно прикладывать фото, видео и звуки 📧\n"
            "• <b>/talk [текст]</b> – Мгновенно отправить сообщение в групповой чат. Поддерживает все типы медиа 📣\n"
            "• <b>/posts</b> – Просмотр и управление отложенными публикациями 📋\n"
            "• <b>/history</b> – Показать историю последних результатов ставок 📜\n\n"
            "🔸 <b>Технические команды</b>:\n"
            "• <b>/chatid</b> – Узнать ID чата\n"
            "• <b>/getfileid</b> – Получить file_id отправленного GIF\n"
            "• <b>/start_autopost</b> – Включить автопубликацию постов\n"
            "• <b>/stop_autopost</b> – Отключить автопубликацию постов\n"
            "• <b>/start_quiz</b> – Включить викторину и еженедельные итоги\n"
            "• <b>/stop_quiz</b> – Отключить викторину и еженедельные итоги\n"
            "• <b>/start_wisdom</b> – Включить публикацию мудрости дня\n"
            "• <b>/stop_wisdom</b> – Отключить публикацию мудрости дня\n"
            "• <b>/start_betting</b> – Включить систему ставок\n"
            "• <b>/stop_betting</b> – Отключить систему ставок\n"
            "• <b>/status</b> – Показать баланс материалов для постов и викторин\n"
            "• <b>/jobs</b> – Узнать расписание задач\n\n"
            "• <b>/technical_work</b> – Уведомление о технических работах\n\n"
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode="HTML"
        )
    await check_chat_and_execute(update, context, _help)
