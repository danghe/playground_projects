from pathlib import Path
from src.index.ma_index import build_index
from src.forecast.forecast import arima_forecast
from src.plotting.plots import plot_composite, plot_buckets, plot_forecast


def main():
    outdir = Path("output"); outdir.mkdir(exist_ok=True, parents=True)
    df = build_index("config/signals.yaml")
    df.to_csv(outdir / "ma_health_index.csv")
    plot_composite(df, str(outdir / "ma_health_index.png"))
    plot_buckets(df, str(outdir / "bucket_contributions.png"))
    comp = df["Composite"].dropna()
    fc, _ = arima_forecast(comp, steps=12, order=(3, 0, 0))
    fc.to_csv(outdir / "ma_health_forecast.csv")
    plot_forecast(comp, fc, str(outdir / "ma_health_forecast.png"))
    print("Done. Files in output/:", [p.name for p in outdir.iterdir()])


if __name__ == "__main__":
    main()
