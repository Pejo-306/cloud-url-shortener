from collections.abc import Callable
from typing import Any

from pytest import MonkeyPatch


def monkeypatch_innermost_function(
    monkeypatch: MonkeyPatch,
    innermost: Callable[..., Any],
    replacement: Callable[..., Any],
) -> None:
    # Patch the wrapped function body so the existing decorator stack remains in effect.
    monkeypatch.setattr(innermost.__wrapped__, '__code__', replacement.__code__)
