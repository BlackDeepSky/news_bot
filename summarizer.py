from transformers import pipeline
from newspaper import Article
import aiohttp
import os
from loguru import logger
import re

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

def postprocess_summary(summary):
    """Постобработка сводки"""
    # Удаляем повторяющиеся фразы
    summary = re.sub(r'\b(\w+)\b\s+\1', r'\1', summary)
    
    # Удаляем лишние пробелы
    summary = re.sub(r'\s+', ' ', summary).strip()
    
    return summary

def summarize_text(text):
    """Суммаризация с настройкой параметров"""
    try:
        truncated = " ".join(text.split()[:1024])  # Ограничиваем входной текст
        return summarizer(
            truncated,
            max_length=300,
            min_length=100,
            do_sample=True,  # Включаем случайную выборку
            num_beams=4,     # Увеличиваем количество лучей
            temperature=0.3  # Устанавливаем температуру
        )[0]['summary_text']
    except Exception as e:
        logger.error(f"Ошибка суммаризации: {e}")
        return "Ошибка создания сводки"