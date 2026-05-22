"""
Example: SMA Crossover dengan TP/SL
Gunakan: python3 examples/example.py
"""
import sys
sys.path.insert(0, "/home/admin/rust-engine/python")

import pandas as pd
import numpy as np
from rust_backtest import run

np.random.seed(42)
n = 1000
price = 100.0
prices = []
for _ in range(n):
    price += np.random.normal(0, 0.5)
    prices.append(max(price, 1.0))

df = pd.DataFrame({
    "timestamp": pd.date_range("2020-01-01", periods=n, freq="h"),
    "close": prices,
    "open": [p * (1 + np.random.normal(0, 0.001)) for p in prices],
    "high": [p * (1 + abs(np.random.normal(0, 0.003))) for p in prices],
    "low": [p * (1 - abs(np.random.normal(0, 0.003))) for p in prices],
    "volume": np.random.randint(1000, 10000, n),
})

sma_fast = df["close"].rolling(10).mean()
sma_slow = df["close"].rolling(30).mean()
df["signal"] = 0
df.loc[sma_fast > sma_slow, "signal"] = 1
df.loc[sma_fast < sma_slow, "signal"] = -1
df.loc[:30, "signal"] = 0

df["tp_price"] = np.where(
    df["signal"] == 1, df["close"] * 1.03,
    np.where(df["signal"] == -1, df["close"] * 0.97, 0.0)
)
df["sl_price"] = np.where(
    df["signal"] == 1, df["close"] * 0.985,
    np.where(df["signal"] == -1, df["close"] * 1.015, 0.0)
)
df["units"] = 100

result = run(
    df,
    timestamp_col="timestamp",
    initial_capital=100_000.0,
    commission_pct=0.001,
    slippage_pct=0.0005,
)

result.summary()
print(f"\nTrades exit breakdown:\n{result.trades['exit_reason'].value_counts()}")
