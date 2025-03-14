import requests
from config import NEWSAPI_KEY

CATEGORIES = {
    'наука': 'science',
    'техника': 'technology',
    'мировые новости': 'general',
    'игры': 'game',
    'роботы': 'robots',
    'искуственный интеллект': 'artificial intelligence'
}

def get_news(category):
    """Получение новостей по категории"""
    url = f'https://newsapi.org/v2/top-headlines?category={CATEGORIES[category]}&apiKey={NEWSAPI_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['articles']
    return []