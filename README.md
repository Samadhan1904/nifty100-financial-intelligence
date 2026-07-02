<div align="center">

# 📊 Nifty 100 Financial Intelligence Platform

### A production-grade financial analytics platform for 92 Nifty 100 companies
### Built during Data Analytics Internship — June 2026

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30-red?logo=streamlit)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green?logo=fastapi)
![SQLite](https://img.shields.io/badge/SQLite-3.x-blue?logo=sqlite)
![Status](https://img.shields.io/badge/Status-In%20Progress-orange)
![Sprint](https://img.shields.io/badge/Sprint-1%20of%206-yellow)

</div>

---

## 🎯 What is this project?

This platform transforms raw financial Excel data into a complete
financial intelligence system — think of it as a self-built
mini version of **Screener.in**.

**Input:** 12 Excel files with financial statements of 92 Nifty 100 companies

**Output:** Interactive dashboard, stock screener, PDF reports, REST API

---

## 📸 Project Overview

| Metric | Value |
|--------|-------|
| Companies covered | 92 Nifty 100 companies |
| Financial KPIs | 50+ computed metrics |
| Years of data | FY 2010 – 2024 (14 years) |
| Total data points | 11,000+ |
| Modules built | 12 |
| Total features | 120+ |
| Sprint duration | 45 days / 6 sprints |

---

## 🏗️ Project Architecture

```
Raw Excel Files (12)
       ↓
ETL Pipeline (Sprint 1)
       ↓
SQLite Database — nifty100.db (10 tables)
       ↓
Financial Ratio Engine — 50+ KPIs (Sprint 2)
       ↓
┌──────────────────────────────────────────┐
│  Screener  │  Peer Engine  │  Sector     │ (Sprint 3)
└──────────────────────────────────────────┘
       ↓
Streamlit Dashboard — 8 screens (Sprint 4)
       ↓
PDF Reports + NLP + Cash Flow (Sprint 5)
       ↓
FastAPI (16 endpoints) + ML Clustering (Sprint 6)
```

---

## 📦 Dataset

### Core Files (Real Data)
| File | Records | Description |
|------|---------|-------------|
| companies.xlsx | 92 | Master company list |
| profitandloss.xlsx | 1,276 | Annual P&L FY2010–2024 |
| balancesheet.xlsx | 1,312 | Annual Balance Sheets |
| cashflow.xlsx | 1,187 | Annual Cash Flows |
| analysis.xlsx | 20 | Pre-computed growth metrics |
| documents.xlsx | 1,585 | Annual report PDF links |
| prosandcons.xlsx | 16 | Qualitative insights |

### Supplementary Files (Created)
| File | Records | Description |
|------|---------|-------------|
| sectors.xlsx | 92 | GICS-style sector mapping |
| stock_prices.xlsx | 5,520 | Monthly OHLCV (simulated) |
| market_cap.xlsx | 552 | Annual valuation multiples |
| financial_ratios.xlsx | 1,184 | Pre-computed KPIs |
| peer_groups.xlsx | 56 | 11 peer group definitions |

---

## 🚀 6 Sprint Plan

| Sprint | Days | Focus | Status |
|--------|------|-------|--------|
| Sprint 1 | 1–7 | Data Foundation & ETL | 🔄 In Progress |
| Sprint 2 | 8–14 | Financial Ratio Engine | ⏳ Pending |
| Sprint 3 | 15–21 | Screener & Peer Comparison | ⏳ Pending |
| Sprint 4 | 22–28 | Streamlit Dashboard | ⏳ Pending |
| Sprint 5 | 29–35 | Reports & NLP | ⏳ Pending |
| Sprint 6 | 36–45 | API, ML & QA | ⏳ Pending |

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11 |
| Data Processing | pandas, numpy, openpyxl |
| Database | SQLite 3.x |
| Analytics | scipy, scikit-learn |
| Dashboard | Streamlit |
| API | FastAPI + Uvicorn |
| PDF Reports | ReportLab |
| Charts | Plotly, Matplotlib |
| NLP | NLTK, regex |
| Testing | pytest |
| Code Quality | black, ruff |

---

## 📁 Folder Structure

```
nifty100/
├── data/
│   ├── raw/              ← 7 core Excel files
│   └── supporting/       ← 5 supplementary files
├── src/
│   ├── etl/              ← loader, normaliser, validator
│   ├── analytics/        ← ratio engine, screener, peer
│   ├── nlp/              ← text parser, pros/cons generator
│   ├── dashboard/        ← Streamlit app (8 screens)
│   ├── api/              ← FastAPI (16 endpoints)
│   └── reports/          ← PDF tearsheet generator
├── db/
│   └── schema.sql        ← 10-table SQLite schema
├── tests/                ← 60+ pytest tests
├── config/               ← settings, screener thresholds
├── reports/              ← generated PDFs and charts
└── output/               ← generated CSVs
```

---

## ⚙️ Setup & Installation

### 1. Clone the repository
```cmd
git clone https://github.com/Samadhan1904/nifty100-financial-intelligence.git
cd nifty100-financial-intelligence
```

### 2. Create virtual environment
```cmd
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies
```cmd
pip install -r requirements.txt
```

### 4. Configure environment
```cmd
copy config\.env.template .env
```

### 5. Add your Excel data files
```
Place core Excel files in:     data\raw\
Place supporting files in:     data\supporting\
```

---

## 🏃 Running the Project

```cmd
# Load all data into database
make load

# Compute financial ratios
make ratios

# Run test suite
make test

# Start dashboard (opens at http://localhost:8501)
make dashboard

# Start API server (opens at http://localhost:8000/docs)
make api
```

---

## 📊 Key Features

### ✅ Sprint 1 — Data Foundation
- ETL pipeline loading 12 Excel files
- 16 data quality validation rules
- SQLite database with 10 tables
- Year and ticker normalisation

### ⏳ Sprint 2 — Financial Ratio Engine
- 50+ KPIs including ROE, ROCE, D/E, FCF
- CAGR computation (3yr, 5yr, 10yr)
- Capital allocation pattern detection

### ⏳ Sprint 3 — Screener & Peer Analysis
- 18 filter parameters
- 6 preset screeners (Quality, Value, Growth...)
- 11 peer group comparisons with radar charts

### ⏳ Sprint 4 — Dashboard
- 8-screen Streamlit web application
- Company profile, screener, peer comparison
- Sector analysis, trend charts

### ⏳ Sprint 5 — Reports & Intelligence
- 92 company PDF tearsheets
- Auto-generated pros/cons using KPI rules
- Cash flow intelligence module

### ⏳ Sprint 6 — API & ML
- 16 REST API endpoints
- KMeans clustering (5 clusters)
- 60+ automated tests

---

## 📈 Sample KPIs Computed

| KPI | Formula | Benchmark |
|-----|---------|-----------|
| ROE | net_profit / equity × 100 | >15% good |
| ROCE | EBIT / capital_employed × 100 | >15% good |
| D/E Ratio | borrowings / equity | <1.0 healthy |
| FCF | CFO + CFI | >0 preferred |
| Revenue CAGR | (end/start)^(1/n) − 1 | >10% healthy |
| OPM | operating_profit / sales × 100 | >15% good |

---

## 🧪 Testing

```cmd
# Run all tests
pytest tests/ -v

# Run specific category
pytest tests/etl/ -v
pytest tests/kpi/ -v
pytest tests/api/ -v

# Generate HTML report
pytest tests/ --html=reports/pytest_report.html
```

---

## 📅 Daily Progress

| Day | Task | Status |
|-----|------|--------|
| Day 1 | Environment setup, folder structure | ✅ Done |
| Day 2 | Normaliser + Excel loader | ⏳ |
| Day 3 | Schema validator (16 DQ rules) | ⏳ |
| Day 4 | SQLite schema (10 tables) | ⏳ |
| Day 5 | Full data load (12 files) | ⏳ |
| Day 6 | Data quality review | ⏳ |
| Day 7 | Exploratory queries + Sprint review | ⏳ |

---

## 👨‍💻 Author

**Samadhan**
Data Analytics Intern — June 2026
- GitHub: [@Samadhan1904](https://github.com/Samadhan1904)
- LinkedIn: [Add your LinkedIn URL here](https://www.linkedin.com/in/pranjal-dhore-084b12292/)

---

## 📄 License

This project is for internal use only.
Data Analytics Division — Internship Project 2026

---

<div align="center">
⭐ Star this repo if you find it helpful!
</div>