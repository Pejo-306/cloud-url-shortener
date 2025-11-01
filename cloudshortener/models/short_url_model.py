from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class ShortURLModel:
    """Represent a shortend URL mapping.
    
    Attributes:
        target (str):
            The original long URL that the short code redirects to.
        shortcode (str):
            The unique short identifier representing the shortened URL.
        expires_at (Optional[datetime]):
            Time-To-Live(TTL) as Python datetime, after which the short URL
            is no longer valid or persisted. 
    
    Example:
        >>> from datetime import datetime, timedelta
        >>> url = ShortURLModel(
        ...     target="https://example.com/article/123",
        ...     shortcode="abc123",
        ...     expires_at=datetime.utcnow() + timedelta(days=365)
        ... )
        >>> url.target
        'https://example.com/article/123'
        >>> url.shortcode
        'abc123'
        >>> isinstance(url.expires_at, datetime)
        True
    """
    target: str
    shortcode: str
    expires_at: Optional[datetime] = None
