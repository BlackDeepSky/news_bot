import sqlite3

from config import DB_PATH


def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY,
            category TEXT,
            title TEXT,
            summary TEXT,
            url TEXT UNIQUE,
            image_url TEXT,
            published_at TEXT
        )
    ''')
    conn.commit()
    conn.close()


def is_known(url):
    """Проверка, публиковали ли уже эту статью"""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute('SELECT 1 FROM news WHERE url = ?', (url,)).fetchone()
    conn.close()
    return row is not None


def add_news(category, title, summary, url, image_url, published_at):
    """Добавление новости в базу. False, если url уже есть (UNIQUE)."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            '''INSERT INTO news (category, title, summary, url, image_url, published_at)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (category, title, summary, url, image_url, published_at),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
