from dataclasses import dataclass, field

from cloudshortener.cloud.dao.base import BackendConfigCacheBaseDAO


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    body: str
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class FunctionConfig:
    pass


@dataclass(frozen=True)
class RedirectConfig(FunctionConfig):
    redis_host: str
    redis_port: int
    redis_db: int
    redis_username: str | None = None
    redis_password: str | None = None
    app_prefix: str | None = None


@dataclass(frozen=True)
class ShortenConfig(FunctionConfig):
    redis_host: str
    redis_port: int
    redis_db: int
    redis_username: str | None = None
    redis_password: str | None = None
    app_prefix: str | None = None


@dataclass(frozen=True)
class FunctionRequest:
    pass


@dataclass(frozen=True)
class RedirectRequest(FunctionRequest):
    shortcode: str | None
    short_url: str


@dataclass(frozen=True)
class ShortenRequest(FunctionRequest):
    user_id: str | None
    body: str | None
    base_url: str


@dataclass(frozen=True)
class WarmConfigCacheRequest(FunctionRequest):
    pass


@dataclass(frozen=True)
class WarmConfigCacheConfig(FunctionConfig):
    dao: BackendConfigCacheBaseDAO
