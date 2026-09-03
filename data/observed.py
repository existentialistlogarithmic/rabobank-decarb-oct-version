"""Shared plumbing for observed data: one series type, one caching rule.

Two providers sit on top of this - :mod:`eurostat` and :mod:`ecb`.  They differ
only in URL shape and in how a response is unpacked, so everything else lives
here: what a series *is*, how it is cached, and the rule that the model must
run with the network switched off.

The offline rule
----------------
Every fetch goes through :func:`fetch_or_cache`, which tries the network, falls
back to the committed cache, and never raises on a network failure.  A run with
no connectivity therefore produces the same numbers as a run with it - the
cached ones - and says so in the citation.  This is not a convenience: a model
whose outputs depend on whether a web service answered is not reproducible.
"""

from __future__ import annotations

import json
import pathlib
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Final

TIMEOUT: Final[int] = 25

#: Errors a fetch may raise that mean "fall back to cache" rather than "stop".
NETWORK_ERRORS: Final[tuple[type[BaseException], ...]] = (
    urllib.error.URLError, KeyError, IndexError, ValueError, TimeoutError, OSError,
)


@dataclass(frozen=True)
class Series:
    """One observed series: what it is, when, and where it came from.

    ``live`` records whether this run reached the source or read the cache.  It
    is carried into :meth:`cite` because a number's provenance includes how it
    arrived, not only who published it.
    """

    name: str
    period: str
    value: float
    unit: str
    source: str
    live: bool

    def cite(self) -> str:
        tag = "fetched" if self.live else "cached"
        return f"{self.name}: {self.value:,.4f} {self.unit} ({self.period}, {self.source}, {tag})"


def get_json(url: str) -> dict:
    """GET a JSON document. Raises on anything but a clean 200."""
    req = urllib.request.Request(url, headers={"User-Agent": "timing-model/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode())


def cache_read(path: pathlib.Path) -> dict:
    """Cached observations, or an empty dict if there is no readable cache."""
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def cache_write(path: pathlib.Path, data: dict) -> None:
    """Write the cache sorted and indented, so a refresh diffs readably."""
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def fetch_or_cache(
    key: str,
    cache: dict,
    offline: bool,
    fetch: Callable[[], tuple[str, float]],
    name: str,
    unit: str,
    source: str,
    default: Mapping[str, object] | None = None,
) -> Series:
    """One series, live if possible and cached otherwise.

    ``fetch`` returns ``(period, value)`` and may raise anything in
    :data:`NETWORK_ERRORS`; the failure is swallowed and the cache answers.

    Raises :class:`LookupError` only when there is no network *and* no cached
    value *and* no documented default - i.e. when the series has never been
    retrieved on this machine and nothing can honestly be reported.
    """
    if not offline:
        try:
            period, value = fetch()
            cache[key] = {"period": period, "value": value}
            return Series(name, period, value, unit, source, True)
        except NETWORK_ERRORS:
            pass
    cached = cache.get(key, default)
    if cached is None:
        raise LookupError(f"no cached value for {key!r}; run online once")
    return Series(name, str(cached["period"]), float(cached["value"]),
                  unit, source, False)
