from decouple import config

BOT_TOKEN = config('BOT_TOKEN')
CHANNEL_ID = config('CHANNEL_ID')
OPENROUTER_API_KEY = config('OPENROUTER_API_KEY')
PEXELS_API_KEY = config('PEXELS_API_KEY')

# Бесплатная модель на OpenRouter. Список бесплатных моделей меняется —
# актуальный смотреть на https://openrouter.ai/models?max_price=0
# gemma-4-31b-it временно недоступна (общий бесплатный пул Google AI Studio
# был перегружен на момент проверки, отдавал 429 всем без исключения) —
# nemotron прошла живую проверку.
OPENROUTER_MODEL = 'nvidia/nemotron-3-super-120b-a12b:free'

# Лимит на прогон: 16 прогонов (см. cron в workflow) x 1 пост = до 16
# постов/сутки: 14 обычных + 2 дайджеста «Мир» (DIGEST_HOURS_UTC), равномерно
# в дневные часы. Round-robin по источникам (main.py) распределяет квоту по
# кругу, так что за день в канал попадают разные источники, а не всегда
# первый Habr.
#
# MAX_ARTICLES_PER_RUN ограничивает и дневную квоту OpenRouter: без оплаченных
# кредитов она обычно около 50/сутки (см. свой dashboard после регистрации).
# Расход на день: обычный пост = 2 запроса (selector + process_article),
# дайджест = 1 запрос (digest). 14x2 + 2x1 = 30 запросов/сутки — в запасе.
MAX_ARTICLES_PER_RUN = 1
MAX_ARTICLES_PER_FEED = 2

# Сколько статей-кандидатов (заголовок + сниппет из RSS, без извлечения полного
# текста) собрать для выбора самой интересной одним LLM-запросом. Отбор
# добавляет 1 вызов OpenRouter на пост (см. selector.main), при 14x1
# обычных постах это ~28 запросов + 2 на дайджесты = ~30 — всё ещё в запасе
# квоты ~50. Кандидатов подняли c 3 до 5: модель видит больше материала и
# выбирает осмысленнее (число запросов на выбор не меняется — растёт только
# длина промпта, см. main.py «сбор кандидатов по кругу»).
CANDIDATES_PER_RUN = 5

# Минимальная длина (в символах) RSS-сниппета, при которой он считается
# «достаточным» материалом для отбора. Если сниппет короче — main.py
# догружает кандидату description ленты (расширенный текст записи), чтобы
# модель выбирала не «вслепую» по пустому заголовку.
CANDIDATE_MIN_SNIPPET = 80

# ---- Дайджест «Главное в мире за день» ---------------------------------
# Часы (UTC), когда вместо обычного поста публикуется сводка мировых новостей:
# 05:00 = 08:00 и 19:00 = 22:00 по Минску (утро и вечер). Оба часа входят в
# cron workflow ('0 5-20 * * *'), так что расписание не меняется — main.py
# сам определяет, какой прогон дайджестовый.
DIGEST_HOURS_UTC = (5, 19)
DIGEST_TITLE = 'Главное в мире за день'
# Сколько тем из РАЗНЫХ областей мира модель должна выбрать в сводку и минимум,
# при котором дайджест считается собранным (меньше — фолбэк на обычный пост,
# чтобы в канал не уходил обрубок).
DIGEST_TOPICS = 5
DIGEST_MIN_TOPICS = 3
# Потолок кандидатов на дайджест и сколько записей берём с каждой ленты.
DIGEST_CANDIDATES = 10
DIGEST_FEED_LIMIT = 4

# Мировые ленты для дайджеста: общая повестка дня (политика, экономика,
# технологии, наука, общество). Русскоязычным источником здесь не ограничены —
# текст лент (преимущественно английский) дайджест переводит через LLM, см.
# digest.build_digest. Проверялось, что ленты отдают RSS без ключа.
WORLD_FEEDS = [
    ('BBC World', 'https://feeds.bbci.co.uk/news/world/rss.xml'),
    ('The Guardian World', 'https://www.theguardian.com/world/rss'),
    ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml'),
    ('CNN World', 'http://rss.cnn.com/rss/edition_world.rss'),
]

# Потолок размера скачиваемой картинки. Равно лимиту sendPhoto в Telegram
# (10 МБ): больше всё равно не уйдёт, а без лимита вредоносный URL из RSS мог
# бы исчерпать память раннера. См. images.download_image.
MAX_IMAGE_BYTES = 10 * 1024 * 1024

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
