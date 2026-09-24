"""
Every connector takes a FetchSource and returns a plain list of dicts —
nothing here knows about Django models beyond that, so a connector is
testable with zero database access.

Expected dict keys per item (all but title/opportunity_url optional):
    title, description, organization, location,
    opportunity_url, application_deadline (datetime or None)
"""

from abc import ABC, abstractmethod


class BaseConnector(ABC):
    def __init__(self, source):
        self.source = source

    @abstractmethod
    def fetch(self) -> list[dict]:
        """Fetch and return raw opportunity items. Raise on failure rather
        than returning an empty list, so the caller can distinguish
        'nothing new' from 'the fetch broke'."""
        raise NotImplementedError
