import logging
import requests
import config
from auth import get_access_token

logger = logging.getLogger(__name__)


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json",
    }


def get_excel_headers() -> list[str]:
    token = get_access_token()
    url = (
        f"{config.GRAPH_BASE_URL}/drives/{config.EXCEL_FILE_ID}"
        f"/workbook/worksheets('{config.EXCEL_WORKSHEET_NAME}')"
        f"/tables('{config.EXCEL_TABLE_NAME}')/columns"
    )
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    cols = [c["name"] for c in resp.json().get("value", [])]
    logger.info(f"Excel columns: {cols}")
    return cols


def check_duplicate(code: str) -> bool:
    token = get_access_token()
    url = (
        f"{config.GRAPH_BASE_URL}/drives/{config.EXCEL_FILE_ID}"
        f"/workbook/worksheets('{config.EXCEL_WORKSHEET_NAME}')"
        f"/tables('{config.EXCEL_TABLE_NAME}')/rows"
    )
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    rows = resp.json().get("value", [])
    cols = get_excel_headers()
    code_idx = None
    for i, c in enumerate(cols):
        if "código" in c.lower() and "proyecto" in c.lower():
            code_idx = i
            break
    if code_idx is None:
        return False
    for row in rows:
        vals = row.get("values", [[]])[0]
        if len(vals) > code_idx and str(vals[code_idx]).strip() == code:
            logger.info(f"Duplicate found: {code}")
            return True
    return False


def insert_row(data: dict) -> bool:
    cols = get_excel_headers()
    mapping = {
        "Carrera": data.get("Carrera", ""),
        "Nombre del Proyecto": data.get("Nombre del Proyecto", ""),
        "Código del Proyecto": data.get("Código del Proyecto", ""),
        "Beneficiarios Directos": data.get("Beneficiarios Directos", 0),
        "Beneficiarios Indirectos": data.get("Beneficiarios Indirectos", 0),
        "Total Mujeres": data.get("Total Mujeres", 0),
        "Total Hombres": data.get("Total Hombres", 0),
        "Discapacidad Mujeres": data.get("Discapacidad Mujeres", 0),
        "Discapacidad Hombres": data.get("Discapacidad Hombres", 0),
        "Mestizo": data.get("Mestizo", 0),
        "Indígena": data.get("Indígena", 0),
        "Afroecuatoriano": data.get("Afroecuatoriano", 0),
        "Montubio": data.get("Montubio", 0),
        "Blanco": data.get("Blanco", 0),
        "Otros": data.get("Otros", 0),
    }
    row_values = [mapping.get(c, "") for c in cols]
    token = get_access_token()
    url = (
        f"{config.GRAPH_BASE_URL}/drives/{config.EXCEL_FILE_ID}"
        f"/workbook/worksheets('{config.EXCEL_WORKSHEET_NAME}')"
        f"/tables('{config.EXCEL_TABLE_NAME}')/rows"
    )
    payload = {"values": [row_values]}
    resp = requests.post(url, headers=_headers(), json=payload)
    resp.raise_for_status()
    logger.info(f"Row inserted: {data.get('Código del Proyecto')}")
    return True


def send_to_excel(data: dict) -> bool:
    code = data.get("Código del Proyecto", "")
    if not code or code == "No encontrado":
        logger.warning("No valid project code. Skipping.")
        return False
    if check_duplicate(code):
        logger.info(f"Skipping duplicate: {code}")
        return False
    return insert_row(data)
