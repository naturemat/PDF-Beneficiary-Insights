import re
import logging
import requests
from pathlib import Path
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

PDFS_FOLDER = Path(__file__).parent / "pdfs"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/pdf,*/*",
}


def is_url(input_str: str) -> bool:
    return bool(re.match(r"https?://", input_str.strip(), re.IGNORECASE))


def is_sharepoint_url(url: str) -> bool:
    return "sharepoint.com" in url.lower()


def _try_download(url: str, timeout: int = 60) -> bytes | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            return None
        content = resp.content
        if content[:5] == b"%PDF-":
            return content
        ct = resp.headers.get("Content-Type", "").lower()
        if "pdf" in ct:
            return content
    except Exception as e:
        logger.debug(f"Download attempt failed: {e}")
    return None


def _graph_api_download(url: str) -> bytes | None:
    try:
        from auth import get_access_token
        from config import GRAPH_BASE_URL
        token = get_access_token()
        if not token:
            return None

        file_id = _extract_sharepoint_file_id(url)
        if not file_id:
            return None

        api_url = f"{GRAPH_BASE_URL}/me/drive/items/{file_id}/content"
        logger.info(f"Graph API download: {api_url[:80]}...")
        resp = requests.get(
            api_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
            allow_redirects=True,
        )
        if resp.status_code == 200 and resp.content[:5] == b"%PDF-":
            return resp.content
        logger.warning(f"Graph API returned status {resp.status_code}")
    except Exception as e:
        logger.debug(f"Graph API download failed: {e}")
    return None


def _extract_sharepoint_file_id(url: str) -> str | None:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "id" in qs:
        return qs["id"][0]
    token_match = re.search(r"/([A-Za-z0-9_%\-]+)\?e=", url)
    if token_match:
        return token_match.group(1)
    return None


def _sharepoint_strategies(url: str) -> bytes | None:
    # Strategy 0: Graph API (if configured)
    result = _graph_api_download(url)
    if result:
        return result

    # Strategy 1: direct with download=1
    sep = "&" if "?" in url else "?"
    attempt1 = f"{url}{sep}download=1"
    logger.info(f"Strategy 1 (download=1): {attempt1[:80]}...")
    result = _try_download(attempt1)
    if result:
        return result

    # Strategy 2: replace :b: with :u:
    if "/:b:/" in url:
        attempt2 = url.replace("/:b:/", "/:u:/")
        logger.info(f"Strategy 2 (:u: link): {attempt2[:80]}...")
        result = _try_download(attempt2)
        if result:
            return result

    # Strategy 3: download.aspx
    token_match = re.search(r"/([^/]+)\?e=", url)
    if token_match:
        token = token_match.group(1)
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        attempt3 = f"{base}/_layouts/15/download.aspx?UniqueId={token}"
        logger.info(f"Strategy 3 (download.aspx): {attempt3[:80]}...")
        result = _try_download(attempt3)
        if result:
            return result

    return None


def download_pdf(source: str) -> bytes:
    if is_url(source):
        return _download_from_url(source)
    return _read_from_file(source)


def list_local_pdfs() -> list[Path]:
    PDFS_FOLDER.mkdir(exist_ok=True)
    return sorted(PDFS_FOLDER.glob("*.pdf"))


def _download_from_url(url: str) -> bytes:
    if is_sharepoint_url(url):
        result = _sharepoint_strategies(url)
        if result:
            logger.info(f"SharePoint download succeeded ({len(result)} bytes).")
            return result
        raise PermissionError(
            "SharePoint requires authentication.\n"
            "  Option A: Configure .env with Microsoft Graph API credentials\n"
            "  Option B: Open the URL in your browser, download the PDF,\n"
            f"            save it to: {PDFS_FOLDER}, then use option 2 or 3"
        )

    logger.info(f"Downloading from URL: {url[:80]}...")
    result = _try_download(url)
    if result:
        return result

    try:
        resp = requests.get(url, timeout=60, allow_redirects=True)
        resp.raise_for_status()
        if resp.content[:5] == b"%PDF-":
            return resp.content
    except Exception:
        pass

    raise ValueError(
        f"Could not download PDF from URL.\n"
        "  1. Open the URL in your browser\n"
        "  2. Download the PDF manually\n"
        f"  3. Save it to: {PDFS_FOLDER}\n"
        "  4. Use option 2 or 3 in the menu"
    )


def _read_from_file(path_str: str) -> bytes:
    path = Path(path_str).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.suffix.lower() == ".pdf":
        raise ValueError(f"Not a PDF file: {path}")
    logger.info(f"Reading local file: {path}")
    data = path.read_bytes()
    logger.info(f"Read {len(data)} bytes.")
    return data
