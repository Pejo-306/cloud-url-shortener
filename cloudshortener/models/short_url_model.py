from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class ShortURLModel:
    """Represent a shortend URL mapping.
    
    Attributes:
        original_url (str):
            The original long URL that the short code redirects to.
        short_code (str):
            The unique short identifier representing the shortened URL.
        expires_at (Optional[datetime]):
            Time-To-Live(TTL) as Python datetime, after which the short URL
            is no longer valid or persisted. 
    
    Example:
        >>> from datetime import datetime, timedelta
        >>> url = ShortURLModel(
        ...     original_url="https://example.com/article/123",
        ...     short_code="abc123",
        ...     expires_at=datetime.utcnow() + timedelta(days=365)
        ... )
        >>> url.original_url
        'https://example.com/article/123'
        >>> url.short_code
        'abc123'
        >>> isinstance(url.expires_at, datetime)
        True
    """
    original_url: str
    short_code: str
    expires_at: Optional[datetime] = None
