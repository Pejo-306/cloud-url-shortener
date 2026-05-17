import json
from unittest.mock import Mock

from pytest import MonkeyPatch

from cloudshortener.cloud.gcp import config as config_module
from cloudshortener.constants import ENV, FunctionName


def test_load_config(monkeypatch: MonkeyPatch) -> None:
    mock_blob = Mock(spec=['download_as_text'])
    mock_blob.download_as_text.return_value = json.dumps(
        {
            'active_backend': 'redis',
            'configs': {
                'redirect_url': {
                    'redis': {
                        'host': 'redis.example',
                        'port': 6379,
                        'db': 2,
                        'username': 'u1',
                        'password': 'secret',
                    },
                },
            },
        },
    )
    mock_bucket = Mock(spec=['blob'])
    mock_bucket.blob.return_value = mock_blob
    mock_client = Mock(spec=['bucket'])
    mock_client.bucket.return_value = mock_bucket

    monkeypatch.setattr(config_module.storage, 'Client', lambda: mock_client)
    monkeypatch.setenv(ENV.GCP.CONFIG_GCS_BUCKET, 'cfg-bucket')
    monkeypatch.delenv(ENV.GCP.CONFIG_GCS_OBJECT, raising=False)

    raw_config = config_module.load_config(FunctionName.REDIRECT_URL)

    assert raw_config == {
        'redis': {
            'host': 'redis.example',
            'port': 6379,
            'db': 2,
            'username': 'u1',
            'password': 'secret',
        },
    }
