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
