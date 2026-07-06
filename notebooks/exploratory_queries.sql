-- ============================================================
-- Nifty 100 Financial Intelligence Platform
-- Sprint 1 — Exploratory SQL Queries
--
-- Run these in any SQLite browser or via Python
-- Author: Pranjal
-- Date: Sprint 1 Day 7
-- ============================================================


-- ── Query 1: Row count per table ─────────────────────────────
-- Purpose: Verify all 10 tables have data loaded

SELECT 'companies'     AS table_name, COUNT(*) AS row_count FROM companies
UNION ALL
SELECT 'profitandloss',                COUNT(*)              FROM profitandloss
UNION ALL
SELECT 'balancesheet',                 COUNT(*)              FROM balancesheet
UNION ALL
SELECT 'cashflow',                     COUNT(*)              FROM cashflow
UNION ALL
SELECT 'analysis',                     COUNT(*)              FROM analysis
UNION ALL
SELECT 'documents',                    COUNT(*)              FROM documents
UNION ALL
SELECT 'prosandcons',                  COUNT(*)              FROM prosandcons
UNION ALL
SELECT 'sectors',                      COUNT(*)              FROM sectors
UNION ALL
SELECT 'stock_prices',                 COUNT(*)              FROM stock_prices
UNION ALL
SELECT 'market_cap',                   COUNT(*)              FROM market_cap;


-- ── Query 2: Year coverage per company ───────────────────────
-- Purpose: Check how many years of P&L data each company has
-- Flag companies with less than 10 years

SELECT
    p.company_id,
    c.company_name,
    COUNT(DISTINCT p.year)  AS years_of_data,
    MIN(p.year)             AS earliest_year,
    MAX(p.year)             AS latest_year,
    CASE
        WHEN COUNT(DISTINCT p.year) >= 10 THEN 'GOOD'
        WHEN COUNT(DISTINCT p.year) >= 5  THEN 'ACCEPTABLE'
        ELSE 'LOW'
    END AS coverage_status
FROM profitandloss p
JOIN companies c ON p.company_id = c.id
GROUP BY p.company_id, c.company_name
ORDER BY years_of_data ASC;


-- ── Query 3: NULL value check across critical columns ─────────
-- Purpose: Find missing data in important fields

SELECT
    'profitandloss.sales'          AS column_name,
    COUNT(*)                       AS null_count
FROM profitandloss WHERE sales IS NULL
UNION ALL
SELECT 'profitandloss.net_profit', COUNT(*)
FROM profitandloss WHERE net_profit IS NULL
UNION ALL
SELECT 'profitandloss.eps',        COUNT(*)
FROM profitandloss WHERE eps IS NULL
UNION ALL
SELECT 'balancesheet.total_assets',COUNT(*)
FROM balancesheet WHERE total_assets IS NULL
UNION ALL
SELECT 'balancesheet.borrowings',  COUNT(*)
FROM balancesheet WHERE borrowings IS NULL
UNION ALL
SELECT 'cashflow.operating_activity', COUNT(*)
FROM cashflow WHERE operating_activity IS NULL;


-- ── Query 4: Top 10 companies by latest year sales ────────────
-- Purpose: Sanity check — RELIANCE should be near top

SELECT
    p.company_id,
    c.company_name,
    p.year,
    ROUND(p.sales, 0)       AS sales_cr,
    ROUND(p.net_profit, 0)  AS profit_cr,
    ROUND(p.opm_percentage, 1) AS opm_pct
FROM profitandloss p
JOIN companies c ON p.company_id = c.id
WHERE p.year = (
    SELECT MAX(year) FROM profitandloss p2
    WHERE p2.company_id = p.company_id
)
ORDER BY p.sales DESC
LIMIT 10;


-- ── Query 5: Sector distribution ─────────────────────────────
-- Purpose: Check how many companies in each sector

SELECT
    broad_sector,
    COUNT(*)        AS company_count,
    GROUP_CONCAT(company_id, ', ') AS companies
FROM sectors
GROUP BY broad_sector
ORDER BY company_count DESC;


