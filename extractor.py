import io
import re
import logging
import pdfplumber

logger = logging.getLogger(__name__)

NOT_FOUND = "No encontrado"


def extract_text_from_pdf(pdf_bytes: bytes) -> dict[int, str]:
    texts = {}
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            texts[i + 1] = page.extract_text() or ""
    return texts


def extract_tables_from_pdf(pdf_bytes: bytes) -> dict[int, list]:
    tables = {}
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            tables[i + 1] = page.extract_tables() or []
    return tables


def _safe_int(val) -> int:
    if val is None:
        return 0
    raw = str(val).replace(",", "").replace(".", "").strip()
    try:
        return int(raw)
    except ValueError:
        return 0


def _extract_after_label(text: str, label_pattern: str) -> str | None:
    patterns = [
        re.compile(label_pattern + r"\s*:\s*\n?\s*(.+)", re.IGNORECASE),
        re.compile(label_pattern + r"\s*:\s*(.+)", re.IGNORECASE),
        re.compile(r"(?i)" + label_pattern + r"\s{0,5}:\s*(.+)"),
    ]
    for pat in patterns:
        match = pat.search(text)
        if match:
            value = match.group(1).strip()
            value = re.split(r"\n", value)[0].strip()
            if value:
                return value
    return None


def _extract_multiline(text: str, label_pattern: str, stop_pattern: str) -> str | None:
    match = re.search(label_pattern + r"\s*:", text, re.IGNORECASE)
    if not match:
        return None
    after = text[match.end():]
    stop_match = re.search(r"\n\s*(?:" + stop_pattern + r")\s*:", after, re.IGNORECASE)
    if not stop_match:
        stop_match = re.search(r"(?:" + stop_pattern + r")\s*:", after, re.IGNORECASE)
    if stop_match:
        block = after[:stop_match.start()]
    else:
        block = after.split("\n\n")[0] if "\n\n" in after else after[:500]
    lines = [l.strip() for l in block.split("\n") if l.strip()]
    skip_starts = [
        r"(?i)^escoja\b", r"(?i)^escriba\b", r"(?i)^seleccione\b",
        r"(?i)^incorporar\b", r"(?i)^en\s+caso\s+de\b",
        r"(?i)^el\s+c.digo\b", r"(?i)^notas?\b",
    ]
    instruction_re = r"(?i)(?:proyecto\s+nuevo,?\s*)?(?:escriba\s+los\s+datos\s+del\s+proyecto\s+en\s+la\s+)?celda\s+a\s+color\s*"
    clean_lines = []
    for line in lines:
        skip = False
        for sp in skip_starts:
            if re.search(sp, line):
                skip = True
                break
        if skip:
            parts = re.split(instruction_re, line, maxsplit=1)
            if len(parts) > 1 and parts[-1].strip():
                clean_lines.append(parts[-1].strip())
        else:
            cleaned = re.sub(instruction_re, "", line).strip()
            if cleaned:
                clean_lines.append(cleaned)
    result = " ".join(clean_lines)
    result = re.sub(r"\s+", " ", result).strip()
    if result:
        return result
    return None


