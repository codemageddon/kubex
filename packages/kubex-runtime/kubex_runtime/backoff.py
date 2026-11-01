from __future__ import annotations

import random
import threading
from typing import Protocol


class Backoff(Protocol):
    """Yields the delays between attempts of a failing operation."""

    def next(self) -> float | None:
        """The delay before the next attempt, None when no attempt is left."""

    def reset(self) -> None:
        """Starts over: the operation succeeded."""


class ExponentialBackoff:
    """Delays growing by `factor` from `initial` up to `max_delay`.

    With `jitter` every delay is drawn uniformly from [delay / 2, delay], so that
    clients failing together do not retry together.
    """

    def __init__(
        self,
        *,
        initial: float = 0.8,
        max_delay: float = 30.0,
        factor: float = 2.0,
        jitter: bool = True,
        max_retries: int | None = None,
    ) -> None:
        self._initial = initial
        self._max_delay = max_delay
        self._factor = factor
        self._jitter = jitter
        self._max_retries = max_retries
        self._attempt = 0
        # it may be shared by watchers in several threads
        self._lock = threading.Lock()

    def next(self) -> float | None:
        with self._lock:
            attempt = self._attempt
            if self._max_retries is not None and attempt >= self._max_retries:
                return None
            self._attempt += 1
        # min() before the power would overflow after ~1000 attempts
        exponent = min(attempt, 64)
        delay = min(self._initial * self._factor**exponent, self._max_delay)
        if self._jitter:
            delay = random.uniform(delay / 2, delay)
        return delay

    def reset(self) -> None:
        self._attempt = 0


def default_backoff() -> Backoff:
    return ExponentialBackoff()
