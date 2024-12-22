import logging
import click
import asyncio
from typing import List, Optional
from .models import ProcessingResult
from .filter_urls import filter_url
from .article import get_article_content
from .condense import condense_text
from .common import process_text_to_audio
from .errors import ProcessingError
from .constants import MIN_CONTENT_LENGTH, SUSPICIOUS_TEXTS
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ProcessingResult:
    url: str
    success: bool
    skipped: bool = False
    error: Optional[str] = None
    text: Optional[str] = None
    title: Optional[str] = None
    method: Optional[str] = None

async def process_article_async(url: str, **kwargs) -> ProcessingResult:
    """Async version of article processing"""
    try:
        if not await filter_url(url):
            logger.info(f"Skipping URL: {url}")
            return ProcessingResult(
                url=url,
                success=False,
                skipped=True,
                error="URL filtered: non-article content"
            )
            
        logger.info(f"Fetching content from URL: {url}")
        text, title, method = await get_article_content(url)
        
        logger.debug(f"Content extracted using {method} ({len(text)} chars):\n---\n{text}\n---")
        
        # Check for suspicious content patterns
        text_lower = text.lower()
        for suspicious in SUSPICIOUS_TEXTS:
            if suspicious in text_lower:
                raise ProcessingError(f"Suspicious content detected: '{suspicious}'. Article may not have loaded properly.")
        
        if len(text) < MIN_CONTENT_LENGTH:
            raise ProcessingError(f"Content too short ({len(text)} chars). Article may not have loaded properly.")

        if not kwargs.get('yes') and not click.confirm(f"Do you want to proceed with converting '{title}' to audio?", default=False):
            return ProcessingResult(url=url, success=False, skipped=True, error="Skipped by user")

        logger.info(f"Processing article: '{title}' (extracted using {method})")
        
        if kwargs.get('condense'):
            logger.info("Condensing article...")
            text = condense_text(text, kwargs['text_model'], kwargs['condense_ratio'])

        # Process the text to audio
        await process_text_to_audio(
            text=text,
            title=title,
            vendor=kwargs['vendor'],
            directory=kwargs['directory'],
            audio_format=kwargs['audio_format'],
            model=kwargs['speech_model'],
            voice=kwargs['voice'],
            strip=kwargs['strip']
        )
        
        return ProcessingResult(url=url, success=True, text=text, title=title, method=method)
        
    except Exception as e:
        logger.error(f"Failed to process {url}: {str(e)}")
        return ProcessingResult(url=url, success=False, error=str(e))

async def process_with_semaphore(url, semaphore, **kwargs):
    async with semaphore:
        try:
            if not await filter_url(url):
                logger.info(f"Skipping URL: {url}")
                return {
                    'url': url,
                    'success': False,
                    'skipped': True,
                    'error': "URL filtered: non-article content"
                }
            
            logger.info(f"Fetching content from URL: {url}")
            text, title, method = await get_article_content(url)
            
            # Apply condensing if requested
            if kwargs.get('condense'):
                ratio = kwargs.get('condense_ratio', 0.5)
                text_model = kwargs.get('text_model')
                logger.info(f"Condensing text with ratio {ratio} using model {text_model}")
                text = condense_text(
                    text=text,
                    text_model=text_model,
                    condense_ratio=ratio
                )
            
            # Rename speech_model to model if it exists in kwargs
            if 'speech_model' in kwargs:
                kwargs['model'] = kwargs.pop('speech_model')
                
            # Process text to audio without awaiting here
            await process_text_to_audio(text, title, **kwargs)
            
            return {
                'url': url,
                'success': True,
                'text': text,
                'title': title,
                'method': method
            }
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
            return {
                'url': url,
                'success': False,
                'error': str(e)
            }

async def process_articles_async(urls: List[str], concurrency: int = 3, **kwargs) -> List[dict]:
    """Process multiple articles concurrently"""
    semaphore = asyncio.Semaphore(concurrency)
    tasks = []
    
    # Create tasks for each URL
    for url in urls:
        task = asyncio.create_task(process_with_semaphore(url, semaphore, **kwargs))
        tasks.append(task)
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

def process_articles(urls: List[str], concurrency: int = 1, **kwargs) -> List[dict]:
    """Process a list of article URLs, converting them to audio."""
    if concurrency > 1:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(process_articles_async(urls, concurrency=concurrency, **kwargs))
            finally:
                loop.close()
                asyncio.set_event_loop(None)
        except Exception as e:
            logger.error(f"Error in async processing: {str(e)}")
            raise
    
    # Synchronous processing for concurrency=1
    results = []
    for url in urls:
        try:
            if not filter_url(url):
                logger.info(f"Skipping URL: {url}")
                results.append({
                    'url': url,
                    'success': False,
                    'skipped': True,
                    'error': "URL filtered: non-article content"
                })
                continue
            
            logger.info(f"Fetching content from URL: {url}")
            text, title, method = get_article_content(url)
            
            # Apply condensing if requested
            if kwargs.get('condense'):
                ratio = kwargs.get('condense_ratio', 0.5)
                text_model = kwargs.get('text_model')
                logger.info(f"Condensing text with ratio {ratio} using model {text_model}")
                text = condense_text(
                    text=text,
                    text_model=text_model,
                    condense_ratio=ratio
                )
            
            process_text_to_audio(text, title, **kwargs)
            results.append({
                'url': url,
                'success': True,
                'text': text,
                'title': title,
                'method': method
            })
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
            results.append({
                'url': url,
                'success': False,
                'error': str(e)
            })
    
    return results

async def process_article(url: str, options: dict) -> None:
    """Process a single article"""
    try:
        # Await the filter_url coroutine
        if not await filter_url(url):
            logger.info(f"Skipping filtered URL: {url}")
            return

        # Await the get_article_content coroutine
        text, title, method = await get_article_content(url)
        
        if options.get("strip"):
            text = text[:int(options["strip"])]
            
        # Process the text through the speech service
        await process_text_to_speech(text, title, options)
            
    except Exception as e:
        logger.error(f"Error processing {url}: {str(e)}")
        raise ProcessingError(f"Failed to process article: {str(e)}")
