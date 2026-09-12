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

# Лимит на прогон: 4 прогона/сутки (см. cron-job.org: 05,10,15,19 UTC) x 1 пост =
# до 4 постов/сутки: 3 обычных + 1 дайджест «Мир» (DIGEST_HOURS_UTC), равномерно
# в дневные часы. Round-robin по источникам (main.py) распределяет квоту по
# кругу, так что за день в канал попадают разные источники, а не всегда
# первый Habr.
#
# MAX_ARTICLES_PER_RUN ограничивает и дневную квоту OpenRouter: без оплаченных
# кредитов она обычно около 50/сутки (см. свой dashboard после регистрации).
# Расход на день: обычный пост = 2 запроса (selector + process_article),
# дайджест = 1 запрос (digest). 3x2 + 1 = 7 запросов/сутки — в запасе.
MAX_ARTICLES_PER_RUN = 1
MAX_ARTICLES_PER_FEED = 2

# Сколько статей-кандидатов (заголовок + сниппет из RSS, без извлечения полного
# текста) собрать для выбора самой интересной одним LLM-запросом. Отбор
# добавляет 1 вызов OpenRouter на пост (см. selector.main): при 3 обычных
# постах в день это 3 запроса + 1 на дайджест = ~7 — всё ещё в запасе квоты ~50.
# Кандидатов подняли c 3 до 5: модель видит больше материала и
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
# один дайджест в сутки, 05:00 UTC = 08:00 по Минску. Раньше был и вечерний
# (17:00 UTC = 20:00 Минск), но его убрали — вечерний слот стал обычным постом.
# Час входит в расписание cron-job.org (05,10,15,19 UTC) — main.py сам
# определяет, какой прогон дайджестовый.
DIGEST_HOURS_UTC = (5,)
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

# Минимальная длина большей стороны картинки (px), при которой она считается
# достаточно детальной для публикации. Telegram при sendPhoto сжимает фото
# примерно до 1280px по длинной стороне — меньший исходник на экране канала
# превращается в размытый апскейл (ленты любят отдавать превью 500px и меньше).
# Проверяем реальные пиксели после скачивания, а не байты: мелкий JPEG легко
# укладывается в лимит размера, но в канал он всё равно не годится.
# См. images.fetch_image.
MIN_IMAGE_LONG_SIDE = 1080

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
