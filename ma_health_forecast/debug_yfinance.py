import yfinance as yf

tickers = ["AAPL", "MSFT", "NVDA", "ORCL"]

print(f"--- Testing YFinance for {tickers} ---")
for t in tickers:
    try:
        print(f"Fetching {t}...")
        stock = yf.Ticker(t)
        info = stock.info
        mc = info.get('marketCap')
        sector = info.get('sector')
        print(f"  > {t}: Market Cap=${mc}, Sector={sector}")
    except Exception as e:
        print(f"  x Failed {t}: {e}")
