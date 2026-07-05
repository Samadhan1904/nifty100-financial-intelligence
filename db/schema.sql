-- ============================================================
-- Nifty 100 Financial Intelligence Platform
-- SQLite Database Schema — 10 Tables
--
-- Author: Samadhan
-- Sprint: 1 — Day 4
--
-- How to run:
--   python src/etl/db_setup.py
-- ============================================================

-- Enable foreign key enforcement
-- SQLite does NOT enforce FK by default — this turns it ON
PRAGMA foreign_keys = ON;


-- ============================================================
-- TABLE 1: companies
-- Master reference table for all 92 Nifty 100 companies.
-- Primary key for the ENTIRE platform.
-- All other tables link back to this via company_id.
-- ============================================================

CREATE TABLE IF NOT EXISTS companies (
    id              TEXT    PRIMARY KEY,    -- NSE ticker e.g. "TCS"
    company_logo    TEXT,                   -- URL to logo image
    company_name    TEXT    NOT NULL,       -- Full legal name
    chart_link      TEXT,                   -- TradingView chart URL
    about_company   TEXT,                   -- Business description
    website         TEXT,                   -- Official website URL
    nse_profile     TEXT,                   -- NSE India profile URL
    bse_profile     TEXT,                   -- BSE India profile URL
    face_value      REAL,                   -- Share face value in Rs
    book_value      REAL,                   -- Book value per share
    roce_percentage REAL,                   -- Pre-computed ROCE %
    roe_percentage  REAL                    -- Pre-computed ROE %
);


-- ============================================================
-- TABLE 2: profitandloss
-- Annual Profit & Loss statements FY2010-2024.
-- ~1,276 rows (92 companies x ~14 years)
-- Primary key: (company_id, year)
-- ============================================================

