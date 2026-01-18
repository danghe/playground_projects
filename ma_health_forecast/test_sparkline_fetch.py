import yfinance as yf

print("Testing 90d period...")
t = yf.Ticker("AAPL")
try:
    h = t.history(period="90d")
    print(f"90d Result Empty?: {h.empty}")
    print(f"90d Result Len: {len(h)}")
except Exception as e:
    print(f"90d Error: {e}")

print("\nTesting 3mo period...")
try:
    h = t.history(period="3mo")
    print(f"3mo Result Empty?: {h.empty}")
    print(f"3mo Result Len: {len(h)}")
except Exception as e:
    print(f"3mo Error: {e}")
