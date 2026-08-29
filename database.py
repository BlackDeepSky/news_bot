import json
import os
import tempfile
from pathlib import Path

# Память бота между запусками теперь живёт в двух текстовых файлах, а не в
# бинарнике SQLite. Почему так:
#   * рантайму нужны только два факта — «этот URL уже постили» и «курсор
#     round-robin по источникам», никакой транзакционной мощности SQLite
#     здесь не используется;
#   * бинарник news.db в git порождал коммит на каждый пост (~2 КБ блоба),
#     служебные коммиты «Update news database» и бинарные конфликты при
#     merge — текстовая история этих проблем не имеет и diff'ится как обычный
#     код (git остаётся единственным хранилищем памяти бота на эфемерном
#     раннере GitHub Actions).
DATA_DIR = Path('data')
URLS_FILE = DATA_DIR / 'seen_urls.txt'
STATE_FILE = DATA_DIR / 'state.json'

# Набор URL держим в памяти на время прогона, файл читаем один раз в init_db.
_seen_urls = set()


def _load_seen_urls():
    if not URLS_FILE.exists():
        return set()
    return {line.strip() for line in URLS_FILE.read_text(encoding='utf-8').splitlines() if line.strip()}


def _load_state():
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state):
    # Пишем атомарно: сначала во временный файл в той же директории, потом
    # rename поверх настоящего. Иначе падение процесса посреди write_text()
    # обрезало бы state.json до хвоста, а read без атомарности — риск гонки при
    # параллельных прогонах (cron + ручной запуск).
    fd, tmp = tempfile.mkstemp(dir=DATA_DIR, prefix='.state.')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, STATE_FILE)
    except BaseException:
        os.unlink(tmp)
        raise


def init_db():
    """Готовит файлы памяти бота: директорию, список URL и файл состояния."""
    DATA_DIR.mkdir(exist_ok=True)
    global _seen_urls
    _seen_urls = _load_seen_urls()
    if not STATE_FILE.exists():
        _save_state({})


def get_state(key, default=0):
    """Читает сервисное значение (например, курсор round-robin по источники)."""
    return _load_state().get(key, default)


def set_state(key, value):
    """Пишет или обновляет сервисное значение."""
    state = _load_state()
    state[key] = value
    _save_state(state)


def is_known(url):
    """Проверка, публиковали ли уже эту статью."""
    return url in _seen_urls


def add_news(category, title, summary, url, image_url, published_at):
    """Отмечает статью как опубликованную. False, если url уже был (не
    плодим дубликатов). Заголовок и остальные поля не храним: для рантайма
    нужен только URL, архив постов — сам канал в Telegram."""
    if url in _seen_urls:
        return False
    with URLS_FILE.open('a', encoding='utf-8') as f:
        f.write(url + '\n')
    _seen_urls.add(url)
    return True
