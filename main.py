import sys
from datetime import datetime, timezone

from loguru import logger

from config import (FEEDS, CHANNEL_ID, MAX_ARTICLES_PER_RUN, MAX_ARTICLES_PER_FEED,
                    CANDIDATES_PER_RUN, DIGEST_HOURS_UTC, DIGEST_TITLE)
from database import init_db, is_known, add_news, get_state, set_state
from feeds import get_entries, entry_image
from extractor import get_article
from ai import process_article
from selector import select_best
from digest import build_digest
from pexels import search_photo
from image_gen import generate_image_url
from images import fetch_image
from publisher import post_news

logger.remove()
logger.add(sys.stderr, format="<green>{time}</green> <level>{level}</level> {message}", colorize=True)


def _publish_entry(category, source_name, entry):
    """Проводит одну статью через весь пайплайн: текст -> ИИ -> картинка ->
    публикация. Возвращает True, если статья реально опубликована."""
    url = entry.get('link', '')
    if not url or is_known(url):
        return False

    text, og_image = get_article(url)
    if not text:
        logger.warning(f"Пропуск (не удалось извлечь текст): {url}")
        return False

    title_ru, summary_ru, image_prompt, _tags_ru = process_article(entry.get('title', ''), text)
    if not summary_ru:
        logger.warning(f"Пропуск (ИИ не ответил): {url}")
        return False

    # Цепочка источников картинки, от самого достоверного к самому
    # крайнему: настоящая картинка из RSS -> настоящая картинка со
    # страницы статьи (og:image) -> релевантное стоковое фото по
    # теме -> и только если вообще ничего не нашли — рисуем сами.
    # Скачиваем выбранную картинку сами и отдаём байты в Telegram
    # (см. publisher.post_news): если дать Telegram ссылку, он сам
    # полезет по ней и срежет посты на медленных сервисах вроде
    # Pollinations (генерация занимает минуту).
    candidates = [
        entry_image(entry),
        og_image,
        search_photo(image_prompt),
        generate_image_url(image_prompt),
    ]
    image_bytes, image_url = fetch_image(candidates)
    if not image_bytes:
        logger.warning(f"Пропуск (не удалось получить картинку): {url}")
        return False

    # Добавляем URL в «уже опубликованные» только ПОСЛЕ подтверждённой
    # отправки: иначе упавшая/отклонённая публикация помечала статью как
    # вышедшую и она навсегда терялась (никогда не ретраилась). Цена такого
    # порядка — редкий дубль, если процесс упадёт между отправкой и меткой,
    # но дубль заметно лучше, чем тихая потеря новости.
    # Модельные теги не публикуем — только тег категории (надёжный, стабильный,
    # из FEEDS). Сгенерированные free-LLM теги нестабильны (то регистр, то
    # мусор) и превращаются в визуальный шум без пользы для навигации.
    # Категория уже попадает в caption через category= в post_news.
    if post_news(CHANNEL_ID, title_ru, summary_ru, url, image_bytes,
                 category=category):
        add_news(category, title_ru, summary_ru, url, image_url, entry.get('published', ''))
        logger.info(f"Опубликовано [{category}] {title_ru}")
        return True

    logger.error(f"Не удалось отправить в канал: {url}")
    return False


def _is_digest_hour(utc_hour):
    """True, если текущий час (UTC) — дайджестовый. Вынесено в функцию ради
    простого теста и чёткого места, где расписание дайджестов живёт."""
    return utc_hour in DIGEST_HOURS_UTC


def _publish_digest():
    """Публикует один дайджест «Главное в мире за день». Возвращает True,
    только если дайджест реально ушёл в канал. Обложка — сток по общей теме,
    без неё пост уходит текстом (не теряем сводку из-за картинки)."""
    bullets = build_digest()
    if not bullets:
        logger.warning("Дайджест не собран — переходим к обычному посту")
        return False

    summary = '\n'.join('• ' + b for b in bullets)

    # У дайджеста нет одной «статьи», поэтому и картинка не из RSS: ищем сток
    # по общей теме мира/новостей, запасной вариант — генерация. Цепочка та же,
    # что в обычном посте, но без entry/og-картинок.
    cover_prompt = (
        "world news daily digest cover, globe, newspapers front page with "
        "headlines, breaking news, photorealistic, no text, no watermark"
    )
    image_bytes, _image_url = fetch_image([
        search_photo(cover_prompt),
        generate_image_url(cover_prompt),
    ])

    # url='' — у сводки нет одной ссылки; publisher умеет не рисовать ссылку.
    if post_news(CHANNEL_ID, DIGEST_TITLE, summary, '', image_bytes, category='Мир'):
        logger.info(f"Опубликован дайджест [{CHANNEL_ID}]: {len(bullets)} тем")
        return True

    logger.error("Не удалось отправить дайджест в канал")
    return False