def _find_numeric_near(text: str, label: str) -> int | None:
    patterns = [
        re.compile(label + r"\s+(\d+)", re.IGNORECASE),
        re.compile(label + r"\s*:\s*(\d+)", re.IGNORECASE),
        re.compile(label + r"[^\d]*(\d+)", re.IGNORECASE),
    ]
    for pat in patterns:
        match = pat.search(text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    return None


def _find_numeric_after(text: str, label: str) -> int | None:
    match = re.search(label, text, re.IGNORECASE)
    if not match:
        return None
    after = text[match.end():]
    num_match = re.search(r"[\d.,]+", after[:300])
    if num_match:
        raw = num_match.group().replace(",", "").replace(".", "")
        try:
            return int(raw)
        except ValueError:
            return None
    return None


# --- PAGE 1: HEADER DATA ---

def _parse_carrera(text: str) -> str:
    methods = [
        lambda: _extract_after_label(text, r"Carrera"),
        lambda: _extract_after_label(text, r"Facultad"),
        lambda: _extract_after_label(text, r"departamento"),
    ]
    for m in methods:
        val = m()
        if val and val.lower() not in ("carrera:", "facultad:", ""):
            return val

    match = re.search(r"(?i)carrera\s*\n\s*(.+)", text)
    if match:
        return match.group(1).strip()

    return NOT_FOUND


def _parse_proyecto(text: str) -> str:
    next_fields = r"(?:C.digo del proyecto|Programa|Facultad|Direcci|Docente|Fecha|Per.odo)"
    methods = [
        lambda: _extract_multiline(text, r"Nombre\s+del\s+Proyecto", next_fields),
        lambda: _extract_multiline(text, r"(?i)Proyecto", next_fields),
        lambda: _extract_multiline(text, r"Título\s+del\s+proyecto", next_fields),
    ]
    for m in methods:
        val = m()
        if val and len(val) > 3:
            return val

    match = re.search(r"(?i)proyecto\s*\n\s*(.+)", text)
    if match:
        val = match.group(1).strip()
        if len(val) > 3:
            return val

    return NOT_FOUND


def _parse_codigo(text: str) -> str:
    methods = [
        lambda: _extract_after_label(text, r"C[oó]digo\s+del\s+proyecto"),
        lambda: _extract_after_label(text, r"C[oó]digo\s+del\s+Proyecto"),
        lambda: _extract_after_label(text, r"C[oó]digo"),
    ]
    for m in methods:
        raw = m()
        if raw:
            code = re.search(r"(P\d+\w+)", raw)
            if code:
                return code.group(1)
            if len(raw) < 30 and re.match(r"^[A-Z0-9\-]+$", raw):
                return raw

    match = re.search(r"(?i)c[oó]digo\s+del\s+proyecto\s*\n\s*(.+)", text)
    if match:
        raw = match.group(1).strip()
        code = re.search(r"(P\d+\w+)", raw)
        if code:
            return code.group(1)

    match = re.search(r"P\d{2}[A-Z]{2,}\d{2,}", text)
    if match:
        return match.group(0)

    return NOT_FOUND


# --- PAGE 3: BENEFICIARY DATA ---

def _parse_beneficiarios_directos(text: str) -> int:
    methods = [
        lambda: _find_numeric_near(text, r"BENEFICIARIOS\s+DIRECTOS"),
        lambda: _find_numeric_near(text, r"Beneficiarios\s+Directos"),
        lambda: _find_numeric_after(text, r"BENEFICIARIOS\s+DIRECTOS"),
        lambda: _find_numeric_after(text, r"Beneficiarios\s+directos"),
    ]
    for m in methods:
        val = m()
        if val is not None:
            return val

    match = re.search(r"(?i)directos\s*\n?\s*(\d+)", text)
    if match:
        return int(match.group(1))

    return 0


def _parse_beneficiarios_indirectos(text: str) -> int:
    methods = [
        lambda: _find_numeric_near(text, r"BENEFICIARIOS\s+INDIRECTOS"),
        lambda: _find_numeric_near(text, r"Beneficiarios\s+Indirectos"),
        lambda: _find_numeric_after(text, r"BENEFICIARIOS\s+INDIRECTOS"),
        lambda: _find_numeric_after(text, r"Beneficiarios\s+indirectos"),
    ]
    for m in methods:
        val = m()
        if val is not None:
            return val

    match = re.search(r"(?i)indirectos\s*\n?\s*(\d+)", text)
    if match:
        return int(match.group(1))

    return 0


# --- PAGE 6: GENDER / DISABILITY / ETHNICITY ---

def _parse_total_row(table) -> dict:
    result = {"Total Mujeres": 0, "Total Hombres": 0,
              "Discapacidad Mujeres": 0, "Discapacidad Hombres": 0}
    for row in table:
        if not row or len(row) < 3:
            continue
        cell0 = str(row[0] or "").strip().upper()
        if cell0 == "TOTAL":
            ncols = len(row)
            if ncols >= 11:
                result["Total Mujeres"] = sum(_safe_int(row[i]) for i in range(1, 6))
                result["Total Hombres"] = sum(_safe_int(row[i]) for i in range(6, 11))
                result["Discapacidad Mujeres"] = _safe_int(row[5])
                result["Discapacidad Hombres"] = _safe_int(row[10])
            elif ncols >= 8:
                result["Total Mujeres"] = _safe_int(row[1])
                result["Total Hombres"] = _safe_int(row[6])
                result["Discapacidad Mujeres"] = _safe_int(row[5])
                result["Discapacidad Hombres"] = _safe_int(row[min(10, ncols-1)])
            elif ncols >= 3:
                result["Total Mujeres"] = _safe_int(row[1])
                result["Total Hombres"] = _safe_int(row[2])
            return result
    return result


def _parse_ethnicity_table(table) -> dict:
    result = {
        "Mestizo": 0, "Indígena": 0, "Afroecuatoriano": 0,
        "Montubio": 0, "Blanco": 0, "Otros": 0,
    }
    eth_map = {
        "mestizo": "Mestizo", "indigena": "Indígena", "indígena": "Indígena",
        "afroecuatoriano": "Afroecuatoriano", "montubio": "Montubio",
        "blanco": "Blanco", "otros": "Otros",
    }

    for row in table:
        if not row or len(row) < 8:
            continue
        cell5 = str(row[5] or "").strip()
        col6 = _safe_int(row[6])
        col7 = _safe_int(row[7])

        if "\n" in cell5 and "AUTOIDENTIFICACI" in cell5.upper():
            nums6 = re.findall(r"\d+", str(row[6] or ""))
            nums7 = re.findall(r"\d+", str(row[7] or ""))
            h_val = int(nums6[0]) if nums6 else 0
            m_val = int(nums7[0]) if nums7 else 0
            result["Mestizo"] = h_val + m_val
            logger.info(f"Combined ethnicity cell: H={h_val}, M={m_val}")
        elif cell5.lower() in eth_map:
            key = eth_map[cell5.lower()]
            result[key] = col6 + col7

    return result


def _parse_ethnicity_text(text: str) -> dict:
    result = {
        "Mestizo": 0, "Indígena": 0, "Afroecuatoriano": 0,
        "Montubio": 0, "Blanco": 0, "Otros": 0,
    }
    eth_names = ["Mestizo", "Indigena", "Indígena", "Afroecuatoriano",
                 "Montubio", "Blanco", "Otros"]

    for name in eth_names:
        match = re.search(name + r"\s+(\d+)\s+(\d+)", text, re.IGNORECASE)
        if match:
            key = "Indígena" if name in ("Indigena", "Indígena") else name
            result[key] = int(match.group(1)) + int(match.group(2))

    return result


def _fallback_gender_from_text(text: str) -> dict:
    result = {"Total Mujeres": 0, "Total Hombres": 0,
              "Discapacidad Mujeres": 0, "Discapacidad Hombres": 0}

    match = re.search(r"(?i)TOTAL\s+([\d\s]+)", text)
    if match:
        nums = re.findall(r"\d+", match.group(1))
        if len(nums) >= 10:
            vals = [int(n) for n in nums[:10]]
            result["Total Mujeres"] = sum(vals[:5])
            result["Total Hombres"] = sum(vals[5:10])
            result["Discapacidad Mujeres"] = vals[4]
            result["Discapacidad Hombres"] = vals[9]

    return result


def parse_page6_data(pdf_bytes: bytes) -> dict:
    logger.info("Parsing gender/ethnicity data (searching all pages).")
    all_tables = extract_tables_from_pdf(pdf_bytes)
    pages = extract_text_from_pdf(pdf_bytes)

    result = {
        "Total Mujeres": 0,
        "Total Hombres": 0,
        "Discapacidad Mujeres": 0,
        "Discapacidad Hombres": 0,
        "Mestizo": 0,
        "Indígena": 0,
        "Afroecuatoriano": 0,
        "Montubio": 0,
        "Blanco": 0,
        "Otros": 0,
    }

    for page_num, tables in all_tables.items():
        for table in tables:
            total = _parse_total_row(table)
            if any(total[k] != 0 for k in total):
                for k in total:
                    if total[k] != 0:
                        result[k] = total[k]

            eth = _parse_ethnicity_table(table)
            if any(eth[k] != 0 for k in eth):
                for k in eth:
                    if eth[k] != 0:
                        result[k] = eth[k]

        if result["Total Mujeres"] != 0 or result["Mestizo"] != 0:
            break

    if result["Total Mujeres"] == 0 and result["Total Hombres"] == 0:
        for page_num, text in pages.items():
            fallback = _fallback_gender_from_text(text)
            if any(fallback[k] != 0 for k in fallback):
                for k in fallback:
                    if fallback[k] != 0:
                        result[k] = fallback[k]
                break

    if result["Mestizo"] == 0:
        for page_num, text in pages.items():
            eth_text = _parse_ethnicity_text(text)
            if any(eth_text[k] != 0 for k in eth_text):
                for k in eth_text:
                    if eth_text[k] != 0:
                        result[k] = eth_text[k]
                break

    logger.info(f"Gender/ethnicity final: {result}")
    return result


# --- MAIN EXTRACTION ---

def _parse_beneficiarios_all_pages(pages: dict[int, str]) -> tuple[int, int]:
    for page_num, text in pages.items():
        d = _parse_beneficiarios_directos(text)
        i = _parse_beneficiarios_indirectos(text)
        if d != 0 or i != 0:
            return d, i
    return 0, 0


def _find_report_pages(pages: dict[int, str]) -> list[int]:
    report_starts = []
    for page_num, text in pages.items():
        if re.search(r"(?i)DATOS\s+GENERALES", text):
            report_starts.append(page_num)
    return report_starts


def _extract_single_report(pages: dict[int, str], start_page: int, end_page: int) -> dict:
    report_text = ""
    for p in range(start_page, end_page + 1):
        if p in pages:
            report_text += pages[p] + "\n"

    result = {}
    result["Carrera"] = _parse_carrera(report_text)
    result["Nombre del Proyecto"] = _parse_proyecto(report_text)
    result["Código del Proyecto"] = _parse_codigo(report_text)

    d = _parse_beneficiarios_directos(report_text)
    i = _parse_beneficiarios_indirectos(report_text)
    result["Beneficiarios Directos"] = d
    result["Beneficiarios Indirectos"] = i

    gender = {"Total Mujeres": 0, "Total Hombres": 0,
              "Discapacidad Mujeres": 0, "Discapacidad Hombres": 0,
              "Mestizo": 0, "Indígena": 0, "Afroecuatoriano": 0,
              "Montubio": 0, "Blanco": 0, "Otros": 0}

    all_tables = extract_tables_from_pdf(pdf_bytes)
    for p in range(start_page, end_page + 1):
        if p not in all_tables:
            continue
        for table in all_tables[p]:
            total = _parse_total_row(table)
            if any(total[k] != 0 for k in total):
                for k in total:
                    if total[k] != 0:
                        gender[k] = total[k]
            eth = _parse_ethnicity_table(table)
            if any(eth[k] != 0 for k in eth):
                for k in eth:
                    if eth[k] != 0:
                        gender[k] = eth[k]

    if gender["Total Mujeres"] == 0 and gender["Total Hombres"] == 0:
        for p in range(start_page, end_page + 1):
            if p in pages:
                fb = _fallback_gender_from_text(pages[p])
                if any(fb[k] != 0 for k in fb):
                    for k in fb:
                        if fb[k] != 0:
                            gender[k] = fb[k]
                    break

    if gender["Mestizo"] == 0:
        for p in range(start_page, end_page + 1):
            if p in pages:
                et = _parse_ethnicity_text(pages[p])
                if any(et[k] != 0 for k in et):
                    for k in et:
                        if et[k] != 0:
                            gender[k] = et[k]
                    break

    result.update(gender)
    return result


pdf_bytes = b""


def extract_all_data(pdf_data: bytes) -> list[dict]:
    global pdf_bytes
    pdf_bytes = pdf_data
    pages = extract_text_from_pdf(pdf_data)

    report_starts = _find_report_pages(pages)

    if not report_starts:
        result = {}
        result["Carrera"] = _parse_carrera(pages.get(1, ""))
        result["Nombre del Proyecto"] = _parse_proyecto(pages.get(1, ""))
        result["Código del Proyecto"] = _parse_codigo(pages.get(1, ""))
        bd, bi = _parse_beneficiarios_all_pages(pages)
        result["Beneficiarios Directos"] = bd
        result["Beneficiarios Indirectos"] = bi
        result.update(parse_page6_data(pdf_data))
        return [result]

    reports = []
    max_page = max(pages.keys())
    for i, start in enumerate(report_starts):
        end = report_starts[i + 1] - 1 if i + 1 < len(report_starts) else max_page
        report = _extract_single_report(pages, start, end)
        if report.get("Carrera") != NOT_FOUND or report.get("Beneficiarios Directos", 0) > 0:
            reports.append(report)

    if not reports:
        result = {}
        result["Carrera"] = _parse_carrera(pages.get(1, ""))
        result["Nombre del Proyecto"] = _parse_proyecto(pages.get(1, ""))
        result["Código del Proyecto"] = _parse_codigo(pages.get(1, ""))
        bd, bi = _parse_beneficiarios_all_pages(pages)
        result["Beneficiarios Directos"] = bd
        result["Beneficiarios Indirectos"] = bi
        result.update(parse_page6_data(pdf_data))
        reports.append(result)

    return reports
