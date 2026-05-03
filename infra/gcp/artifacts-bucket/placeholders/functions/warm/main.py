"""Placeholder Eventarc-triggered Cloud Function — not production logic."""

import json
import logging

import functions_framework

logger = logging.getLogger(__name__)


@functions_framework.cloud_event
def warm_appconfig_cache(cloud_event):
    """Stub for GCS object finalized → warm cache wiring."""
    payload = {
        "status": "PLACEHOLDER",
        "message": "warm_appconfig_cache not implemented yet",
        "event_type": getattr(cloud_event, "type", ""),
    }
    logger.info("warm_appconfig_cache stub: %s", payload)
    return json.dumps(payload)
