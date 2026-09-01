import logging
import msal
import config

logger = logging.getLogger(__name__)


def get_access_token() -> str:
    app = msal.ConfidentialClientApplication(
        client_id=config.CLIENT_ID,
        client_credential=config.CLIENT_SECRET,
        authority=config.GRAPH_AUTHORITY,
    )
    result = app.acquire_token_silent(config.GRAPH_SCOPES, account=None)
    if not result:
        logger.info("No cached token. Acquiring new token...")
        result = app.acquire_token_for_client(scopes=config.GRAPH_SCOPES)
    if "access_token" in result:
        logger.info("Token acquired.")
        return result["access_token"]
    error = result.get("error", "unknown")
    desc = result.get("error_description", "No description")
    raise RuntimeError(f"Token failed: {error} - {desc}")
