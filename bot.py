import asyncio
import sys
import sqlite3
import aiohttp
from aiogram import Bot, Dispatcher, types, executor
from loguru import logger

from config import BOT_TOKEN, ADMIN_ID, CHANNEL_ID
from news_fetcher import get_news, get_all_categories
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

def truncate_message(summary, max_length=1024):
    """Обрезаем сообщение до указанной длины"""
    if len(summary) > max_length:
        summary = summary[:max_length - 3] + '...'
        logger.warning(f"Суммаризация обрезана до {max_length} символов.")
    return summary

async def fetch_and_send_news():
    """Асинхронная обработка новостей"""
    async with aiohttp.ClientSession() as session:
        while True:
            logger.info("Начинаем новый цикл поиска новостей...")
            
            # Получаем все категории (стандартные и нестандартные)
            categories = get_all_categories()
            
            for category in categories:
                try:
                    articles = await get_news(session, category)
                    logger.info(f"Найдено {len(articles)} новостей в категории '{category}'")
                    articles = articles[:2]
                    await process_articles(category, articles)
                except Exception as e:
                    logger.error(f"Ошибка обработки категории '{category}': {e}")
            
            # Пауза между циклами (2 часа)
            logger.info("Ожидание следующего цикла (2 часа)...")
            await asyncio.sleep(7200)

async def process_articles(category, articles):
    """Обработка статей и отправка администратору"""
    sent_count = 0  # Счетчик отправленных новостей
    
    for article in articles:
        # Пропуск существующих новостей
        if get_news_by_url(article['url']):
            logger.debug(f"Новость уже существует: {article['url']}")
            continue
        
        # Обработка
        title = translate_text(article['title'])
        url = article['url']
        image_url = article.get('urlToImage', '')
        published_at = article.get('publishedAt', '')
        
        article_text = await get_article_text(url)
        summary = summarize_text(article_text)
        summary_ru = translate_text(summary)
        
        if add_news(category, title, "", summary_ru, url, image_url, published_at):  # Сохраняем переведенную версию
            news = get_news_by_url(url)
            news_id = news[0]
            
            # Исправленный вызов truncate_message
            message = truncate_message(summary_ru, max_length=1024 if image_url else 4096)
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("Отправить", callback_data=f"send_{news_id}"))
            
            try:
                if image_url and isinstance(image_url, str) and image_url.startswith(('http://', 'https://')):
                    await bot.send_photo(ADMIN_ID, image_url, caption=message, parse_mode='Markdown', reply_markup=keyboard)
                else:
                    await bot.send_message(ADMIN_ID, message, parse_mode='Markdown', reply_markup=keyboard)
                logger.info(f"Новость из категории '{category}' отправлена администратору (ID: {news_id})")
                sent_count += 1
                
                # Прерываем цикл, если отправлено 3 новости
                if sent_count >= 3:
                    break
            except Exception as e:
                logger.error(f"Ошибка отправки новости: {e}")

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
        
        # Исправленный вызов truncate_message
        message = truncate_message(summary_ru, max_length=1024 if image_url else 4096)
        
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