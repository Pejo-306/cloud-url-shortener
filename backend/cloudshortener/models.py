from dataclasses import dataclass
from datetime import datetime


# fmt: off
@dataclass(frozen=True)
class ShortURLModel:
    target: str                         # Original long URL
    shortcode: str                      # Unique short identifier of shortened URL
    hits: int | None = None             # Leftover montly quota for link hits
    expires_at: datetime | None = None  # TTL as Python datetime, after which this record is expired
# fmt: on
