import sys

from loguru import logger

from config import FEEDS, CHANNEL_ID, MAX_ARTICLES_PER_RUN, MAX_ARTICLES_PER_FEED
from database import init_db, is_known, add_news
from feeds import get_entries, entry_image
from extractor import get_article_text
from ai import process_article
from image_gen import generate_image_url
from publisher import post_news

logger.remove()
logger.add(sys.stderr, format="<green>{time}</green> <level>{level}</level> {message}", colorize=True)


def run():
    init_db()
    posted = 0

    for category, sources in FEEDS.items():
        if posted >= MAX_ARTICLES_PER_RUN:
            break

        for source_name, feed_url in sources:
            if posted >= MAX_ARTICLES_PER_RUN:
                break

            entries = get_entries(feed_url, MAX_ARTICLES_PER_FEED)
            logger.info(f"[{category}] {source_name}: {len(entries)} записей")

            for entry in entries:
                if posted >= MAX_ARTICLES_PER_RUN:
                    break

                url = entry.get('link', '')
                if not url or is_known(url):
                    continue

                text = get_article_text(url)
                if not text:
                    logger.warning(f"Пропуск (не удалось извлечь текст): {url}")
                    continue

                title_ru, summary_ru = process_article(entry.get('title', ''), text)
                if not summary_ru:
                    logger.warning(f"Пропуск (ИИ не ответил): {url}")
                    continue

                # Картинка из RSS есть далеко не всегда (проверено вживую: у Habr
                # и TechCrunch пусто) — тогда генерируем свою по заголовку.
                image_url = entry_image(entry) or generate_image_url(title_ru)
                published_at = entry.get('published', '')

                if not add_news(category, title_ru, summary_ru, url, image_url, published_at):
                    # Другой источник в этом же прогоне уже добавил тот же url
                    continue

                if post_news(CHANNEL_ID, title_ru, summary_ru, url, image_url):
                    posted += 1
                    logger.info(f"Опубликовано [{category}] {title_ru}")
                else:
                    logger.error(f"Не удалось отправить в канал: {url}")

    logger.info(f"Прогон завершён, опубликовано новостей: {posted}")


if __name__ == '__main__':
    run()
