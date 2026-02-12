"""Common interface for publication fetchers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from citesync.models import Publication


class Fetcher(ABC):
    """Base class all fetchers implement.

    Keeping this thin and explicit (rather than a `Protocol`) so fetchers can
    share small helpers later (retry logic, rate limiting) without every
    call site needing to know about it.
    """

    @abstractmethod
    def fetch(self) -> list[Publication]:
        """Return normalized publications from this source."""
        raise NotImplementedError
