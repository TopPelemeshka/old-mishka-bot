import asyncio
import unittest
import sys
from unittest.mock import MagicMock, AsyncMock, patch, call
import datetime
import random # Добавим импорт random

# Импортируем необходимые классы и функции из telegram и нашего кода
# Примечание: Пути импорта могут потребовать корректировки в зависимости от структуры проекта
from telegram import Update, Message, User, Chat, PhotoSize, InputMediaPhoto, InputMediaVideo, InputMediaAudio, InputMediaDocument # Добавим остальные InputMedia*
from telegram.ext import ContextTypes, JobQueue, Job

# Импортируем тестируемые функции и константу POST_CHAT_ID
# Предполагается, что scheduler.py находится в корне проекта или настроен PYTHONPATH
try:
    from scheduler import talk_media_group_command, send_media_group_callback, POST_CHAT_ID, logger # Импортируем и логгер
except ImportError:
    # Если запуск тестов идет из другой директории, можно попробовать так:
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from scheduler import talk_media_group_command, send_media_group_callback, POST_CHAT_ID, logger


class TestTalkMediaGroup(unittest.TestCase):

    def setUp(self):
        """Настройка перед каждым тестом"""
        # Создаем базовые моки
        self.bot_mock = AsyncMock()
        self.job_queue_mock = MagicMock(spec=JobQueue)
        # Словарь для хранения 'запущенных' задач run_once
        self.scheduled_jobs = {}

        # Модифицируем job_queue_mock.run_once для имитации планирования
        def run_once_side_effect(callback, when, data, name):
            job_mock = MagicMock(spec=Job)
            job_mock.data = data
            job_mock.name = name
            self.scheduled_jobs[name] = {'callback': callback, 'job': job_mock, 'when': when}
            return job_mock

        self.job_queue_mock.run_once.side_effect = run_once_side_effect

        # Создаем мок Application
        self.application_mock = MagicMock()
        self.application_mock.bot = self.bot_mock
        self.application_mock.job_queue = self.job_queue_mock
        
        # Создаем мок для ContextTypes/CallbackContext
        self.context = MagicMock(spec=ContextTypes.DEFAULT_TYPE) 
        self.context.application = self.application_mock
        self.context.bot_data = {} # Инициализируем bot_data как пустой словарь
        self.context.chat_data = {}
        self.context.user_data = {}
        
        # Явно присваиваем bot и job_queue для прямого доступа, если код их использует
        self.context.bot = self.bot_mock 
        self.context.job_queue = self.job_queue_mock

        # Устанавливаем POST_CHAT_ID (если он импортирован)
        self.target_chat_id = POST_CHAT_ID if 'POST_CHAT_ID' in globals() else -1001234567890 # Запасной ID

    def _create_mock_photo_message(self, user_id, chat_id, media_group_id, file_id, caption=None):
        """Вспомогательная функция для создания мока сообщения с фото"""
        user = User(id=user_id, first_name='Test', is_bot=False)
        chat = Chat(id=chat_id, type='private')
        photo_size = PhotoSize(file_id=file_id, file_unique_id=f"uniq_{file_id}", width=100, height=100)
        message = Message(
            message_id=random.randint(1000, 9999),
            date=datetime.datetime.now(),
            chat=chat,
            from_user=user,
            media_group_id=str(media_group_id),
            photo=[photo_size],
            video=None, # Добавим None для других типов медиа
            audio=None,
            document=None,
            caption=caption
        )
        update = Update(update_id=random.randint(1000, 9999), message=message)
        return update, message

    @patch('scheduler.logger') # Мокаем логгер, чтобы не засорять вывод теста
    def test_media_group_handling_success(self, mock_logger):
        """Тест успешной обработки альбома из 3 фото"""
        # Параметры
        user_id = 123
        chat_id = 456
        media_group_id = 789
        file_ids = ["file1", "file2", "file3"]
        caption_command = "/talk Тестовый альбом"
        expected_caption = "Тестовый альбом"
        job_name = f"send_group_{media_group_id}"

        # 1. Имитируем получение первого сообщения с caption
        update1, _ = self._create_mock_photo_message(user_id, chat_id, media_group_id, file_ids[0], caption=caption_command)
        asyncio.run(talk_media_group_command(update1, self.context))

        # Проверка: создана запись в bot_data, запланирована задача
        self.assertIn('media_groups', self.context.bot_data)
        self.assertIn(str(media_group_id), self.context.bot_data['media_groups'])
        group_data = self.context.bot_data['media_groups'][str(media_group_id)]
        self.assertEqual(len(group_data['media']), 1)
        self.assertIsInstance(group_data['media'][0], InputMediaPhoto)
        self.assertEqual(group_data['media'][0].media, file_ids[0])
        self.assertEqual(group_data['caption'], expected_caption)
        self.assertEqual(group_data['chat_id'], chat_id)
        self.assertFalse(group_data['processed'])
        self.job_queue_mock.run_once.assert_called_once_with(
            send_media_group_callback,
            when=2, # Ожидаем задержку в 2 секунды
            data={'media_group_id': str(media_group_id)},
            name=job_name
        )
        self.assertIn(job_name, self.scheduled_jobs) # Проверяем, что задача действительно 'запланирована'

        # 2. Имитируем получение второго сообщения (без caption)
        update2, _ = self._create_mock_photo_message(user_id, chat_id, media_group_id, file_ids[1], caption=None)
        # Сбросим счетчик вызовов run_once перед вторым вызовом talk_command
        self.job_queue_mock.run_once.reset_mock()
        asyncio.run(talk_media_group_command(update2, self.context))

        # Проверка: добавлен второй файл, таймер перезапущен
        group_data = self.context.bot_data['media_groups'][str(media_group_id)]
        self.assertEqual(len(group_data['media']), 2)
        self.assertIsInstance(group_data['media'][1], InputMediaPhoto)
        self.assertEqual(group_data['media'][1].media, file_ids[1])
        # Убедимся, что run_once был вызван снова для перезапуска таймера
        self.job_queue_mock.run_once.assert_called_once_with(
             send_media_group_callback,
             when=2,
             data={'media_group_id': str(media_group_id)},
             name=job_name
        )

        # 3. Имитируем получение третьего сообщения (без caption)
        update3, _ = self._create_mock_photo_message(user_id, chat_id, media_group_id, file_ids[2], caption=None)
        # Сбросим счетчик вызовов run_once перед третьим вызовом talk_command
        self.job_queue_mock.run_once.reset_mock()
        asyncio.run(talk_media_group_command(update3, self.context))

         # Проверка: добавлен третий файл, таймер снова перезапущен
        group_data = self.context.bot_data['media_groups'][str(media_group_id)]
        self.assertEqual(len(group_data['media']), 3)
        self.assertIsInstance(group_data['media'][2], InputMediaPhoto)
        self.assertEqual(group_data['media'][2].media, file_ids[2])
        self.job_queue_mock.run_once.assert_called_once_with(
             send_media_group_callback,
             when=2,
             data={'media_group_id': str(media_group_id)},
             name=job_name
        )

        # 4. Имитируем срабатывание таймера - вызываем callback
        # Получаем последний запланированный callback
        scheduled_task = self.scheduled_jobs.get(job_name)
        self.assertIsNotNone(scheduled_task, f'Задача {job_name} не найдена в запланированных')
        callback_func = scheduled_task['callback']
        callback_job = scheduled_task['job']

        # Передаем мок context в callback
        # Важно: создаем новый мок Application для callback context
        mock_callback_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE) # Создаем мок для callback context
        mock_callback_context.application = MagicMock(bot=self.bot_mock) # Устанавливаем мок application с ботом
        mock_callback_context.bot_data = self.context.bot_data # Передаем bot_data
        # В callback_job.data тоже должна быть строка
        callback_job.data = {'media_group_id': str(media_group_id)}
        mock_callback_context.job = callback_job # Передаем мок задачи
        mock_callback_context.bot = self.bot_mock # Добавим прямого бота, так как send_media_group_callback его использует

        asyncio.run(callback_func(mock_callback_context))

        # 5. Проверяем результат вызова callback
        # Проверка вызова send_media_group
        self.bot_mock.send_media_group.assert_awaited_once()
        call_args, call_kwargs = self.bot_mock.send_media_group.call_args

        # Проверяем аргументы send_media_group
        self.assertEqual(call_kwargs.get('chat_id'), self.target_chat_id)
        sent_media = call_kwargs.get('media')
        self.assertIsNotNone(sent_media)
        self.assertEqual(len(sent_media), 3) # Должно быть 3 медиа

        # Проверяем содержимое и caption
        self.assertIsInstance(sent_media[0], InputMediaPhoto)
        self.assertEqual(sent_media[0].media, file_ids[0])
        self.assertEqual(sent_media[0].caption, expected_caption) # Caption у первого

        self.assertIsInstance(sent_media[1], InputMediaPhoto)
        self.assertEqual(sent_media[1].media, file_ids[1])
        self.assertIsNone(sent_media[1].caption) # У остальных нет

        self.assertIsInstance(sent_media[2], InputMediaPhoto)
        self.assertEqual(sent_media[2].media, file_ids[2])
        self.assertIsNone(sent_media[2].caption) # У остальных нет

        # Проверка отправки подтверждения пользователю
        self.bot_mock.send_message.assert_awaited_once_with(
            chat_id=chat_id, # Отправляем ответ в чат пользователя
            text=f'Альбом с 3 медиа отправлен в групповой чат.'
        )

        # Проверка очистки данных группы
        self.assertNotIn(str(media_group_id), self.context.bot_data.get('media_groups', {}))


# Запуск тестов, если файл выполняется напрямую
if __name__ == '__main__':
    # Для корректной работы asyncio в unittest
    if sys.platform == "win32" and sys.version_info >= (3, 8):
           asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    unittest.main() 