import functools
import json
import logging
from collections.abc import Callable

from cloudshortener.cloud.functions.types import FunctionConfig, FunctionRequest, HttpResponse
from cloudshortener.constants import UNKNOWN_INTERNAL_SERVER_ERROR

logger = logging.getLogger(__name__)


# TODO: add support for running locally
def guarantee_500_response[RequestT: FunctionRequest, ConfigT: FunctionConfig](
    handler: Callable[[RequestT, ConfigT], HttpResponse],
) -> Callable[[RequestT, ConfigT], HttpResponse]:
    """Decorator: guarantee a 500 HTTP response in case of unhandled exception."""

    # TODO: need to extend this to include CORS headers
    def _response_500() -> HttpResponse:
        body = {
            'message': 'Internal Server Error',
            'error_code': UNKNOWN_INTERNAL_SERVER_ERROR,
        }
        return HttpResponse(
            status_code=500,
            headers={'Content-Type': 'application/json'},
            body=json.dumps(body),
        )

    @functools.wraps(handler)
    def wrapper(request: RequestT, config: ConfigT) -> HttpResponse:
        try:
            return handler(request, config)
        except Exception as e:
            logger.exception('Unhandled error in redirect handler.', extra={'error': e.__class__.__name__, 'reason': str(e)})
            return _response_500()

    return wrapper
