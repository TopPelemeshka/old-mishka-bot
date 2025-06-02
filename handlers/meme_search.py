# handlers/meme_search.py
import logging
import httpx
import random
import os
from telegram import Update, InputMediaPhoto
from telegram.ext import ContextTypes
from config import MEMOTEKA_API_URL, MEMOTEKA_WEB_APP_URL

logger = logging.getLogger(__name__)

MEME_SEARCHING_PHRASES_FILE = "phrases/meme_searching_phrases.txt" 
DEFAULT_SEARCHING_MESSAGE = "Подбираю лучшие мемы по запросу: \"{query}\"..."

def load_meme_searching_phrases() -> list[str]:
    phrases = []
    if not os.path.exists(MEME_SEARCHING_PHRASES_FILE):
        logger.warning(f"Файл с фразами для поиска мемов не найден: {MEME_SEARCHING_PHRASES_FILE}")
        return phrases 
    try:
        with open(MEME_SEARCHING_PHRASES_FILE, "r", encoding="utf-8") as f:
            phrases = [line.strip() for line in f if line.strip()]
        if not phrases:
            logger.warning(f"Файл {MEME_SEARCHING_PHRASES_FILE} пуст или содержит только пустые строки.")
    except Exception as e:
        logger.error(f"Ошибка чтения файла с фразами {MEME_SEARCHING_PHRASES_FILE}: {e}", exc_info=True)
    return phrases

async def search_meme_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Пожалуйста, укажите описание ситуации после команды /meme.\n"
            "Пример: `/meme кот смотрит на рыбу`",
            parse_mode='Markdown'
        )
        return

    if not MEMOTEKA_API_URL or not MEMOTEKA_WEB_APP_URL:
        logger.error("URL API Мемотеки или Web App не настроены в конфигурации.")
        await update.message.reply_text("Извините, сервис поиска мемов временно недоступен (ошибка конфигурации).")
        return

    search_query = " ".join(context.args)
    user_id = update.effective_user.id
    logger.info(f"Бот: получен запрос на поиск мема: '{search_query}' от user {user_id}")
    
    searching_message_text = ""
    loaded_phrases = load_meme_searching_phrases()

    if loaded_phrases:
        chosen_phrase_template = random.choice(loaded_phrases)
        searching_message_text = chosen_phrase_template.replace("[query]", search_query)
    else:
        searching_message_text = DEFAULT_SEARCHING_MESSAGE.format(query=search_query)
        
    # searching_message_object = None # Можно объявить, но мы его не будем удалять
    try:
        # Отправляем сообщение о поиске и НЕ будем его сохранять для удаления
        await update.message.reply_text(searching_message_text)

        api_search_url = f"{MEMOTEKA_API_URL}/search"
        payload = {
            "q": search_query,
            "limit": 2, 
            "user_id": user_id,
            "search_mode": "situation"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(api_search_url, json=payload, timeout=120.0) 
            response.raise_for_status()
            data = response.json()
        
        # --- УДАЛЕНО УДАЛЕНИЕ СООБЩЕНИЯ О ПОИСКЕ ---
        # if searching_message_object:
        #    try: 
        #        await searching_message_object.delete()
        #        searching_message_object = None 
        #    except Exception as e_del:
        #         logger.warning(f"Не удалось удалить сообщение 'Ищу мем...': {e_del}")
        
        results = data.get("results")
        if results and len(results) > 0:
            media_group = []
            links_if_media_group_fails = []

            for meme_data in results:
                image_url_path = meme_data.get("image_url") 
                meme_id = meme_data.get("id", "unknown_id")

                if not image_url_path:
                    logger.warning(f"Бот: у мема {meme_id} отсутствует image_url.")
                    continue 

                if image_url_path.startswith("/"):
                    full_image_url = f"{MEMOTEKA_WEB_APP_URL.rstrip('/')}{image_url_path}"
                else: 
                    full_image_url = image_url_path
                
                media_group.append(InputMediaPhoto(media=full_image_url))
                links_if_media_group_fails.append(full_image_url)

                if len(media_group) >= 10:
                    break 
            
            if media_group:
                try:
                    await context.bot.send_media_group(
                        chat_id=update.effective_chat.id,
                        media=media_group
                    )
                    logger.info(f"Бот: успешно отправлена медиагруппа из {len(media_group)} мемов для запроса '{search_query}'.")
                except Exception as e_media_group:
                    logger.error(f"Бот: Не удалось отправить медиагруппу. Ошибка: {e_media_group}. Попытка отправить ссылки.", exc_info=True)
                    if links_if_media_group_fails:
                        await update.message.reply_text(
                            f"Не смог отправить мемы как галерею, но вот ссылки на них по запросу \"{search_query}\":\n" + 
                            "\n".join(links_if_media_group_fails)
                        )
                    else:
                        await update.message.reply_text("Произошла ошибка при отправке мемов.")
            elif not results: # Если results был, но после фильтрации media_group оказался пуст
                 await update.message.reply_text(f"Мемы по запросу \"{search_query}\" найдены, но не удалось получить изображения.")

        else: 
            improved_query = data.get("improved_query")
            if improved_query and improved_query != search_query:
                 await update.message.reply_text(f"Мемы по запросу \"{search_query}\" не найдены. "
                                                 f"Пробовал уточнить до \"{improved_query}\", но тоже ничего нет :(")
            else:
                await update.message.reply_text(f"Мемы по запросу \"{search_query}\" не найдены :(")

    except httpx.HTTPStatusError as e:
        # --- УДАЛЕНО УДАЛЕНИЕ СООБЩЕНИЯ О ПОИСКЕ В БЛОКАХ EXCEPT ---
        # if searching_message_object: 
        #     try: await searching_message_object.delete()
        #     except Exception: pass
        logger.error(f"Бот: Ошибка API Мемотеки при поиске: {e.response.status_code} - {e.response.text}", exc_info=True)
        await update.message.reply_text(f"Возникла ошибка при обращении к базе мемов ({e.response.status_code}). Попробуйте немного позже.")
    except httpx.RequestError as e:
        # --- УДАЛЕНО УДАЛЕНИЕ СООБЩЕНИЯ О ПОИСКЕ В БЛОКАХ EXCEPT ---
        # if searching_message_object: 
        #     try: await searching_message_object.delete()
        #     except Exception: pass
        request_info = f"{e.request.method} {e.request.url if e.request else 'N/A'}"
        logger.error(f"Бот: Сетевая ошибка при запросе к Мемотеке. Запрос: {request_info}", exc_info=True)
        await update.message.reply_text("Проблема с сетью при поиске мема в Мемотеке. Пожалуйста, попробуйте позже.")
    except Exception as e:
        # --- УДАЛЕНО УДАЛЕНИЕ СООБЩЕНИЯ О ПОИСКЕ В БЛОКАХ EXCEPT ---
        # if searching_message_object: 
        #     try: await searching_message_object.delete()
        #     except Exception: pass
        logger.error(f"Бот: Непредвиденная ошибка при поиске мема в Мемотеке: {e}", exc_info=True)
        await update.message.reply_text("Ой, что-то пошло не так при поиске мема. Попробуйте еще раз.")