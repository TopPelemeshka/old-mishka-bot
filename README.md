# Mishka Bot

Бот для Telegram, который может:
- Отправлять случайные мемы и арты
- Играть в казино (рулетка, слоты)
- Отправлять случайные анекдоты и мудрости
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
```

6. Создайте файлы состояния:
```bash
cp state_data/scheduled_posts.example.json state_data/scheduled_posts.json
cp state_data/balance.example.json state_data/balance.json
cp state_data/rating.example.json state_data/rating.json
cp state_data/weekly_quiz_count.example.json state_data/weekly_quiz_count.json
cp state_data/praise_state.example.json state_data/praise_state.json
cp state_data/sleep_index.example.json state_data/sleep_index.json
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

## Лицензия

MIT 