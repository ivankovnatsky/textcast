import logging
import click
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
        try:
            if not filter_url(url):
                logger.info(f"Skipping URL: {url}")
                results.append(ProcessingResult(
                    url=url,
                    success=False,
                    skipped=True,
                    error="URL filtered: non-article content"
                ))
                continue
                
            logger.info(f"Fetching content from URL: {url}")
            text, title, method = get_article_content(url)
            
            logger.debug(f"Content extracted using {method} ({len(text)} chars):\n---\n{text}\n---")
            
            # Check for suspicious content patterns
            text_lower = text.lower()
            for suspicious in SUSPICIOUS_TEXTS:
                if suspicious in text_lower:
                    raise ProcessingError(f"Suspicious content detected: '{suspicious}'. Article may not have loaded properly.")
            
            if len(text) < MIN_CONTENT_LENGTH:
                raise ProcessingError(f"Content too short ({len(text)} chars). Article may not have loaded properly.")

            if not kwargs.get('yes') and not click.confirm(f"Do you want to proceed with converting '{title}' to audio?", default=False):
                results.append(ProcessingResult(url=url, success=False, skipped=True, error="Skipped by user"))
                continue

            logger.info(f"Processing article: '{title}' (extracted using {method})")
            
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
                strip=kwargs['strip'],
                abs_url=kwargs.get('abs_url'),
                abs_pod_lib_id=kwargs.get('abs_pod_lib_id'),
                abs_pod_folder_id=kwargs.get('abs_pod_folder_id')
            )
            
            results.append(ProcessingResult(url=url, success=True))
            
        except Exception as e:
            logger.error(f"Failed to process {url}: {str(e)}")
            results.append(ProcessingResult(url=url, success=False, error=str(e)))
            continue
    
    # Update summary to include skipped count
    successful = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success and not r.skipped)
    skipped = sum(1 for r in results if r.skipped)
    
    logger.info("Processing Summary:")
    logger.info(f"Successfully processed: {successful}")
    logger.info(f"Failed to process: {failed}")
    logger.info(f"Skipped: {skipped}")
    
    if failed > 0 or skipped > 0:
        logger.info("Failed articles:")
        for result in results:
            if not result.success and not result.skipped:
                logger.info(f"- {result.url}: {result.error}")
                
        logger.info("Skipped articles:")
        for result in results:
            if result.skipped:
                logger.info(f"- {result.url}: {result.error}")
    
    return results 