def run():
    init_db()
    posted = 0

    # Дайджестовый прогон — своя ветка: вместо выбора статьи из техно-лент
    # публикуем сводку мировых новостей и выходим. Курсор round-robin не трогаем
    # (дайджест не тратит очередь источников). Если сводка не собралась —
    # не пропускаем прогон впустую, а выходим на обычный пост ниже.
    if _is_digest_hour(datetime.now(timezone.utc).hour):
        if _publish_digest():
            posted = 1
            logger.info(f"Прогон завершён, опубликовано новостей: {posted}")
            return
        logger.info("Дайджест не вышел, публикую обычную новость")

    # Плоский список источников вместе с их категорией — обходим его по кругу.
    # Раньше порядок словаря FEEDS + глобальный лимит означали, что первый
    # же источник (Habr) съедал всю квоту прогона, а остальные не трогались.
    all_sources = [
        (category, source_name, feed_url)
        for category, sources in FEEDS.items()
        for source_name, feed_url in sources
    ]
    n_sources = len(all_sources)
    if n_sources == 0:
        logger.warning("FEEDS пуст, нечего публиковать")
        return

    # Точка входа этого прогона — источник, следующий за последним
    # использованным (см. set_state в конце). По умолчанию — первый.
    start_index = get_state('feed_cursor', default=0) % n_sources

    # ---- Отбор самой интересной статьи ---------------------------------
    # Собираем по одному неопубликованному кандидату (заголовок + сниппет
    # из RSS, без извлечения полного текста) с первых CANDIDATES_PER_RUN
    # источников и одним запросом модели выбираем самого интересного.
    # Публикуем победителя; если его не удалось провести через пайплайн —
    # фолбэк на обычный round-robin внизу.
    candidates = []
    for step in range(CANDIDATES_PER_RUN):
        category, source_name, feed_url = all_sources[(start_index + step) % n_sources]
        for entry in get_entries(feed_url, MAX_ARTICLES_PER_FEED):
            url = entry.get('link', '')
            if url and not is_known(url):
                candidates.append((url, entry, category, source_name))
                break

    if candidates:
        pick_list = [
            (url, entry.get('title', ''), entry.get('summary', ''))
            for url, entry, _, _ in candidates
        ]
        best_url = select_best(pick_list)
        if best_url:
            for url, entry, category, source_name in candidates:
                if url == best_url:
                    if _publish_entry(category, source_name, entry):
                        posted = 1
                    break
            if posted:
                # Следующий прогон начнёт после последнего просмотренного
                # источника — обходили CANDIDATES_PER_RUN штук с start_index.
                set_state('feed_cursor', (start_index + CANDIDATES_PER_RUN) % n_sources)
                logger.info(f"Прогон завершён, опубликовано новостей: {posted}")
                return

    visited = 0
    idx = start_index
    while posted < MAX_ARTICLES_PER_RUN and visited < n_sources:
        category, source_name, feed_url = all_sources[idx]

        entries = get_entries(feed_url, MAX_ARTICLES_PER_FEED)
        logger.info(f"[{category}] {source_name}: {len(entries)} записей")

        for entry in entries:
            if posted >= MAX_ARTICLES_PER_RUN:
                break

            if _publish_entry(category, source_name, entry):
                posted += 1

        idx = (idx + 1) % n_sources
        visited += 1

    # Следующий прогон начнёт с источника, идущего за последним просмотренным:
    # так каждый прогон стартует с нового места, а не вечно с Habr.
    # Если же прогон обошёл весь круг, а не остановился по лимиту (idx снова
    # равен start_index, курсор «запарковался» бы) — всё равно сдвигаемся на
    # один вперёд, чтобы проголодавшийся источник не получал все прогоны.
    cursor = idx if visited < n_sources else (start_index + 1) % n_sources
    set_state('feed_cursor', cursor)

    logger.info(f"Прогон завершён, опубликовано новостей: {posted}")


if __name__ == '__main__':
    run()
