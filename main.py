import json
import sys
import logging
from pathlib import Path
from extractor import extract_all_data
from downloader import download_pdf, list_local_pdfs, PDFS_FOLDER

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("automation.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def print_report(data: dict, source: str):
    print("\n" + "=" * 60)
    print(f"  ANALYSIS RESULT")
    print(f"  Source: {Path(source).name}")
    print("=" * 60)
    print(f"  Carrera:                {data.get('Carrera', 'N/A')}")
    print(f"  Nombre del Proyecto:    {data.get('Nombre del Proyecto', 'N/A')}")
    print(f"  Código del Proyecto:    {data.get('Código del Proyecto', 'N/A')}")
    print("-" * 60)
    print(f"  Beneficiarios Directos: {data.get('Beneficiarios Directos', 'N/A')}")
    print(f"  Beneficiarios Indirectos: {data.get('Beneficiarios Indirectos', 'N/A')}")
    print("-" * 60)
    print(f"  Total Mujeres:          {data.get('Total Mujeres', 0)}")
    print(f"  Total Hombres:          {data.get('Total Hombres', 0)}")
    print(f"  Discapacidad Mujeres:   {data.get('Discapacidad Mujeres', 0)}")
    print(f"  Discapacidad Hombres:   {data.get('Discapacidad Hombres', 0)}")
    print("-" * 60)
    print(f"  Mestizo:                {data.get('Mestizo', 0)}")
    print(f"  Indígena:               {data.get('Indígena', 0)}")
    print(f"  Afroecuatoriano:        {data.get('Afroecuatoriano', 0)}")
    print(f"  Montubio:               {data.get('Montubio', 0)}")
    print(f"  Blanco:                 {data.get('Blanco', 0)}")
    print(f"  Otros:                  {data.get('Otros', 0)}")
    print("=" * 60 + "\n")


def process_source(source: str) -> list[dict]:
    try:
        pdf_bytes = download_pdf(source)
        reports = extract_all_data(pdf_bytes)
        for i, data in enumerate(reports):
            label = f"{source} [{i+1}]" if len(reports) > 1 else source
            print_report(data, label)
        return reports
    except Exception as e:
        print(f"\n[ERROR] Failed to process '{source}': {e}\n")
        logger.error(f"Error processing {source}: {e}", exc_info=True)
        return []


def process_local_folder() -> list[dict]:
    pdfs = list_local_pdfs()
    if not pdfs:
        print(f"\nNo PDF files found in: {PDFS_FOLDER}")
        print(f"Place your PDF files there and try again.\n")
        return []
    print(f"\nFound {len(pdfs)} PDF(s) in {PDFS_FOLDER}:")
    for i, p in enumerate(pdfs, 1):
        print(f"  {i}. {p.name}")
    confirm = input("\nProcess all? (y/n): ").strip().lower()
    if confirm != "y":
        return []
    results = []
    for p in pdfs:
        reports = process_source(str(p))
        for r in reports:
            results.append({"source": p.name, "data": r})
    return results


def export_to_xlsx(results: list[dict]):
    try:
        import pandas as pd
    except ImportError:
        print("[ERROR] pandas not installed. Run: pip install pandas openpyxl")
        return
    rows = []
    for r in results:
        row = {"Archivo": r["source"]}
        row.update(r["data"])
        rows.append(row)
    df = pd.DataFrame(rows)
    out_path = Path("analysis_results.xlsx")
    df.to_excel(out_path, index=False, engine="openpyxl")
    print(f"\nExported {len(rows)} row(s) to: {out_path.resolve()}\n")


def send_to_online_excel(results: list[dict]):
    try:
        from excel_writer import send_to_excel, get_excel_headers
        from config import EXCEL_FILE_ID
    except Exception as e:
        print(f"[ERROR] Could not load Excel modules: {e}")
        print("Make sure .env is configured with TENANT_ID, CLIENT_ID, CLIENT_SECRET, EXCEL_FILE_ID")
        return

    if not EXCEL_FILE_ID:
        print("[ERROR] EXCEL_FILE_ID not set in .env")
        return

    try:
        cols = get_excel_headers()
        print(f"\nExcel columns found: {cols}")
    except Exception as e:
        print(f"[ERROR] Could not connect to Excel: {e}")
        print("Check your .env credentials and EXCEL_FILE_ID")
        return

    sent = 0
    skipped = 0
    errors = 0
    for r in results:
        data = r["data"]
        code = data.get("Código del Proyecto", "N/A")
        try:
            if send_to_excel(data):
                print(f"  [OK] {code} sent to Excel")
                sent += 1
            else:
                print(f"  [SKIP] {code} duplicate or invalid")
                skipped += 1
        except Exception as e:
            print(f"  [ERROR] {code}: {e}")
            errors += 1

    print(f"\nDone: {sent} sent, {skipped} skipped, {errors} errors\n")


def post_analysis_menu(results: list[dict]):
    while True:
        print("\nWhat would you like to do?")
        print("1. Back to main menu")
        print("2. Export to local XLSX file")
        print("3. Send to online Excel (Graph API)")
        choice = input("Select option: ").strip()
        if choice == "1":
            return
        elif choice == "2":
            export_to_xlsx(results)
            return
        elif choice == "3":
            send_to_online_excel(results)
            return
        else:
            print("Invalid option. Try again.")


def menu():
    print("\n--- Report PDF Analyzer ---")
    print("1. Analyze from URL")
    print("2. Analyze from local file path")
    print("3. Analyze all PDFs in 'pdfs' folder")
    print("4. Analyze multiple URLs (comma-separated)")
    print("5. Exit")
    return input("Select option: ").strip()


def main():
    results = []
    while True:
        choice = menu()
        if choice == "1":
            url = input("Enter PDF URL: ").strip()
            if url:
                reports = process_source(url)
                for r in reports:
                    results.append({"source": url, "data": r})
                if reports:
                    post_analysis_menu(results)
        elif choice == "2":
            path = input("Enter file path (e.g. C:\\Users\\...\\file.pdf): ").strip()
            if path:
                reports = process_source(path)
                for r in reports:
                    results.append({"source": path, "data": r})
                if reports:
                    post_analysis_menu(results)
        elif choice == "3":
            folder_results = process_local_folder()
            if folder_results:
                results.extend(folder_results)
                post_analysis_menu(results)
        elif choice == "4":
            urls = input("Enter URLs comma-separated: ").strip()
            for u in urls.split(","):
                u = u.strip()
                if u:
                    reports = process_source(u)
                    for r in reports:
                        results.append({"source": u, "data": r})
            if results:
                post_analysis_menu(results)
        elif choice == "5":
            break
        else:
            print("Invalid option. Try again.")

    if results:
        save = input("Save results to JSON before exit? (y/n): ").strip().lower()
        if save == "y":
            out = "analysis_results.json"
            with open(out, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"Results saved to {out}")


if __name__ == "__main__":
    main()
