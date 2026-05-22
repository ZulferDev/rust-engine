<p align="center">
  <h1 align="center">⚡ Rust Backtest Engine</h1>
  <p align="center">Fast backtesting engine for trading strategy validation.</p>
  <p align="center"><b>Rust</b> core loop · <b>Python</b> wrapper · 100–1000× faster than pure Python</p>
</p>

<p align="center">
  <a href="https://github.com/ZulferDev/rust-engine/releases"><img src="https://img.shields.io/github/v/release/ZulferDev/rust-engine" alt="Release"></a>
  <a href="https://github.com/ZulferDev/rust-engine/actions/workflows/release.yml"><img src="https://img.shields.io/github/actions/workflow/status/ZulferDev/rust-engine/release.yml?branch=main" alt="Build"></a>
</p>

---

## Quick Start

```bash
pip install git+https://github.com/ZulferDev/rust-engine.git
```

```python
from rust_backtest import run
import pandas as pd, numpy as np

# Prepare your data (OHLCV + signal + tp/sl + units)
df = pd.DataFrame({
    "timestamp": pd.date_range("2020-01-01", periods=5000, freq="h"),
    "close": ...,
    "high": ..., "low": ..., "open": ..., "volume": ...,
    "signal": ...,       # 1 = Long, -1 = Short, 0 = no action
    "tp_price": ...,     # take profit price
    "sl_price": ...,     # stop loss price
    "units": ...,        # position size
})

result = run(df, timestamp_col="timestamp", initial_capital=10_000)
result.summary()
# ══════════════════════════════════════════════
#   Sharpe Ratio:     1.24
#   Total Return:     +$636.09 (+0.64%)
#   Max Drawdown:     1.17%
#   Total Trades:     47 (42.6% win rate)
# ══════════════════════════════════════════════

result.trades        # DataFrame: complete trade history
result.equity_curve  # DataFrame: equity per bar
result.stats         # dict: 25+ metrics
```

Binary Rust di-download otomatis (pre-built, ~700 KB) — **tidak perlu kompilasi**.

---

## Why Rust?

| Task | Pure Python | Rust (this engine) |
|---|---|---|
| 100,000 bars | ~3–5 sec | ~30 ms |
| 1,000,000 bars | ~30–50 sec | ~250 ms |
| Parameter optimization (10k runs) | ~10 hours | ~30 min |

Signal processing stays in Python (pandas/numpy is fast enough). The iteration-heavy backtest loop moves to Rust.

---

## Google Colab / Kaggle

```python
# Satu baris — langsung bisa
!pip install git+https://github.com/ZulferDev/rust-engine.git

from rust_backtest import run
```

Binary di-download otomatis saat `run()` pertama (~2 detik). Tersimpan di cache (`~/.cache/rust_backtest/`) — tidak perlu download ulang tiap runtime restart.

---

## Data Format

| Column | Values | Description |
|---|---|---|
| `signal` | `1`, `-1`, `0` | Long, Short, No action |
| `tp_price` | float | Take profit price (set per bar) |
| `sl_price` | float | Stop loss price (set per bar) |
| `units` | int/float | Position size in shares/contracts |
| `timestamp` | datetime/int | Unix seconds or datetime. Auto-detect. |
| `open, high, low, close, volume` | float | OHLCV data |

### Signal Logic

- **1** → Open Long (only if currently Flat)
- **-1** → Open Short (only if currently Flat)
- **0** → No action
- Positions close **only** via TP/SL (signal does not close)
- No overlapping positions allowed

### TP/SL Exit

**Long**: TP if `high >= tp_price`, SL if `low <= sl_price`
**Short**: TP if `low <= tp_price`, SL if `high >= sl_price`

Exit price = the TP or SL price that was hit.

---

## Statistics (25+ metrics)

| Category | Metrics |
|---|---|
| **Return** | Initial/final equity, total return ($/%), annualized return, volatility |
| **Risk** | Max drawdown ($/%), Sharpe ratio, Sortino ratio, Calmar ratio |
| **Trades** | Total/winning/losing/breakeven, win rate, profit factor, expectancy |
| **Detail** | Avg win/loss ($/%), largest win/loss, avg holding period, consecutive wins/losses |

All risk metrics are annualized using actual calendar duration.

---

## Configuration

```python
result = run(df,
    initial_capital=10_000,     # Starting capital
    commission_pct=0.001,       # 0.1% per transaction (×2 for entry+exit)
    slippage_pct=0.0005,        # 0.05% slippage on entry
)
```

---

## How It Works

```
Python (signal, prep) ──CSV──▶ Rust engine ──JSON──▶ Python (result)
```

- **Build**: Tag `v*` → GitHub Actions build musl static binary → upload ke Release
- **Install**: `pip install` via git clone repo
- **Run**: `run()` pertama → download pre-built binary dari GitHub Releases → cache di `~/.cache/`
- **Fallback**: Jika download gagal, build dari source (Rust harus terinstall)

---

## Documentation

Full documentation: [`docs/engine_documentation.md`](docs/engine_documentation.md)

Includes: architecture, API reference, formula derivations for all statistics, limitations, and changelog.

---

## Limitations

- TP checked before SL when both hit in same bar (standard convention)
- Entry at bar close (no intra-bar entries)
- Open positions at data end are not closed (unrealized PnL in final equity)
- No margin call enforcement (cash can go negative)

---

## License

MIT
