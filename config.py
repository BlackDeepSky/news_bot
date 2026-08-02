from decouple import config

BOT_TOKEN = config('BOT_TOKEN')
CHANNEL_ID = config('CHANNEL_ID')
OPENROUTER_API_KEY = config('OPENROUTER_API_KEY')

# Бесплатная модель на OpenRouter. Список бесплатных моделей меняется —
# актуальный смотреть на https://openrouter.ai/models?max_price=0
OPENROUTER_MODEL = 'google/gemma-4-31b-it:free'

DB_PATH = 'news.db'

# OpenRouter без оплаченных кредитов даёт ограниченную дневную квоту запросов
# (обычно около 50/сутки — see dashboard после регистрации). Эти два лимита
# держат суммарный расход в пределах любой разумной дневной квоты:
# при cron раз в 3 часа (8 прогонов/сутки) и 6 новостях за прогон — 48 запросов/сутки.
MAX_ARTICLES_PER_RUN = 6
MAX_ARTICLES_PER_FEED = 2

# category -> [(человекочитаемое имя источника, URL RSS-ленты), ...]
FEEDS = {
    'ИИ': [
        ('Habr: Искусственный интеллект', 'https://habr.com/ru/rss/hubs/artificial_intelligence/articles/all/?fl=ru'),
        ('VentureBeat AI', 'https://venturebeat.com/category/ai/feed/'),
        ('MIT News: AI', 'https://news.mit.edu/rss/topic/artificial-intelligence2'),
        ('OpenAI News', 'https://openai.com/news/rss.xml'),
        ('DeepMind Blog', 'https://deepmind.google/blog/rss.xml'),
    ],
    'Робототехника': [
        ('IEEE Spectrum: Robotics', 'https://spectrum.ieee.org/feeds/topic/robotics.rss'),
        ('The Robot Report', 'https://www.therobotreport.com/feed/'),
    ],
    'Наука': [
        ('Habr: Научно-популярное', 'https://habr.com/ru/rss/hubs/popular_science/articles/all/?fl=ru'),
        ('ScienceDaily', 'https://www.sciencedaily.com/rss/all.xml'),
        ('Phys.org', 'https://phys.org/rss-feed/'),
        ('Nature', 'https://www.nature.com/nature.rss'),
    ],
    'Программирование': [
        ('Habr: Программирование', 'https://habr.com/ru/rss/hubs/programming/articles/all/?fl=ru'),
        ('Dev.to', 'https://dev.to/feed'),
        ('InfoQ', 'https://feed.infoq.com/'),
        ('GitHub Blog', 'https://github.blog/feed/'),
    ],
    'ИТ': [
        ('TechCrunch', 'https://techcrunch.com/feed/'),
        ('Ars Technica', 'https://feeds.arstechnica.com/arstechnica/index'),
        ('The Verge', 'https://www.theverge.com/rss/index.xml'),
        ('Wired', 'https://www.wired.com/feed/rss'),
        ('MIT Technology Review', 'https://www.technologyreview.com/feed/'),
        ('Hacker News', 'https://hnrss.org/frontpage'),
        ('Stack Overflow Blog', 'https://stackoverflow.blog/feed/'),
    ],
}
