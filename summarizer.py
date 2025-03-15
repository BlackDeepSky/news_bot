from transformers import pipeline
from newspaper import Article
import aiohttp
import os
from loguru import logger

summarizer = None

def load_models():
    """Инициализация модели суммаризации"""
    global summarizer
    try:
        summarizer = pipeline(
            "summarization",
            model="sshleifer/distilbart-cnn-12-6",
            framework="pt"
        )
        logger.info("Модель для суммаризации загружена")
    except Exception as e:
        logger.error(f"Ошибка загрузки модели: {e}")
        raise

async def get_article_text(url):
    """Асинхронное получение текста статьи"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                html = await response.text()
                
        article = Article(url)
        article.set_html(html)
        article.parse()
        
        if article.text and len(article.text) > 100:
            return article.text[:3000]  # Ограничение для CPU
        
        return "Не удалось извлечь текст статьи."
    
    except Exception as e:
        logger.error(f"Ошибка парсинга {url}: {e}")
        return ""

def summarize_text(text):
    """Суммаризация с DistilBART"""
    try:
        truncated = " ".join(text.split()[:900])
        return summarizer(truncated, max_length=150, min_length=30)[0]['summary_text']
    except Exception as e:
        logger.error(f"Ошибка суммаризации: {e}")
        return "Ошибка создания сводки"