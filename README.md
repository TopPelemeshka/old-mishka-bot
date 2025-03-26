# Telegram Bot

Многофункциональный Telegram бот с поддержкой различных команд и функций.

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/your-bot.git
cd your-bot
```

2. Создайте виртуальное окружение и активируйте его:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate     # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

## Настройка

1. Скопируйте примеры конфигурационных файлов:
```bash
cp config/bot_config.example.json config/bot_config.json
cp config/paths_config.example.json config/paths_config.json
cp config/sound_config.example.json config/sound_config.json
cp config/file_ids.example.json config/file_ids.json
```

2. Отредактируйте файлы конфигурации в директории `config/`:
   - `bot_config.json` - настройки бота (токен, разрешенные чаты и т.д.)
   - `paths_config.json` - пути к директориям с контентом
   - `sound_config.json` - настройки звуков (список доступных звуков и их названия)
   - `file_ids.json` - идентификаторы медиафайлов (GIF, изображения и т.д.)

3. Создайте необходимые директории для контента:
   - `post_materials/` - для исходных материалов
   - `post_archive/` - для архивированных материалов
   - `state_data/` - для данных состояний

## Запуск

```bash
python main.py
```

## Функциональность

- Автоматический постинг контента
- Система квизов
- Звуковые эффекты (встроенная панель звуков)
- Игровые функции
- И другие возможности

## Структура проекта

```
├── config/                 # Конфигурационные файлы
├── handlers/              # Обработчики команд
├── sound_panel/          # Звуковые файлы (включены в репозиторий)
├── pictures/             # Изображения (включены в репозиторий)
├── post_materials/       # Исходные материалы
├── post_archive/         # Архив материалов
├── state_data/           # Данные состояний
├── main.py              # Основной файл бота
├── config.py            # Загрузчик конфигураций
└── requirements.txt     # Зависимости проекта
```

## Лицензия

MIT 