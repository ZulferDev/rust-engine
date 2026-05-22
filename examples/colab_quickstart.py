"""
=== RUST BACKTEST ENGINE — Quickstart for Google Colab / Kaggle ===

Cara pakai di Colab:
    1. Copy-paste semua kode di bawah ke cell Colab
    2. Jalankan

Atau jalankan langsung:
    python3 colab_quickstart.py
"""

# ──────────────────── CELL 1: Install ────────────────────
import subprocess, sys, os
from pathlib import Path

# Clone repo (ganti dengan repo URL kamu nanti)
repo_url = "https://github.com/username/rust-engine.git"
repo_dir = Path("/content/rust-engine")

if not repo_dir.exists():
    print("Cloning repository...")
    subprocess.run(["git", "clone", repo_url, str(repo_dir)], check=True)

os.chdir(repo_dir)

# Install Python package (akan trigger build Rust engine)
subprocess.run([sys.executable, "-m", "pip", "install", "-e", "./python"], check=True)

# ──────────────────── CELL 2: Import ────────────────────
from rust_backtest import run
import pandas as pd
import numpy as np

print("Import OK")

# ──────────────────── CELL 3: Generate Data ────────────────────
np.random.seed(42)
n = 2000
price = 100.0
prices = []
for _ in range(n):
    price += np.random.normal(0, 0.3)
    prices.append(max(price, 1.0))

df = pd.DataFrame({
    "timestamp": pd.date_range("2020-01-01", periods=n, freq="h"),
    "close": prices,
    "open": [p * (1 + np.random.normal(0, 0.001)) for p in prices],
    "high": [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
    "low":  [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
    "volume": np.random.randint(1000, 10000, n),
})

# Simple SMA crossover signal
sma10 = df["close"].rolling(20).mean()
sma30 = df["close"].rolling(60).mean()
df["signal"] = 0
df.loc[sma10 > sma30, "signal"] = 1
df.loc[sma10 < sma30, "signal"] = -1
df.loc[:60, "signal"] = 0  # warmup

# TP/SL: 2% take profit, 1% stop loss
df["tp_price"] = np.where(
    df["signal"] == 1, df["close"] * 1.02,
    np.where(df["signal"] == -1, df["close"] * 0.98, 0.0)
)
df["sl_price"] = np.where(
    df["signal"] == 1, df["close"] * 0.99,
    np.where(df["signal"] == -1, df["close"] * 1.01, 0.0)
)
df["units"] = 50

# ──────────────────── CELL 4: Run Backtest ────────────────────
result = run(
    df,
    timestamp_col="timestamp",
    initial_capital=50_000,
    commission_pct=0.001,
    slippage_pct=0.0005,
)

result.summary()

# ──────────────────── CELL 5: Analisis ────────────────────
print(f"\nTrade sample:\n{result.trades.head(10)}")
print(f"\nExit reason breakdown:\n{result.trades['exit_reason'].value_counts()}")

# Plot equity curve (Colab)
try:
    import matplotlib.pyplot as plt
    plt.figure(figsize=(12, 5))
    plt.plot(result.equity_curve["timestamp"], result.equity_curve["equity"])
    plt.title("Equity Curve")
    plt.xlabel("Time")
    plt.ylabel("Equity ($)")
    plt.grid(True, alpha=0.3)
    plt.show()
except ImportError:
    print("Install matplotlib untuk plot: !pip install matplotlib")
