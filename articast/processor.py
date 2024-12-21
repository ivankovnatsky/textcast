import logging
import click
from typing import List
from .models import ProcessingResult
from .filter_urls import filter_url
from .article import get_article_content
from .condense import condense_text
from .common import process_text_to_audio

logger = logging.getLogger(__name__)

def process_articles(urls: List[str], **kwargs) -> List[ProcessingResult]:
    """
    Process a list of article URLs, converting them to audio.
    
    Args:
        urls: List of URLs to process
        **kwargs: Additional arguments from CLI (condense, text_model, condense_ratio, etc.)
    
    Returns:
        List[ProcessingResult]: Results of processing each article
    """
    results = []
    
    for url in urls:
        if not filter_url(url):
            results.append(ProcessingResult(url=url, success=False, error="URL filtered: non-article content"))
            continue

        try:
            logger.info(f"Fetching content from URL: {url}")
            text, title = get_article_content(url)
            
            if not kwargs.get('yes') and not click.confirm(f"Do you want to proceed with converting '{title}' to audio?", default=False):
                results.append(ProcessingResult(url=url, success=False, error="Skipped by user"))
                continue

            logger.info(f"Processing article: '{title}'")
            
            if kwargs.get('condense'):
                logger.info("Condensing article...")
                text = condense_text(text, kwargs['text_model'], kwargs['condense_ratio'])

            # Process the text to audio
            process_text_to_audio(
                text=text,
                title=title,
                vendor=kwargs['vendor'],
                directory=kwargs['directory'],
                audio_format=kwargs['audio_format'],
                model=kwargs['speech_model'],
                voice=kwargs['voice'],
                strip=kwargs['strip']
            )
            
            results.append(ProcessingResult(url=url, success=True))
            
        except Exception as e:
            logger.error(f"Failed to process {url}: {str(e)}")
            results.append(ProcessingResult(url=url, success=False, error=str(e)))
            continue
    
    # Print summary
    successful = len([r for r in results if r.success])
    failed = len([r for r in results if not r.success])
    
    logger.info("\nProcessing Summary:")
    logger.info(f"Successfully processed: {successful}")
    logger.info(f"Failed to process: {failed}")
    
    if failed > 0:
        logger.info("\nFailed articles:")
        for result in results:
            if not result.success:
                logger.info(f"- {result.url}: {result.error}")
    
    return results 
