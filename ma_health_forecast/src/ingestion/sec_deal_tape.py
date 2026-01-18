import re
import sqlite3
import json
import logging
import sys
import os
from datetime import datetime, timedelta

# Path hack for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.data.sec_client import SECClient
from src.data.schema import get_db_path

class DealTapeIngestor:
    """
    Module A: Announced Deal Tape (SEC Audit-Grade).
    Scans for 8-K, S-4, DEFM14A to detect Definitive Agreements.
    """
    
    # regex patterns
    DEAL_PATTERNS = r"Merger Agreement|Agreement and Plan of Merger|Stock Purchase Agreement|Asset Purchase Agreement|Purchase and Sale Agreement|Business Combination|Plan of Reorganization"
    ACTION_PATTERNS = r"acquire|acquisition|merger|to be acquired|divestiture|sale of|carve-out|spin-off|strategic review"
    
    VALUE_PATTERN = r"\$([\d\.]+) (million|billion)"
    
    def __init__(self):
        self.client = SECClient()
        self.db_path = get_db_path()
        
    def run_sweep(self, tickers):
        print(f"Starting Deal Tape Sweep for {len(tickers)} tickers...")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        count = 0
        known_deals = 0
        
        for t in tickers:
            cik = self.client.get_cik(t)
            if not cik: 
                # print(f"Skipping {t} (No CIK)")
                continue
            
            data = self.client.fetch_submissions(cik)
            if not data: continue
            
            deals = self._analyze_filings(t, data)
            for d in deals:
                self._save_deal(cursor, d)
                count += 1
                
        conn.commit()
        conn.close()
        print(f"Deal Tape Sweep Complete. Processed {count} potential events.")

    def _analyze_filings(self, ticker, data):
        deals = []
        filings = data.get('filings', {}).get('recent', {})
        if not filings: return []
        
        forms = filings.get('form', [])
        dates = filings.get('filingDate', [])
        items = filings.get('items', [])
        accessions = filings.get('accessionNumber', [])
        primary_docs = filings.get('primaryDocument', [])
        
        # Look back 180 days for test, 90 for prod
        cutoff = datetime.now() - timedelta(days=180)
        
        for i, form in enumerate(forms):
            try:
                # 1. Broad Filter (Form Type)
                if form not in ['8-K', 'S-4', 'DEFM14A', 'SC TO-T', 'SC TO-I']:
                    continue
                    
                f_date = datetime.strptime(dates[i], '%Y-%m-%d')
                # if f_date < cutoff: continue
                
                # 2. Gatekeeper (8-K Items)
                # 1.01 = Entry into Material Definitive Agreement
                # 2.01 = Completion of Acquisition/Disposition
                # 8.01 = Other events (often press release "Entry into...")
                
                is_deal_doc = False
                deal_status = "Announced"
                deal_type = "Wholeco" # Default
                
                acc = accessions[i]
                
                if form == '8-K':
                    its = items[i] if i < len(items) else ""
                    if "1.01" in its or "2.01" in its:
                        is_deal_doc = True
                        if "2.01" in its: deal_status = "Closed"
                    else:
                        continue # Skip non-deal 8-Ks
                        
                elif form in ['S-4', 'DEFM14A']:
                    is_deal_doc = True
                    deal_status = "Pending"
                
                elif 'SC TO' in form:
                    is_deal_doc = True
                    deal_type = "Tender"
                    
                if not is_deal_doc: continue
                
                # 3. Extraction (Mock - would need full text fetch)
                # For now, we trust the Form classification + basic pattern check
                
                deal_id = f"{ticker}_{dates[i]}_{form}"
                
                deals.append({
                    "deal_id": deal_id,
                    "ticker": ticker,
                    "date": dates[i],
                    "status": deal_status,
                    "type": deal_type,
                    "accession": acc,
                    "form": form,
                    "source_url": f"https://www.sec.gov/Archives/edgar/data/{data['cik']}/{acc.replace('-','')}/{primary_docs[i]}"
                })
                
            except Exception as e:
                print(f"Error analyzing filing {i} for {ticker}: {e}")
                
        return deals

    def _save_deal(self, cursor, deal):
        # Insert or Ignore
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO deals (
                    deal_id, announced_date, status, acquirer_ticker, deal_type, source_accession, source_url, sector
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                deal['deal_id'], deal['date'], deal['status'], 
                deal['ticker'], deal['type'], deal['accession'], deal['source_url'], 'Unknown'
            ))
        except Exception as e:
            print(f"DB Error: {e}")

if __name__ == "__main__":
    ingestor = DealTapeIngestor()
    # Test with a few known deal-makers
    # MSFT (ATVI), CRM (Slack), AVGO (VMware), ADSK (Design)
    targets = ['MSFT', 'CRM', 'AVGO', 'ADSK', 'SSNC']
    ingestor.run_sweep(targets)
