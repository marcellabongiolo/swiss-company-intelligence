# Swiss Company Intelligence 🇨🇭

A Python-first portfolio project for **screening, benchmarking and prioritizing Swiss companies**.

The project solves a realistic business problem:

> **Given a portfolio of Swiss companies, which firms deserve analyst attention first because of unusual financial/operational signals?**

It combines deterministic business rules with statistical anomaly detection and produces an explainable priority score.

> **Important:** the included CSV is **synthetic demo data**. Company names are used only to make the example recognizable; the financial figures are not reported company results.

## Why this is a strong Python portfolio project

- `pandas` data pipelines
- typed Python models
- validation and normalization
- feature engineering
- robust z-score anomaly detection
- explainable risk scoring
- CLI with `typer`
- terminal UX with `rich`
- report generation
- unit tests with `pytest`
- linting with `ruff`
- GitHub Actions CI
- clean `src/` package layout

## Problem solved

Analysts often receive a spreadsheet with dozens or hundreds of companies. Looking at every row manually is slow.

This package:

1. validates the company dataset;
2. normalizes financial and operating indicators;
3. benchmarks each company against its sector;
4. detects unusual values with robust statistics;
5. calculates an explainable **attention score from 0 to 100**;
6. lists the main reasons behind each score;
7. exports a ranked CSV report.

The score is a **screening heuristic**, not investment advice or a credit rating.

## Quick start

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
swiss-intel analyze data/sample_companies.csv
```

## Python usage

```python
from swiss_company_intel.analyzer import CompanyAnalyzer
from swiss_company_intel.io import load_companies

df = load_companies("data/sample_companies.csv")
result = CompanyAnalyzer().analyze(df)
print(result.head())
```

## Swiss public-data expansion

A production version can enrich the pipeline with official Swiss sources such as the Federal Statistical Office (FSO/BFS), Swiss UID register, Zefix where permitted, and cantonal/open-government datasets.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

## License

MIT


## Interactive dashboard

The repository includes a Streamlit dashboard for exploring the attention ranking visually.

```bash
streamlit run src/swiss_company_intel/dashboard.py
```

The dashboard supports CSV uploads, portfolio metrics, company ranking, sector summaries and a live connection check to the Swiss Federal Statistical Office (FSO/BFS) STAT-TAB API.

### Dashboard workflow

1. Start the dashboard and optionally upload a CSV. Without an upload, it uses the bundled synthetic example dataset.
2. Optionally upload a JSON file of scoring weights; use **Active scoring weights** to inspect the configuration.
3. Use **Search company name** (case-insensitive), **Canton**, **Sector**, **Priority band**, and **Minimum attention score** together to narrow the results.
4. Review the company drill-down, explanations, rankings, and sector overview. **Download filtered results (CSV)** exports only the current filtered rows.
5. Choose **Save analysis snapshot** to persist the **complete analyzed report** (not just the filtered subset) to the local SQLite database at `data/analysis_history.db`.
6. Under **Browse saved analysis runs**, select a run to inspect or download its historical scores. Historical snapshots are not recalculated when scoring weights or input data change.

CSV uploads must include company, canton, sector, and the numeric fields shown in `data/sample_companies.csv`. The importer validates missing/duplicate columns, Swiss canton codes, numeric values, and percentage bounds. Uploaded CSV data is validated in memory without a shared temporary file.

### Windows PowerShell setup

From the repository folder, run:

```powershell
py -3 -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -e ".[dev]"
.\\.venv\\Scripts\\python.exe -m streamlit run src/swiss_company_intel/dashboard.py
```

This avoids requiring PowerShell script-execution policy changes. The dashboard opens locally at `http://localhost:8501` by default. The SQLite history is stored on the machine/container running the dashboard; it is not automatically synchronized between installations. Do not use the synthetic demo figures for real-world credit or investment decisions.

## Official FSO / BFS provider

`src/swiss_company_intel/providers/bfs.py` contains a small, testable PxWeb client. The integration is intentionally decoupled from the scoring engine so official Swiss data can later be cached, transformed or swapped without rewriting the analytics layer.

```python
from swiss_company_intel.providers.bfs import BFSClient

client = BFSClient()
metadata = client.get_metadata()
print(client.variable_summary(metadata))
```

## Docker

Build and run the dashboard with Docker:

```bash
docker build -t swiss-company-intelligence .
docker run --rm -p 8501:8501 swiss-company-intelligence
```

Or use Docker Compose:

```bash
docker compose up --build
```

Docker Compose persists saved analysis snapshots in the named `analysis-history` volume, including across container recreation. The container runs as an unprivileged user. The standalone `docker run --rm` example does **not** persist history unless you mount a writable volume at `/app/data`.

Then open `http://localhost:8501`.


## Configurable scoring weights

The default score weights can be overridden without changing source code.

Use the included example configuration:

```bash
swiss-intel analyze data/sample_companies.csv \
  --weights config/weights.example.json
```

The JSON file must provide all seven weights and they must add up to 100:

```json
{
  "leverage": 18,
  "liquidity": 16,
  "concentration": 18,
  "late_payment": 14,
  "revenue_decline": 12,
  "employee_decline": 8,
  "anomaly": 14
}
```

The Streamlit dashboard also accepts an optional scoring-weights JSON file and displays the active configuration.


## Official FSO enterprise-data ingestion

The project can fetch a reproducible subset of official Swiss Federal Statistical Office
(FSO/BFS) enterprise statistics and convert the PxWeb JSON-stat2 response into a tidy
pandas DataFrame.

```python
from swiss_company_intel.providers.bfs import BFSClient

client = BFSClient()
official = client.latest_enterprise_statistics()

print(official.head())
print(official.attrs["source"])
```

The provider reads the cube metadata first, selects the latest available year, queries
valid dimension values and caches identical API queries for 15 minutes by default.

Official source:
- Swiss Federal Statistical Office (FSO/BFS), STAT-TAB / PxWeb
- Table: enterprises and employment by economic activity, enterprise-size group,
  group type and year
- https://www.pxweb.bfs.admin.ch/pxweb/en/px-x-0606010000_102/px-x-0606010000_102/px-x-0606010000_102.px/

The official aggregate dataset is kept separate from the synthetic company-level demo
dataset because the two sources have different units and schemas.


## REST API

Run the FastAPI service locally:

```bash
uvicorn swiss_company_intel.api:app --reload
```

Main endpoints:

- `GET /health` — service health check
- `POST /score` — calculate an explainable score for one set of metrics
- `POST /analyze` — analyze and rank a portfolio of companies
- `GET /docs` — interactive OpenAPI documentation generated by FastAPI

The single-company `/score` endpoint defaults the sector anomaly component to zero unless
`sector_anomaly_strength` is supplied. Portfolio analysis calculates sector-relative
anomalies from the submitted companies.


## Test coverage

Run the full test suite with coverage locally:

```bash
pytest -q --cov=swiss_company_intel --cov-report=term-missing
```

The project enforces a minimum total coverage of **60%**. GitHub Actions runs the
coverage check on Python 3.11, 3.12 and 3.13 and writes the coverage table to the
workflow job summary.
