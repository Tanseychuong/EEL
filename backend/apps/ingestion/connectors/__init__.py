def get_connector_class(connector_type: str):
    from apps.ingestion.models import FetchSource
    from .rss_connector import RSSConnector

    registry = {
        FetchSource.ConnectorType.RSS: RSSConnector,
    }
    try:
        return registry[connector_type]
    except KeyError:
        raise ValueError(f"No connector registered for type '{connector_type}'")

