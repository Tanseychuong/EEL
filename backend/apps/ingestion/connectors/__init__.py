from apps.ingestion.models import FetchSource

from .rss_connector import RSSConnector

CONNECTOR_REGISTRY = {
    FetchSource.ConnectorType.RSS: RSSConnector,
}


def get_connector_class(connector_type: str):
    try:
        return CONNECTOR_REGISTRY[connector_type]
    except KeyError:
        raise ValueError(f"No connector registered for type '{connector_type}'")
