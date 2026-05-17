import json
import os
from typing import Any

from google.cloud import storage

from cloudshortener.constants import ENV, FunctionName


def load_config(function_name: FunctionName) -> dict[str, Any]:
    """Load backend-config.json from GCS and return the active backend entry for `function_name`."""
    bucket = os.environ[ENV.GCP.CONFIG_GCS_BUCKET]
    obj = os.environ.get(ENV.GCP.CONFIG_GCS_OBJECT, 'backend-config.json')

    client = storage.Client()
    blob = client.bucket(bucket).blob(obj)
    doc = json.loads(blob.download_as_text())

    active_backend = doc['active_backend']
    return {active_backend: doc['configs'][function_name.value][active_backend]}
