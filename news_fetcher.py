import aiohttp
from config import NEWSAPI_KEY

CATEGORIES = {
    'наука': 'science',
    'техника': 'technology',
    'мировые новости': 'general',
    'игры': 'game',
    'роботы': 'robots',
    'искуственный интеллект': 'artificial intelligence'
}

async def get_news(session, category):
    """Асинхронное получение новостей"""
    url = f'https://newsapi.org/v2/top-headlines?category={CATEGORIES[category]}&apiKey={NEWSAPI_KEY}'
    try:
        async with session.get(url) as response:
            data = await response.json()
            return data.get('articles', [])
    except Exception as e:
        logger.error(f"Ошибка запроса новостей: {e}")
        return []