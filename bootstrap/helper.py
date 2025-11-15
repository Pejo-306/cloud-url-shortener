"""
Common helpers for seeding configuration into AWS.

This module groups utility functions shared by the seeding CLIs.

Exposed functions (signatures):
    load_yaml(path: pathlib.Path) -> dict[str, Any]
    yaml_config_files(root: pathlib.Path) -> Iterable[pathlib.Path]
    normalize_user_tags(tag_str: str) -> list[dict[str, str]]
    flatten(prefix: str, data: dict[str, Any]) -> dict[str, str]
    boto3_session(profile: str | None) -> "boto3.Session"

Behavior:
    - `load_yaml` safely loads YAML files, defaulting to {} for empty files.
    - `yaml_config_files` discovers files shaped as config/<function>/*.yaml.
    - `normalize_user_tags` converts "K1=V1,K2=V2" into AWS tag dicts.
    - `flatten` turns nested dicts into SSM-like path/value pairs.
    - `boto3_session` builds a boto3 session honoring an optional profile.

Raises:
    FileNotFoundError: When a provided path does not exist.
    ValueError: For malformed tag strings in `normalize_user_tags`.

Example:
    >>> from pathlib import Path
    >>> for p in yaml_config_files(Path("config")):
    ...     doc = load_yaml(p)
    ...     params = doc.get("params") or {}
    ...     flat = flatten("/app/dev/shorten_url", params)
    ...     # Do something with 'flat'

# TODO: add stricter YAML schema validation (e.g., pydantic) if needed
# TODO: add glob filtering to yaml_config_files for targeted functions/environments
"""

from __future__ import annotations

import pathlib
from typing import Any
from collections.abc import Iterator

import boto3
import yaml


def load_yaml(path: pathlib.Path) -> dict[str, Any]:
    """Load a YAML file into a Python dictionary.

    Args:
        path (pathlib.Path):
            Path to a YAML file.

    Returns:
        Dict[str, Any]:
            Parsed YAML document. Returns {} for empty files.

    Raises:
        FileNotFoundError:
            If the file does not exist.

    Example:
        >>> from pathlib import Path
        >>> load_yaml(Path("config/shorten_url/dev.yaml"))  # doctest: +SKIP
        {'params': {...}, 'secrets': {...}}
    """
    if not path.is_file():
        raise FileNotFoundError(f"YAML not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def yaml_config_files(root: pathlib.Path) -> Iterator[pathlib.Path]:
    """Yield config YAML files under `root` following config/<function>/*.yaml.

    Args:
        root (pathlib.Path):
            Root folder containing per-function config directories.

    Yields:
        pathlib.Path:
            Paths to discovered YAML files.

    Example:
        >>> from pathlib import Path
        >>> list(yaml_config_files(Path("config")))  # doctest: +ELLIPSIS +SKIP
        [PosixPath('config/redirect_url/dev.yaml'), PosixPath('config/shorten_url/dev.yaml')]
    """
    for function_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        yield from sorted(function_dir.glob("*.yaml"))


def normalize_user_tags(tag_str: str) -> list[dict[str, str]]:
    """Normalize a comma-separated tag string into AWS tag dicts.

    Input format:
        "Key1=Val1,Key2=Val2"

    Args:
        tag_str (str):
            Comma-separated tags.

    Returns:
        list[dict[str, str]]:
            Items like [{"Key": "Owner", "Value": "Pesho"}, ...].

    Raises:
        ValueError:
            If an entry is malformed (missing '=' or empty key).

    Example:
        >>> normalize_user_tags("Owner=Pesho,Service=cloudshortener")
        [{'Key': 'Owner', 'Value': 'Pesho'}, {'Key': 'Service', 'Value': 'cloudshortener'}]
    """
    tags: list[dict[str, str]] = []
    if not tag_str:
        return tags

    for raw in tag_str.split(","):
        item = raw.strip()
        if not item:
            # Skip empty segments like trailing commas.
            continue
        if "=" not in item:
            raise ValueError(f"Malformed tag (expected key=value): '{item}'")
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"Malformed tag (empty key): '{item}'")
        tags.append({"Key": key, "Value": value})
    return tags


def flatten(prefix: str, data: dict[str, Any]) -> dict[str, str]:
    """Flatten nested dictionaries into path -> string value pairs.

    Rules:
        - Nested dicts become path segments: prefix/key/subkey
        - Non-dict values are stringified
        - None becomes empty string

    Args:
        prefix (str):
            Base path (e.g., "/cloudshortener/dev/shorten_url").
        data (Dict[str, Any]):
            Nested dictionary to flatten.

    Returns:
        Dict[str, str]:
            Mapping of full path to value.

    Example:
        >>> flatten("/p/e/f", {"redis": {"host": "h", "port": 6379}})
        {'/p/e/f/redis/host': 'h', '/p/e/f/redis/port': '6379'}
    """
    out: dict[str, str] = {}

    def _walk(base: str, node: Any) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                _walk(f"{base}/{k}", v)
        else:
            out[base] = "" if node is None else str(node)

    _walk(prefix, data)
    return out


def boto3_session(profile: str | None):
    """Return a boto3 Session honoring an optional profile.

    Args:
        profile (str | None):
            AWS shared config/credentials profile name, or None for default resolution.

    Returns:
        boto3.Session:
            A configured boto3 session ready to create service clients.

    Example:
        >>> session = boto3_session("personal-dev")  # doctest: +SKIP
        >>> ssm = session.client("ssm")              # doctest: +SKIP
    """
    if profile:
        return boto3.Session(profile_name=profile)
    return boto3.Session()
