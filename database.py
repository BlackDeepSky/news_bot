import sqlite3

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect('news.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY,
            category TEXT,
            title TEXT,
            author TEXT,
            description TEXT,
            url TEXT UNIQUE,
            image_url TEXT,
            published_at TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS url_index ON news(url)')
    conn.commit()
    conn.close()

def add_news(category, title, author, description, url, image_url, published_at):
    """Добавление новости в базу"""
    conn = sqlite3.connect('news.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO news (category, title, author, description, url, image_url, published_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (category, title, author, description, url, image_url, published_at))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Новость уже существует
    finally:
        conn.close()

def get_news_by_url(url):
    """Получение новости по URL"""
    conn = sqlite3.connect('news.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM news WHERE url = ?', (url,))
    news = cursor.fetchone()
    conn.close()
    return news