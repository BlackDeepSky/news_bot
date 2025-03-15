import asyncio
import sys
import sqlite3
import aiohttp
from aiogram import Bot, Dispatcher, types, executor
from loguru import logger

from config import BOT_TOKEN, ADMIN_ID, CHANNEL_ID
from news_fetcher import CATEGORIES, get_news
from database import init_db, add_news, get_news_by_url
from translator import load_translation_model, translate_text
from summarizer import load_models, get_article_text, summarize_text

# Настройка логирования
logger.remove()
logger.add(sys.stderr, format="<green>{time}</green> <level>{level}</level> {message}", colorize=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Загрузка моделей при старте
load_models()
load_translation_model()

def sanitize_markdown(text):
    """Очистка текста от проблемных Markdown-символов"""
    if not text:
        return text
    for char in ['*', '_', '[', ']', '`']:
        text = text.replace(char, f'\\{char}')
    return text

def truncate_message(title, author, summary, max_length=1024):
    """Обрезаем сообщение до указанной длины, сохраняя заголовок и автора"""
    base = f"**{title}**\n\nАвтор: **{author}**\n\n"
    remaining_length = max_length - len(base)
    if remaining_length <= 0:
        base = base[:max_length - 3] + '...'
        return base
    truncated_summary = summary[:remaining_length - 3] + '...' if len(summary) > remaining_length else summary
    if len(summary) > remaining_length:
        logger.warning(f"Суммаризация обрезана до {remaining_length} символов.")
    return base + truncated_summary

async def fetch_and_send_news():
    """Асинхронная обработка новостей"""
    async with aiohttp.ClientSession() as session:
        while True:
            logger.info("Начинаем новый цикл поиска новостей...")
            for category in CATEGORIES:
                try:
                    articles = await get_news(session, category)
                    logger.info(f"Найдено {len(articles)} новостей в категории '{category}'")
                    
                    # Перебираем статьи в категории, пока не найдем новую
                    for article in articles:
                        # Пропуск существующих новостей
                        if get_news_by_url(article['url']):
                            logger.debug(f"Новость уже существует: {article['url']}")
                            continue  # Переходим к следующей статье
                            
                        # Обработка новой статьи
                        title = translate_text(article['title'])
                        author = article.get('author', 'Не указан')
                        url = article['url']
                        image_url = article.get('urlToImage', '')
                        published_at = article.get('publishedAt', '')
                        
                        article_text = await get_article_text(url)
                        summary = summarize_text(article_text)
                        summary_ru = translate_text(summary)
                
                        if add_news(category, title, author, summary_ru, url, image_url, published_at):  # Сохраняем переведенную версию
                            news = get_news_by_url(url)
                            news_id = news[0]
                            
                            message = truncate_message(title, author, summary_ru, max_length=1024 if image_url else 4096)
                            keyboard = types.InlineKeyboardMarkup()
                            keyboard.add(types.InlineKeyboardButton("Отправить", callback_data=f"send_{news_id}"))
                            
                            try:
                                if image_url and isinstance(image_url, str) and image_url.startswith(('http://', 'https://')):
                                    await bot.send_photo(ADMIN_ID, image_url, caption=message, parse_mode='Markdown', reply_markup=keyboard)
                                else:
                                    await bot.send_message(ADMIN_ID, message, parse_mode='Markdown', reply_markup=keyboard)
                                logger.info(f"Новость из категории '{category}' отправлена администратору (ID: {news_id})")
                                break  # Переходим к следующей категории после успешной отправки
                            except Exception as e:
                                logger.error(f"Ошибка отправки новости: {e}")
                except Exception as e:
                    logger.error(f"Ошибка обработки категории '{category}': {e}")
            
            # Пауза между циклами (2 часа)
            logger.info("Ожидание следующего цикла (2 часа)...")
            await asyncio.sleep(7200)  # 2 часа = 7200 секунд

@dp.callback_query_handler(lambda c: c.data.startswith('send_'))
async def process_callback_send(callback_query: types.CallbackQuery):
    """Обработка нажатия кнопки 'Отправить'"""
    news_id = int(callback_query.data.split('_')[1])
    with sqlite3.connect('news.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM news WHERE id = ?', (news_id,))
        news = cursor.fetchone()
    
    if news:
        category, title, author, summary_ru, url, image_url, published_at = news[1:]  # Уже переведенная суммаризация
        summary_ru = sanitize_markdown(summary_ru)
        message = truncate_message(title, author, summary_ru, max_length=1024 if image_url else 4096)
        try:
            if image_url and isinstance(image_url, str) and image_url.startswith(('http://', 'https://')):
                await bot.send_photo(CHANNEL_ID, image_url, caption=message, parse_mode='Markdown')
            else:
                await bot.send_message(CHANNEL_ID, message, parse_mode='Markdown')
            await bot.answer_callback_query(callback_query.id, "Новость отправлена в канал")
            logger.info(f"Новость отправлена в канал: {title} (ID: {news_id})")
        except Exception as e:
            await bot.answer_callback_query(callback_query.id, "Ошибка при отправке")
            logger.error(f"Ошибка при отправке в канал: {e}")
    else:
        await bot.answer_callback_query(callback_query.id, "Новость не найдена")
        logger.warning(f"Новость с ID {news_id} не найдена в базе")

if __name__ == '__main__':
    init_db()
    logger.info("Бот запущен")
    loop = asyncio.get_event_loop()
    loop.create_task(fetch_and_send_news())
    executor.start_polling(dp, skip_updates=True)