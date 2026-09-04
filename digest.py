import re
from loguru import logger

from config import (OPENROUTER_API_KEY, OPENROUTER_MODEL,
                    WORLD_FEEDS, DIGEST_TOPICS, DIGEST_MIN_TOPICS,
                    DIGEST_CANDIDATES, DIGEST_FEED_LIMIT)
from retry import post_with_retry
from feeds import get_entries
from database import is_known, add_news

API_URL = 'https://openrouter.ai/api/v1/chat/completions'

# Дайджест — один LLM-запрос на прогон, как и выбор статьи (2 вызова на
# обычный пост). Сводка строится сразу из сниппетов RSS без извлечения
# полного текста: для «что в мире главного» темы и 2 предложений хватает
# заголовка и краткого описания.
SYSTEM_PROMPT = (
    "Ты — редактор новостного Telegram-канала, собираешь ежедневную сводку "
    "мировых новостей. Строки ниже — мировые новости за сутки из разных "
    "международных лент. Отвечай ТОЛЬКО на русском языке: каждое слово "
    "должно быть русским, без единого слова на английском или любом другом "
    "языке (кроме имён собственных и названий стран/компаний)."
)

DIGEST_PROMPT = (
    "Ниже список мировых новостей с номером, заголовком и кратким описанием:\n\n"
    "{list}\n\n"
    "Выбери " + str(DIGEST_TOPICS) + " самых важных тем дня из РАЗНЫХ областей "
    "(политика, экономика, технологии, наука, общество, культура) — не бери "
    "несколько новостей об одном и том же.\n"
    "Верни ровно " + str(DIGEST_TOPICS) + " строк, по одной теме на строку.\n"
    "Формат каждой строки:\n"
    "Тема — краткая суть одним-двумя предложениями. Пиши только факты, без "
    "вводных фраз вроде «в статье говорится», без «по данным».\n"
    "Только сами строки: без нумерации, без маркеров списка, без вводных и "
    "заключительных фраз до и после списка.\n"
)

# Строка дайджеста должна содержать разделитель «Тема — суть» (используем и
# тире «—», и дефис: free-модель иногда пишет то одно, то другое). Строки без
# разделителя — мусор модели (рассуждения, нумерация) и в пост не идут.
_BULLET_DASH_RE = re.compile(r'[—\-]')


def _build_candidate_list(candidates):
    lines = []
    for i, (url, title, snippet) in enumerate(candidates, start=1):
        snippet = re.sub(r'\s+', ' ', (snippet or '')).strip()
        lines.append(f"{i}. {title} — {snippet}")
    return '\n'.join(lines)


def _parse_bullets(content, limit):
    """Достаёт из ответа модели строки «Тема — суть». Отбрасывает строки без
    тире (нумерацию, рассуждения model) и обрезает запредельно длинные."""
    result = []
    for raw in content.splitlines():
        line = re.sub(r'^\s*[\d#•*\-–.]+\s*', '', raw.strip())
        if not line or not _BULLET_DASH_RE.search(line):
            continue
        if len(line) > 400:
            line = line[:397] + '...'
        if line not in result:
            result.append(line)
        if len(result) >= limit:
            break
    return result


def build_digest():
    """Собирает дайджест «Главное в мире за день». Возвращает список строк
    «Тема — суть» (готовых для поста) или '', если не набралось достаточно тем.
    Успешно использованные URL кандидатов помечаются как опубликованные, чтобы
    утренний и вечерний дайджесты (и обычные посты, если ленты пересекутся)
    не повторяли одно и то же."""
    candidates = []
    seen_in_run = set()
    for source_name, feed_url in WORLD_FEEDS:
        for entry in get_entries(feed_url, DIGEST_FEED_LIMIT):
            url = entry.get('link', '')
            # Дубликаты возможны и внутри прогона: ленты иногда отдают
            # перепосты своих же записей или один URL в двух лентах. Иначе
            # один и тот же кандидат ушёл бы в список несколько раз и модель
            # получила бы «двойную» новость для выбора.
            if url and not is_known(url) and url not in seen_in_run:
                seen_in_run.add(url)
                candidates.append((url, entry))
            if len(candidates) >= DIGEST_CANDIDATES:
                break
        if len(candidates) >= DIGEST_CANDIDATES:
            break

    if not candidates:
        logger.warning("Дайджест: в мировых лентах нет новых кандидатов")
        return ''

    pick_list = [
        (url, entry.get('title', ''), entry.get('summary', ''))
        for url, entry in candidates
    ]

    payload = {
        'model': OPENROUTER_MODEL,
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': DIGEST_PROMPT.format(
                list=_build_candidate_list(pick_list))},
        ],
        'temperature': 0.5,
        'max_tokens': 800,
        # Reasoning-модели тратят max_tokens на рассуждения вслух и успевают
        # выдать пустоту — глушим, как в ai.py и selector.py.
        'reasoning': {'enabled': False},
    }
    headers = {'Authorization': f'Bearer {OPENROUTER_API_KEY}'}

    try:
        response = post_with_retry(API_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logger.error(f"Ошибка запроса к OpenRouter при сборке дайджеста: {e}")
        return ''

    bullets = _parse_bullets(content, DIGEST_TOPICS)
    if len(bullets) < DIGEST_MIN_TOPICS:
        logger.warning(
            f"Дайджест: модель дала мало тем ({len(bullets)}), пропускаю: {content[:200]!r}")
        return ''

    # Помечаем использованные кандидаты сразу и только после успешной сборки:
    # иначе упавший запрос «сжёг» бы свежие мировые новости ни за что.
    for url, entry in candidates:
        add_news('Мир', '', '', url, '', entry.get('published', ''))

    logger.info(f"Дайджест собран: {len(bullets)} тем")
    return bullets