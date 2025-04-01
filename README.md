# Mishka Bot

Бот для Telegram, который может:
- Отправлять случайные мемы и арты
- Играть в казино (рулетка, слоты)
- Отправлять случайные анекдоты и мудрости
- Желать доброго утра и спокойной ночи
- Воспроизводить звуки
- И многое другое!

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/TopPelemeshka/mishka-bot.git
cd mishka-bot
```

2. Установите необходимые пакеты для создания виртуального окружения:
```bash
# Для Debian/Ubuntu:
sudo apt update
sudo apt install python3.10-venv python3-pip
```

3. Создайте и активируйте виртуальное окружение:
```bash
python3 -m venv venv
source venv/bin/activate  # для Linux/Mac
# или
.\venv\Scripts\activate  # для Windows
```

4. Установите зависимости:
```bash
pip install -r requirements.txt
```

5. Создайте конфигурационные файлы:
```bash
cp config/bot_config.example.json config/bot_config.json
cp config/file_ids.example.json config/file_ids.json
cp config/paths_config.example.json config/paths_config.json
cp config/sound_config.example.json config/sound_config.json
cp config/schedule_config.example.json config/schedule_config.json
```

6. Создайте файлы состояния:
```bash
cp state_data/scheduled_posts.example.json state_data/scheduled_posts.json
cp state_data/balance.example.json state_data/balance.json
cp state_data/rating.example.json state_data/rating.json
cp state_data/weekly_quiz_count.example.json state_data/weekly_quiz_count.json
cp state_data/praise_state.example.json state_data/praise_state.json
cp state_data/sleep_index.example.json state_data/sleep_index.json
cp state_data/morning_index.example.json state_data/morning_index.json
cp state_data/bot_state.example.json state_data/bot_state.json
```

7. Отредактируйте конфигурационные файлы, добавив свои токены и настройки.

## Запуск

1. Активируйте виртуальное окружение (если еще не активировано):
```bash
source venv/bin/activate  # для Linux/Mac
# или
.\venv\Scripts\activate  # для Windows
```

2. Запустите бота:
```bash
python main.py
```

## Настройка расписания

Расписание публикаций постов, викторин и мудрости настраивается в файле `config/schedule_config.json`. Файл содержит следующие разделы:

- `autopost` - настройки расписания автопостов (утренние картинки, дневные видео, дневные картинки, вечерние картинки)
- `quiz` - настройки для викторин
- `wisdom` - настройки для мудрости дня
- `midnight_reset` - время сброса расписания
- `weekly_quiz_reset` - время еженедельного сброса викторин

Для каждой задачи можно настроить:
- `time_range` - диапазон времени для генерации случайного времени публикации
- `days` - дни недели (0-6, где 0 - воскресенье), в которые публикация будет выполняться

## Настройка автозапуска (для Linux)

1. Создайте файл сервиса systemd:
```bash
sudo nano /etc/systemd/system/mishka-bot.service
```

2. Добавьте следующее содержимое (замените пути на ваши):
```ini
[Unit]
Description=Mishka Telegram Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/mnt/external_disk/mishka-bot
Environment=PATH=/mnt/external_disk/mishka-bot/venv/bin
ExecStart=/mnt/external_disk/mishka-bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Активируйте и запустите сервис:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mishka-bot
sudo systemctl start mishka-bot
```

4. Проверьте статус:
```bash
sudo systemctl status mishka-bot
```

## Структура проекта

- `main.py` - основной файл бота
- `handlers/` - обработчики команд
- `casino/` - модули казино
- `config/` - конфигурационные файлы
- `pictures/` - изображения для бота
- `sound_panel/` - звуковые файлы
- `post_materials/` - материалы для постов
- `post_archive/` - архив постов
- `state_data/` - данные состояния
- `phrases/` - текстовые файлы с фразами

## Тестирование

Для запуска тестов используйте pytest:

1. Активируйте виртуальное окружение:
```bash
source venv/bin/activate  # для Linux/Mac
# или
.\venv\Scripts\activate  # для Windows
```

2. Запустите все тесты:
```bash
pytest
```

3. Запустите конкретную группу тестов:
```bash
pytest tests/test_casino_main.py
```

4. Запустите конкретный тест:
```bash
pytest tests/test_quiz.py::test_generate_quiz_question
```

5. Запустите тесты с подробным выводом:
```bash
pytest -v
```

6. Запустите тесты с покрытием кода:
```bash
pytest --cov=.
```

### Структура тестов

Проект содержит обширный набор тестов, охватывающих все основные функции бота:
- `test_main.py` - тесты основного модуля
- `test_casino_main.py`, `test_roulette.py`, `test_slots.py` - тесты казино
- `test_quiz.py` - тесты системы викторин
- `test_autopost.py` - тесты автопостинга
- `test_scheduler.py` - тесты планировщика
- `test_balance.py` - тесты системы баланса
- И многие другие

## Лицензия

MIT 