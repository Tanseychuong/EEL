from unittest.mock import Mock, patch

import pytest

from apps.ingestion.models import FetchLog, FetchSource
from apps.ingestion.connectors.rss_connector import RSSConnector
from apps.ingestion.services import fetch_source as run_fetch
from apps.opportunities.models import Opportunity

SAMPLE_RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
<item>
  <title>Sample Fellowship</title>
  <link>https://example.com/fellowship</link>
  <description>A great opportunity.</description>
  <pubDate>Mon, 01 Jan 2026 00:00:00 GMT</pubDate>
</item>
</channel></rss>"""


@pytest.fixture
def rss_source(db, category):
    return FetchSource.objects.create(
        name="Test Feed", connector_type=FetchSource.ConnectorType.RSS,
        url="https://example.com/feed.xml", category=category,
    )


def _mock_response(content=SAMPLE_RSS):
    response = Mock(content=content)
    response.raise_for_status = Mock()
    return response


class TestRSSConnector:
    """Pure parsing logic — no database, HTTP mocked out."""

    @patch("apps.ingestion.connectors.rss_connector.requests.get")
    def test_parses_items(self, mock_get, rss_source):
        mock_get.return_value = _mock_response()

        items = RSSConnector(rss_source).fetch()

        assert len(items) == 1
        assert items[0]["title"] == "Sample Fellowship"
        assert items[0]["opportunity_url"] == "https://example.com/fellowship"
        assert items[0]["application_deadline"] is not None

    @patch("apps.ingestion.connectors.rss_connector.requests.get")
    def test_skips_items_without_title(self, mock_get, rss_source):
        no_title_rss = b"""<?xml version="1.0"?>
        <rss version="2.0"><channel><item><link>https://example.com/x</link></item></channel></rss>"""
        mock_get.return_value = _mock_response(no_title_rss)

        items = RSSConnector(rss_source).fetch()

        assert items == []


@pytest.mark.django_db
class TestFetchSourceService:
    """The end-to-end behavior: a fetch creates PENDING opportunities and
    never auto-approves anything."""

    @patch("apps.ingestion.connectors.rss_connector.requests.get")
    def test_creates_pending_opportunity(self, mock_get, rss_source):
        mock_get.return_value = _mock_response()

        log = run_fetch(rss_source)

        assert log.status == FetchLog.Status.SUCCESS
        assert log.items_created == 1
        opportunity = Opportunity.objects.get(title="Sample Fellowship")
        assert opportunity.status == Opportunity.Status.PENDING
        assert opportunity.source_type == Opportunity.SourceType.FETCHED
        assert opportunity.fetch_source == rss_source

    @patch("apps.ingestion.connectors.rss_connector.requests.get")
    def test_does_not_duplicate_on_rerun(self, mock_get, rss_source):
        mock_get.return_value = _mock_response()

        run_fetch(rss_source)
        second_log = run_fetch(rss_source)

        assert Opportunity.objects.filter(title="Sample Fellowship").count() == 1
        assert second_log.items_created == 0
        assert second_log.status == FetchLog.Status.PARTIAL

    @patch("apps.ingestion.connectors.rss_connector.requests.get")
    def test_failure_is_logged_not_raised(self, mock_get, rss_source):
        mock_get.side_effect = Exception("network error")

        log = run_fetch(rss_source)  # should not raise

        assert log.status == FetchLog.Status.FAILURE
        assert "network error" in log.error_message

    @patch("apps.ingestion.connectors.rss_connector.requests.get")
    def test_updates_last_fetched_at(self, mock_get, rss_source):
        mock_get.return_value = _mock_response()
        assert rss_source.last_fetched_at is None

        run_fetch(rss_source)
        rss_source.refresh_from_db()

        assert rss_source.last_fetched_at is not None
