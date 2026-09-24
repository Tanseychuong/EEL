"""
A working RSS/Atom connector. Deliberately uses the standard library's XML
parser rather than a feed-parsing dependency, to keep the example
self-contained — swap in `feedparser` if a real-world feed turns out to be
malformed in ways ElementTree chokes on (common enough with RSS in the
wild that it's worth knowing as the first thing to reach for).
"""

from datetime import datetime
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import requests

from .base import BaseConnector


class RSSConnector(BaseConnector):
    TIMEOUT_SECONDS = 15

    def fetch(self) -> list[dict]:
        response = requests.get(self.source.url, timeout=self.TIMEOUT_SECONDS)
        response.raise_for_status()

        root = ElementTree.fromstring(response.content)
        items = []
        for item in root.findall(".//item"):
            title = self._text(item, "title")
            if not title:
                continue  # skip anything without even a title — not usable
            items.append({
                "title": title,
                "description": self._text(item, "description"),
                "opportunity_url": self._text(item, "link"),
                "organization": self.source.name,
                "application_deadline": self._parse_date(self._text(item, "pubDate")),
            })
        return items

    @staticmethod
    def _text(item, tag: str) -> str:
        el = item.find(tag)
        return (el.text or "").strip() if el is not None else ""

    @staticmethod
    def _parse_date(raw: str) -> datetime | None:
        if not raw:
            return None
        try:
            return parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            return None
