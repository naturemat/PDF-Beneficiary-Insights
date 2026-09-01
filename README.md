# Report PDF Analyzer

Extract specific data from PDF project reports and export to Excel.

## Features

- Extract header data (Carrera, Proyecto, Código)
- Extract beneficiary counts (Directos, Indirectos)
- Extract gender breakdown (Mujeres, Hombres, Discapacidad)
- Extract ethnicity data (Mestizo, Indígena, Afroecuatoriano, Montubio, Blanco, Otros)
- Process single or multiple PDFs
- Export to local XLSX or online Excel via Microsoft Graph API
- Handles different PDF table layouts automatically

## Requirements

- Python 3.9+
- pip

## Installation

```bash
git clone https://github.com/yourusername/report_automation.git
cd report_automation
pip install -r requirements.txt
```

## Configuration

### For local use only (no SharePoint)

No configuration needed. Just run the script.

### For SharePoint/OneDrive access

1. Go to [Azure Portal > App Registrations](https://portal.azure.com)
2. Click **New registration**
3. Name: `Report Analyzer`
4. Click **Register**
5. Copy the **Application (client) ID** and **Directory (tenant) ID**
6. Go to **Certificates & secrets** → **New client secret** → copy the value
7. Go to **API permissions** → **Add a permission** → **Microsoft Graph** → **Application permissions**
8. Add `Files.ReadWrite.All`
9. Click **Grant admin consent**

### Environment Variables

Create a `.env` file in the project root:

```env
# Microsoft Graph API (required for SharePoint URLs)
TENANT_ID=your_tenant_id
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret

# Excel file ID (for online Excel export)
EXCEL_FILE_ID=your_excel_file_id
EXCEL_WORKSHEET_NAME=Sheet1
EXCEL_TABLE_NAME=Table1
```

To find the `EXCEL_FILE_ID`:
- Open your Excel file in OneDrive/SharePoint
- The URL will look like: `https://tenant.sharepoint.com/personal/.../_layouts/15/doc.aspx?sourcedoc={FILE_ID}&...`
- Copy the `FILE_ID` part

## Usage

```bash
python main.py
```

```
--- Report PDF Analyzer ---
1. Analyze from URL
2. Analyze from local file path
3. Analyze all PDFs in 'pdfs' folder
4. Analyze multiple URLs (comma-separated)
5. Exit
```

### Option 1: Analyze from URL

Enter a direct PDF URL or SharePoint URL (requires Graph API config).

### Option 2: Analyze from local file

Enter the full path to a PDF file:
```
C:\Users\...\Documents\report.pdf
```

### Option 3: Batch process (Recommended)

1. Place all PDF files in the `pdfs/` folder
2. Select option 3
3. Confirm to process all files

### Option 4: Multiple URLs

Enter comma-separated URLs:
```
https://example.com/file1.pdf, https://example.com/file2.pdf
```

## Output

After analysis, choose:

- **Back to main menu** — return to main menu
- **Export to local XLSX** — saves `analysis_results.xlsx` in the project folder
- **Send to online Excel** — sends data to your shared Excel via Graph API

### Example Output

```
============================================================
  ANALYSIS RESULT
  Source: report.pdf
============================================================
  Carrera:                CIENCIAS ADMINISTRATIVAS
  Nombre del Proyecto:    EN LA COMUNIDAD DE SAN PEDRO DE CAYAMBE
  Código del Proyecto:    P6ADM01
------------------------------------------------------------
  Beneficiarios Directos: 75
  Beneficiarios Indirectos: 300
------------------------------------------------------------
  Total Mujeres:          46
  Total Hombres:          29
  Discapacidad Mujeres:   0
  Discapacidad Hombres:   0
------------------------------------------------------------
  Mestizo:                62
  Indígena:               13
  Afroecuatoriano:        0
  Montubio:               0
  Blanco:                 0
  Otros:                  0
============================================================
```

## Project Structure

```
report_automation/
├── main.py              # CLI entry point
├── extractor.py         # PDF data extraction (pdfplumber)
├── downloader.py        # URL/file download with SharePoint support
├── auth.py              # Microsoft Graph API authentication
├── excel_writer.py      # Write to online Excel via Graph API
├── config.py            # Environment variable loader
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
├── pdfs/                # Place PDF files here
└── README.md
```

## How It Works

1. **Download** — PDF from URL (direct/SharePoint) or local file
2. **Extract** — `pdfplumber` parses tables and text from each page
3. **Parse** — Regex patterns find labels and extract values
4. **Display** — Results shown in terminal
5. **Export** — To local XLSX or online Excel

### Extraction Methods

Each field uses multiple fallback strategies:

| Field | Methods |
|-------|---------|
| Carrera | "Carrera:", "Facultad:", line-after pattern |
| Proyecto | Multi-line extraction with instruction filtering |
| Código | Pattern matching `P\d+\w+`, text extraction |
| Beneficiarios | Numeric extraction near label, searches all pages |
| Gender | Table column sum, text fallback |
| Ethnicity | Table row extraction, combined cell detection |

## Limitations

- SharePoint `:b:` URLs require authentication (configure `.env` or download manually)
- Multi-column PDF layouts may garble project names
- OCR-based PDFs (scanned images) are not supported

## License

MIT