CREATE TABLE IF NOT EXISTS profitandloss (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id          TEXT    NOT NULL,
    year                TEXT    NOT NULL,   -- Format: YYYY-MM e.g. "2023-03"
    sales               REAL,               -- Net revenue in Cr
    expenses            REAL,               -- Total operating expenses in Cr
    operating_profit    REAL,               -- EBITDA in Cr
    opm_percentage      REAL,               -- Operating profit margin %
    other_income        REAL,               -- Non-operating income in Cr
    interest            REAL,               -- Finance costs in Cr
    depreciation        REAL,               -- D&A in Cr
    profit_before_tax   REAL,               -- PBT in Cr
    tax_percentage      REAL,               -- Effective tax rate %
    net_profit          REAL,               -- PAT in Cr
    eps                 REAL,               -- Earnings per share in Rs
    dividend_payout     REAL,               -- Dividend payout ratio %

    -- Composite unique constraint
    UNIQUE (company_id, year),

    -- Foreign key to companies
    FOREIGN KEY (company_id) REFERENCES companies(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


-- ============================================================
-- TABLE 3: balancesheet
-- Annual Balance Sheets FY2010-2024.
-- ~1,312 rows
-- ============================================================

CREATE TABLE IF NOT EXISTS balancesheet (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id          TEXT    NOT NULL,
    year                TEXT    NOT NULL,
    equity_capital      REAL,               -- Paid-up share capital in Cr
    reserves            REAL,               -- Reserves and surplus in Cr
    borrowings          REAL,               -- Total debt in Cr
    other_liabilities   REAL,               -- Trade payables + other CL in Cr
    total_liabilities   REAL,               -- Sum of all liabilities in Cr
    fixed_assets        REAL,               -- Net fixed assets in Cr
    cwip                REAL,               -- Capital work in progress in Cr
    investments         REAL,               -- Long-term investments in Cr
    other_asset         REAL,               -- Current + other assets in Cr
    total_assets        REAL,               -- Sum of all assets in Cr

    UNIQUE (company_id, year),

    FOREIGN KEY (company_id) REFERENCES companies(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


-- ============================================================
-- TABLE 4: cashflow
-- Annual Cash Flow Statements FY2010-2024.
-- ~1,187 rows
-- ============================================================

CREATE TABLE IF NOT EXISTS cashflow (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id           TEXT    NOT NULL,
    year                 TEXT    NOT NULL,
    operating_activity   REAL,              -- CFO in Cr
    investing_activity   REAL,              -- CFI in Cr
    financing_activity   REAL,              -- CFF in Cr
    net_cash_flow        REAL,              -- CFO + CFI + CFF in Cr

    UNIQUE (company_id, year),

    FOREIGN KEY (company_id) REFERENCES companies(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


-- ============================================================
-- TABLE 5: analysis
-- Pre-computed growth metrics (partial — ~8 companies only).
-- Sprint 2 computes proper metrics for all 92 companies.
-- ============================================================

CREATE TABLE IF NOT EXISTS analysis (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id              TEXT    NOT NULL UNIQUE,
    compounded_sales_growth TEXT,           -- e.g. "10 Years: 21%"
    compounded_profit_growth TEXT,          -- e.g. "5 Years: 6%"
    stock_price_cagr        TEXT,           -- e.g. "10 Years: 15%"
    roe                     TEXT,           -- e.g. "10 Years: 17%"

    FOREIGN KEY (company_id) REFERENCES companies(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


-- ============================================================
-- TABLE 6: documents
-- Annual report PDF links from BSE India.
-- ~1,585 rows
-- ============================================================

CREATE TABLE IF NOT EXISTS documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id    TEXT    NOT NULL,
    year          INTEGER NOT NULL,         -- Calendar year e.g. 2024
    annual_report TEXT,                     -- PDF URL on BSE India

    UNIQUE (company_id, year),

    FOREIGN KEY (company_id) REFERENCES companies(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


-- ============================================================
-- TABLE 7: prosandcons
-- Qualitative investment insights (partial — ~8 companies).
-- Sprint 5 auto-generates for all 92 companies.
-- ============================================================

CREATE TABLE IF NOT EXISTS prosandcons (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  TEXT    NOT NULL,
    pros        TEXT,                       -- Positive observation
    cons        TEXT,                       -- Risk observation

    FOREIGN KEY (company_id) REFERENCES companies(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


-- ============================================================
-- TABLE 8: sectors
-- GICS-style sector mapping for all 92 companies.
-- Created manually — covers all 92 companies.
-- ============================================================

CREATE TABLE IF NOT EXISTS sectors (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id          TEXT    NOT NULL UNIQUE,
    broad_sector        TEXT    NOT NULL,   -- e.g. "Information Technology"
    sub_sector          TEXT,               -- e.g. "IT Services"
    index_weight_pct    REAL,               -- Estimated Nifty 100 weight %
    market_cap_category TEXT,               -- "Large Cap" or "Mid Cap"

    FOREIGN KEY (company_id) REFERENCES companies(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


-- ============================================================
-- TABLE 9: stock_prices
-- Monthly OHLCV price history Jan 2020 - Dec 2024.
-- ~5,520 rows (92 companies x 60 months)
-- NOTE: This data is SIMULATED
-- ============================================================

CREATE TABLE IF NOT EXISTS stock_prices (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id     TEXT    NOT NULL,
    date           TEXT    NOT NULL,        -- Format: YYYY-MM-DD
    open_price     REAL,                    -- Monthly opening price in Rs
    high_price     REAL,                    -- Monthly high in Rs
    low_price      REAL,                    -- Monthly low in Rs
    close_price    REAL,                    -- Monthly closing price in Rs
    volume         INTEGER,                 -- Monthly traded volume
    adjusted_close REAL,                    -- Same as close (no adjustment)

    UNIQUE (company_id, date),

    FOREIGN KEY (company_id) REFERENCES companies(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


-- ============================================================
-- TABLE 10: market_cap
-- Annual valuation multiples 2019-2024.
-- ~552 rows (92 companies x 6 years)
-- NOTE: This data is SIMULATED
-- ============================================================

CREATE TABLE IF NOT EXISTS market_cap (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id              TEXT    NOT NULL,
    year                    INTEGER NOT NULL,   -- Calendar year e.g. 2024
    market_cap_crore        REAL,               -- Market cap in Cr
    enterprise_value_crore  REAL,               -- EV in Cr
    pe_ratio                REAL,               -- Price to earnings
    pb_ratio                REAL,               -- Price to book
    ev_ebitda               REAL,               -- EV / EBITDA
    dividend_yield_pct      REAL,               -- Annual dividend yield %

    UNIQUE (company_id, year),

    FOREIGN KEY (company_id) REFERENCES companies(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


-- ============================================================
-- INDEXES — speed up common queries
-- ============================================================

-- Speed up joins on company_id
CREATE INDEX IF NOT EXISTS idx_pl_company
    ON profitandloss(company_id);

CREATE INDEX IF NOT EXISTS idx_bs_company
    ON balancesheet(company_id);

CREATE INDEX IF NOT EXISTS idx_cf_company
    ON cashflow(company_id);

CREATE INDEX IF NOT EXISTS idx_sp_company
    ON stock_prices(company_id);

CREATE INDEX IF NOT EXISTS idx_mc_company
    ON market_cap(company_id);

-- Speed up time-series queries
CREATE INDEX IF NOT EXISTS idx_pl_year
    ON profitandloss(year);

CREATE INDEX IF NOT EXISTS idx_bs_year
    ON balancesheet(year);

CREATE INDEX IF NOT EXISTS idx_cf_year
    ON cashflow(year);

-- Speed up sector queries
CREATE INDEX IF NOT EXISTS idx_sectors_broad
    ON sectors(broad_sector);