-- ── Query 6: Companies with zero debt (latest year) ───────────
-- Purpose: Find debt-free companies — quality indicator

SELECT
    b.company_id,
    c.company_name,
    b.year,
    b.borrowings,
    b.reserves,
    s.broad_sector
FROM balancesheet b
JOIN companies c  ON b.company_id = c.id
JOIN sectors s    ON b.company_id = s.company_id
WHERE b.borrowings = 0
AND b.year = (
    SELECT MAX(year) FROM balancesheet b2
    WHERE b2.company_id = b.company_id
)
ORDER BY b.reserves DESC;


-- ── Query 7: Cash flow health check ──────────────────────────
-- Purpose: Companies with positive CFO in latest year
-- Positive CFO = generating cash from operations (healthy)

SELECT
    cf.company_id,
    c.company_name,
    cf.year,
    ROUND(cf.operating_activity, 0)  AS cfo_cr,
    ROUND(cf.investing_activity, 0)  AS cfi_cr,
    ROUND(cf.financing_activity, 0)  AS cff_cr,
    ROUND(cf.operating_activity + cf.investing_activity, 0) AS fcf_cr,
    CASE
        WHEN cf.operating_activity > 0 THEN 'HEALTHY'
        ELSE 'CONCERN'
    END AS cfo_status
FROM cashflow cf
JOIN companies c ON cf.company_id = c.id
WHERE cf.year = (
    SELECT MAX(year) FROM cashflow cf2
    WHERE cf2.company_id = cf.company_id
)
ORDER BY cf.operating_activity DESC
LIMIT 15;


-- ── Query 8: Balance sheet balance check ─────────────────────
-- Purpose: Find rows where assets != liabilities
-- Should be zero or near-zero difference

SELECT
    b.company_id,
    c.company_name,
    b.year,
    ROUND(b.total_assets, 0)      AS assets,
    ROUND(b.total_liabilities, 0) AS liabilities,
    ROUND(ABS(b.total_assets - b.total_liabilities), 0) AS difference,
    ROUND(
        ABS(b.total_assets - b.total_liabilities)
        / NULLIF(b.total_assets, 0) * 100,
    2) AS diff_pct
FROM balancesheet b
JOIN companies c ON b.company_id = c.id
WHERE b.total_assets > 0
AND ABS(b.total_assets - b.total_liabilities)
    / NULLIF(b.total_assets, 0) > 0.01
ORDER BY diff_pct DESC
LIMIT 10;


-- ── Query 9: Annual report coverage ──────────────────────────
-- Purpose: Check which companies have most/least annual reports

SELECT
    d.company_id,
    c.company_name,
    COUNT(*)        AS report_count,
    MIN(d.year)     AS earliest_report,
    MAX(d.year)     AS latest_report
FROM documents d
JOIN companies c ON d.company_id = c.id
GROUP BY d.company_id, c.company_name
ORDER BY report_count DESC
LIMIT 15;


-- ── Query 10: Data completeness summary ──────────────────────
-- Purpose: Final completeness check for Sprint 1 sign-off

SELECT
    'Total companies'           AS metric,
    COUNT(*)                    AS value
FROM companies
UNION ALL
SELECT
    'Companies with P&L data',
    COUNT(DISTINCT company_id)
FROM profitandloss
UNION ALL
SELECT
    'Companies with BS data',
    COUNT(DISTINCT company_id)
FROM balancesheet
UNION ALL
SELECT
    'Companies with CF data',
    COUNT(DISTINCT company_id)
FROM cashflow
UNION ALL
SELECT
    'Companies with sector mapping',
    COUNT(DISTINCT company_id)
FROM sectors
UNION ALL
SELECT
    'Companies with stock prices',
    COUNT(DISTINCT company_id)
FROM stock_prices
UNION ALL
SELECT
    'Total P&L records',
    COUNT(*)
FROM profitandloss
UNION ALL
SELECT
    'Total BS records',
    COUNT(*)
FROM balancesheet
UNION ALL
SELECT
    'Total CF records',
    COUNT(*)
FROM cashflow
UNION ALL
SELECT
    'Total stock price records',
    COUNT(*)
FROM stock_prices;