import aiohttp
from config import NEWSAPI_KEY
from loguru import logger

# Стандартные категории NewsAPI
STANDARD_CATEGORIES = {
    'наука': 'science',
    'техника': 'technology',
    'мировые новости': 'general',
    'игры': 'game'
}

# Нестандартные категории и их ключевые слова
CUSTOM_CATEGORIES = {
    'роботы': 'robots',
    'искуственный интеллект': 'artificial intelligence OR AI'
}

async def get_news(session, category):
    """Асинхронное получение новостей по категории или ключевым словам"""
    base_url = "https://newsapi.org/v2/"
    
    if category in STANDARD_CATEGORIES:
        # Используем /top-headlines для стандартных категорий
        url = f"{base_url}top-headlines?category={STANDARD_CATEGORIES[category]}&apiKey={NEWSAPI_KEY}"
    else:
        # Используем /everything для нестандартных категорий
        query = CUSTOM_CATEGORIES.get(category, category)  # Поиск по ключевым словам
        url = f"{base_url}everything?q={query}&language=en&sortBy=publishedAt&apiKey={NEWSAPI_KEY}"
    
    try:
        async with session.get(url) as response:
            response.raise_for_status()  # Проверка на ошибки HTTP
            data = await response.json()
            return data.get('articles', [])
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка запроса к API: {e}")
        return []

def get_all_categories():
    """Возвращает все категории (стандартные и нестандартные)"""
    return list(STANDARD_CATEGORIES.keys()) + list(CUSTOM_CATEGORIES.keys())