from dataclasses import dataclass


@dataclass
class ProcessingResult:
    """
    Represents the result of processing a single article.

    Attributes:
        url: The URL of the article
        success: Whether the processing was successful
        error: Error message if processing failed, None otherwise
    """

    url: str
    success: bool
    error: str = None
