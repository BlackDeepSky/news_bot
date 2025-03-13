import requests
from bs4 import BeautifulSoup
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
import nltk
import os
from loguru import logger
from newspaper import Article

# Указываем путь к nltk_data
nltk.data.path.append(os.path.expanduser('~/nltk_data'))

def ensure_nltk_resources():
    """Проверка и загрузка необходимых ресурсов NLTK"""
    resources = ['punkt', 'punkt_tab']
    for resource in resources:
        try:
            nltk.data.find(f'tokenizers/{resource}')
            logger.info(f"Ресурс {resource} уже доступен.")
        except LookupError:
            logger.info(f"Загружаем {resource} для NLTK...")
            try:
                nltk.download(resource, download_dir=os.path.expanduser('~/nltk_data'), raise_on_error=True)
                logger.info(f"{resource} успешно загружен.")
            except Exception as e:
                logger.error(f"Не удалось загрузить {resource}: {e}")
                raise

def get_article_text(url):
    """Получение текста статьи по URL с использованием newspaper3k"""
    try:
        # Используем newspaper3k для извлечения текста
        article = Article(url)
        # Настраиваем headers для обхода блокировок
        article.config.request_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        article.config.request_timeout = 10  # Устанавливаем timeout
        article.download()
        article.parse()
        article_text = article.text.strip()
        if article_text and len(article_text) > 100:
            logger.info(f"Успешно извлечен текст статьи через newspaper3k: {url}")
            return article_text

        # Fallback на requests + BeautifulSoup
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all(['p', 'div', 'article', 'section'])
        article_text = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True) and len(p.get_text(strip=True)) > 50)
        if article_text:
            logger.info(f"Извлечен текст через BeautifulSoup: {url}")
            return article_text
        return "Не удалось извлечь текст статьи."
    except Exception as e:
        logger.error(f"Ошибка при загрузке статьи {url}: {e}")
        return f"Ошибка при загрузке статьи: {e}"

def summarize_text(text, language='russian', sentences_count=3):
    """Суммаризация текста"""
    ensure_nltk_resources()
    try:
        parser = PlaintextParser.from_string(text, Tokenizer(language))
        summarizer = LsaSummarizer()
        summary = summarizer(parser.document, sentences_count)
        return ' '.join(str(sentence) for sentence in summary)
    except ImportError as e:
        logger.error(f"Ошибка зависимости в суммаризации: {e}")
        return f"Ошибка при суммаризации: требуется установка зависимостей ({e})."
    except Exception as e:
        logger.error(f"Ошибка при суммаризации: {e}")
        return f"Ошибка при суммаризации: {e}"