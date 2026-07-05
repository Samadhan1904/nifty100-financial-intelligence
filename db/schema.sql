-- ============================================================
-- Nifty 100 Financial Intelligence Platform
-- SQLite Database Schema - 10 Tables
--
-- Note: FK constraints removed intentionally.
-- Referential integrity is enforced in validator.py (DQ-03)
-- not at the database level, to allow pandas bulk loading.
--
-- Author: Samadhan
-- Sprint: 1 - Day 4
-- ============================================================

PRAGMA foreign_keys = OFF;


-- ============================================================
-- TABLE 1: companies
-- ============================================================

CREATE TABLE IF NOT EXISTS companies (
    id              TEXT    PRIMARY KEY,
    company_logo    TEXT,
    company_name    TEXT    NOT NULL,
    chart_link      TEXT,
    about_company   TEXT,
    website         TEXT,
    nse_profile     TEXT,
    bse_profile     TEXT,
    face_value      REAL,
    book_value      REAL,
    roce_percentage REAL,
    roe_percentage  REAL
);


-- ============================================================
-- TABLE 2: profitandloss
-- ============================================================

CREATE TABLE IF NOT EXISTS profitandloss (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id          TEXT    NOT NULL,
    year                TEXT    NOT NULL,
    sales               REAL,
    expenses            REAL,
    operating_profit    REAL,
    opm_percentage      REAL,
    other_income        REAL,
    interest            REAL,
    depreciation        REAL,
    profit_before_tax   REAL,
    tax_percentage      REAL,
    net_profit          REAL,
    eps                 REAL,
    dividend_payout     REAL,
    UNIQUE (company_id, year)
);


-- ============================================================
-- TABLE 3: balancesheet
-- ============================================================

CREATE TABLE IF NOT EXISTS balancesheet (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id          TEXT    NOT NULL,
    year                TEXT    NOT NULL,
    equity_capital      REAL,
    reserves            REAL,
    borrowings          REAL,
    other_liabilities   REAL,
    total_liabilities   REAL,
    fixed_assets        REAL,
    cwip                REAL,
    investments         REAL,
    other_asset         REAL,
    total_assets        REAL,
    UNIQUE (company_id, year)
);


-- ============================================================
-- TABLE 4: cashflow
-- ============================================================

CREATE TABLE IF NOT EXISTS cashflow (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id           TEXT    NOT NULL,
    year                 TEXT    NOT NULL,
    operating_activity   REAL,
    investing_activity   REAL,
    financing_activity   REAL,
    net_cash_flow        REAL,
    UNIQUE (company_id, year)
);


-- ============================================================
-- TABLE 5: analysis
-- ============================================================

CREATE TABLE IF NOT EXISTS analysis (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id               TEXT    NOT NULL UNIQUE,
    compounded_sales_growth  TEXT,
    compounded_profit_growth TEXT,
    stock_price_cagr         TEXT,
    roe                      TEXT
);


-- ============================================================
-- TABLE 6: documents
-- ============================================================

CREATE TABLE IF NOT EXISTS documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id    TEXT    NOT NULL,
    year          INTEGER NOT NULL,
    annual_report TEXT,
    UNIQUE (company_id, year)
);


-- ============================================================
-- TABLE 7: prosandcons
-- ============================================================

CREATE TABLE IF NOT EXISTS prosandcons (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  TEXT    NOT NULL,
    pros        TEXT,
    cons        TEXT
);


-- ============================================================
-- TABLE 8: sectors
-- ============================================================

CREATE TABLE IF NOT EXISTS sectors (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id          TEXT    NOT NULL UNIQUE,
    broad_sector        TEXT    NOT NULL,
    sub_sector          TEXT,
    index_weight_pct    REAL,
    market_cap_category TEXT
);


-- ============================================================
-- TABLE 9: stock_prices
-- NOTE: SIMULATED DATA
-- ============================================================

CREATE TABLE IF NOT EXISTS stock_prices (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id     TEXT    NOT NULL,
    date           TEXT    NOT NULL,
    open_price     REAL,
    high_price     REAL,
    low_price      REAL,
    close_price    REAL,
    volume         INTEGER,
    adjusted_close REAL,
    UNIQUE (company_id, date)
);


-- ============================================================
-- TABLE 10: market_cap
-- NOTE: SIMULATED DATA
-- ============================================================

CREATE TABLE IF NOT EXISTS market_cap (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id             TEXT    NOT NULL,
    year                   INTEGER NOT NULL,
    market_cap_crore       REAL,
    enterprise_value_crore REAL,
    pe_ratio               REAL,
    pb_ratio               REAL,
    ev_ebitda              REAL,
    dividend_yield_pct     REAL,
    UNIQUE (company_id, year)
);


-- ============================================================
-- INDEXES - speed up common queries
-- ============================================================

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

CREATE INDEX IF NOT EXISTS idx_pl_year
    ON profitandloss(year);

CREATE INDEX IF NOT EXISTS idx_bs_year
    ON balancesheet(year);

CREATE INDEX IF NOT EXISTS idx_cf_year
    ON cashflow(year);

CREATE INDEX IF NOT EXISTS idx_sectors_broad
    ON sectors(broad_sector);