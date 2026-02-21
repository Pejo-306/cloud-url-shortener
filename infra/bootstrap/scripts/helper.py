# TODO: add stricter YAML schema validation (e.g., pydantic) if needed
# TODO: add glob filtering to yaml_config_files for targeted functions/environments

import pathlib
from typing import Any
from collections.abc import Iterator

import boto3
import yaml

from scripts.types import AWSTag

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent


def load_yaml(path: pathlib.Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f'YAML not found: {path}')
    with path.open('r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data or {}


def yaml_config_files(root: pathlib.Path) -> Iterator[pathlib.Path]:
    """Yield config YAML files under `root` following config/<function>/*.yaml."""
    for function_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        yield from sorted(function_dir.glob('*.yaml'))


def normalize_user_tags(tag_str: str) -> list[AWSTag]:
    """Normalize a comma-separated tag string into AWS tag dicts.

    Input format (comma-separated key=value pairs):
        "Key1=Val1,Key2=Val2"

    Output format (AWS tag dicts):
        [{"Key": "Key1", "Value": "Val1"}, {"Key": "Key2", "Value": "Val2"}]

    Example:
        >>> normalize_user_tags("Owner=Pesho,Service=cloudshortener")
        [{'Key': 'Owner', 'Value': 'Pesho'}, {'Key': 'Service', 'Value': 'cloudshortener'}]
    """
    tags: list[dict[str, str]] = []
    if not tag_str:
        return tags

    for raw in tag_str.split(','):
        item = raw.strip()
        if not item:
            # Skip empty segments like trailing commas.
            continue
        if '=' not in item:
            raise ValueError(f"Malformed tag (expected key=value): '{item}'")
        key, value = item.split('=', 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"Malformed tag (empty key): '{item}'")
        tags.append({'Key': key, 'Value': value})
    return tags


def flatten(prefix: str, data: dict[str, Any]) -> dict[str, str]:
    """Flatten nested dictionaries into path -> string value pairs.

    Used to construct SSM parameter paths from our config YAML files.

    Input format (nested dictionary):
        {"redis": {"host": "h", "port": 6379}}

    Output format (SSM-like path -> string value pairs):
        {
            "/cloudshortener/dev/shorten_url/redis/host": "h",
            "/cloudshortener/dev/shorten_url/redis/port": "6379",
        }

    Rules:
        - Nested dicts become path segments: prefix/key/subkey
        - Non-dict values are stringified
        - None becomes empty string

    Args:
        prefix (str):
            Base path (e.g., "/cloudshortener/dev/shorten_url").
        data (Dict[str, Any]):
            Nested dictionary to flatten.

    Example:
        >>> flatten("/path/prefix", {"redis": {"host": "h", "port": 6379}})
        {"/path/prefix/redis/host": "h", "/path/prefix/redis/port": "6379"}
    """
    out: dict[str, str] = {}

    def _walk(base: str, node: Any) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                _walk(f'{base}/{k}', v)
        else:
            out[base] = '' if node is None else str(node)

    _walk(prefix, data)
    return out


def boto3_session(profile: str | None) -> boto3.Session:
    """Build a boto3 Session honoring an optional profile.

    Example:
        >>> session = boto3_session("personal-dev")  # doctest: +SKIP
        >>> ssm = session.client("ssm")              # doctest: +SKIP
    """
    if profile:
        return boto3.Session(profile_name=profile)
    return boto3.Session()


def parameter_overrides(overrides: str) -> dict[str, str]:
    """Parse a comma-separated CloudFormation --parameter-overrides string.

    Input format:
        "A=B,C=D,E="  (whitespace around items is ignored)

    Behavior:
        - Empty string returns {}.
        - Missing "=value" yields an empty string value (e.g., "Key" -> {"Key": ""}).
        - Preserves empty values (e.g., "E=" -> {"E": ""}).

    Args:
        overrides (str):
            Comma-separated key=value pairs.

    Returns:
        dict[str, str]:
            Parsed mapping suitable for boto3 ParameterKey/ParameterValue conversion.

    Example:
        >>> parameter_overrides("GitHubOrg=Pejo-306,RepoName=cloud-url-shortener,E=")
        {'GitHubOrg': 'Pejo-306', 'RepoName': 'cloud-url-shortener', 'E': ''}
    """
    result: dict[str, str] = {}
    if not overrides:
        return result
    for part in overrides.split(','):
        item = part.strip()
        if not item:
            continue
        if '=' not in item:
            # Allow bare keys; treat as empty string
            result[item] = ''
            continue
        k, v = item.split('=', 1)
        result[k.strip()] = v
    return result
