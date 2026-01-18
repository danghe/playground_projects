import sqlite3
import os

DB_NAME = 'ma_health.db'
DB_PATH = os.path.join(os.path.dirname(__file__), DB_NAME)

SCHEMA_SCRIPT = """
-- Companies (Universe)
CREATE TABLE IF NOT EXISTS companies (
    ticker TEXT PRIMARY KEY,
    cik TEXT,
    company_name TEXT,
    sector TEXT,
    sub_sector TEXT,
    market_cap REAL,
    avg_daily_volume REAL,
    last_price REAL,
    high_52w REAL,
    returns_3m REAL,
    returns_6m REAL,
    returns_12m REAL,
    classification_confidence TEXT, -- 'High', 'Medium', 'Low'
    coverage_flags JSON,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Entity Resolution
CREATE TABLE IF NOT EXISTS company_aliases (
    alias TEXT PRIMARY KEY,
    ticker TEXT,
    alias_type TEXT, -- 'legal', 'common', 'brand', 'former'
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(ticker) REFERENCES companies(ticker)
);

-- Financials (Deep Fundamentals)
CREATE TABLE IF NOT EXISTS fundamentals (
    ticker TEXT,
    as_of DATE,
    revenue_ttm REAL,
    revenue_yoy REAL,
    ebitda_ttm REAL,
    ebit_ttm REAL,
    fcf_ttm REAL,
    cash REAL,
    total_debt REAL,
    interest_expense REAL,
    buybacks_4q REAL,
    buybacks_prev_4q REAL,
    num_segments INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, as_of),
    FOREIGN KEY(ticker) REFERENCES companies(ticker)
);

-- SEC Filings (Metadata Store)
CREATE TABLE IF NOT EXISTS sec_filings (
    accession TEXT PRIMARY KEY,
    ticker TEXT,
    cik TEXT,
    form_type TEXT,
    filed_at TIMESTAMP,
    doc_url TEXT,
    primary_doc_url TEXT,
    parsed_items_json JSON,
    exhibits_json JSON,
    snippet TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(ticker) REFERENCES companies(ticker)
);

-- Deal Tape (Announced Deals)
CREATE TABLE IF NOT EXISTS deals (
    deal_id TEXT PRIMARY KEY,
    announced_date DATE,
    status TEXT, -- 'Announced', 'Pending', 'Closed', 'Terminated'
    acquirer_ticker TEXT,
    target_ticker TEXT,
    target_name TEXT,
    deal_type TEXT, -- 'Wholeco', 'Asset', 'Carve-out', 'Minority', 'JV', 'Tender'
    value_usd REAL,
    consideration TEXT,
    source_accession TEXT,
    source_url TEXT,
    sector TEXT,
    sub_sector TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Events (News + SEC Normalized)
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    ticker TEXT,
    event_date DATE,
    event_type TEXT, -- 'Activism', 'StrategicReview', 'Divestiture', etc.
    source_type TEXT, -- 'SEC', 'News', 'IR'
    confidence_label TEXT, -- 'AUDIT', 'TRUSTED', 'UNCONFIRMED'
    source_url TEXT,
    source_domain TEXT,
    title TEXT,
    snippet TEXT,
    tags_json JSON,
    corroboration_group_id TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(ticker) REFERENCES companies(ticker)
);

-- Scores (Glass Box)
CREATE TABLE IF NOT EXISTS scores (
    ticker TEXT,
    as_of DATE,
    spi REAL,
    fsp REAL,
    ssi REAL,
    spi_drivers_json JSON,
    seller_type TEXT,
    buyer_readiness REAL,
    capacity REAL,
    motive REAL,
    br_drivers_json JSON,
    buyer_type TEXT,
    confidence TEXT, -- 'High', 'Medium', 'Low'
    missing_fields_json JSON,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, as_of),
    FOREIGN KEY(ticker) REFERENCES companies(ticker)
);

-- Sponsors (Private Equity)
CREATE TABLE IF NOT EXISTS sponsors (
    name TEXT PRIMARY KEY,
    est_dry_powder_usd REAL,
    focus_sector TEXT,
    source_note TEXT,
    last_updated DATE
);

-- Run Log
CREATE TABLE IF NOT EXISTS run_log (
    run_id TEXT PRIMARY KEY,
    job_name TEXT,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    status TEXT,
    counts_json JSON,
    error_json JSON
);
"""

def get_db_path():
    return DB_PATH

def get_schema():
    return SCHEMA_SCRIPT
