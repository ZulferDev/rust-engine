# Rust Backtest Engine — Dokumentasi

Backtest engine cepat untuk validasi strategi trading. Core loop ditulis dalam **Rust** untuk performa maksimal, dengan **Python wrapper** untuk kemudahan integrasi.

## Daftar Isi

- [Arsitektur](#arsitektur)
- [Instalasi](#instalasi)
  - [pip install](#pip-install)
  - [Google Colab / Kaggle](#google-colab--kaggle)
  - [Manual](#manual)
- [Data Format](#data-format)
  - [Kolom Wajib](#kolom-wajib)
  - [Timestamp](#timestamp)
  - [Signal](#signal)
  - [TP / SL](#tp--sl)
  - [Units](#units)
  - [Contoh DataFrame](#contoh-dataframe)
- [API Reference](#api-reference)
  - [run()](#run)
  - [BacktestResult](#backtestresult)
- [Logika Backtest](#logika-backtest)
  - [Entry](#entry)
  - [Exit (TP/SL)](#exit-tpsl)
  - [Tidak Ada Concurrent Position](#tidak-ada-concurrent-position)
  - [Equity Curve](#equity-curve)
- [Statistics Reference](#statistics-reference)
  - [Return Metrics](#return-metrics)
  - [Risk Metrics](#risk-metrics)
  - [Trade Metrics](#trade-metrics)
  - [Ratio Metrics](#ratio-metrics)
- [Configuration](#configuration)
- [Komisi & Slippage](#komisi--slippage)
- [Performance](#performance)
- [Limitations](#limitations)
- [Changelog](#changelog)

---

## Arsitektur

```
┌─────────────────────┐     CSV (stdin)      ┌──────────────────────┐
│  Python (pandas)    │ ──────────────────▶  │  Rust CLI Binary     │
│  - Generate signal  │                      │  - Parse CSV         │
│  - Prepare data     │     JSON (stdout)    │  - Iterate bars      │
│  - Visualize hasil  │ ◀──────────────────  │  - Hitung statistik  │
└─────────────────────┘                      └──────────────────────┘
```

- **Python** handle: persiapan data,生成 sinyal, visualisasi
- **Rust** handle: iterasi bar-by-bar tercepat, TP/SL checking
- Komunikasi via file CSV (input) dan JSON (output)

### Kenapa Rust?

| Task | Python | Rust (engine ini) |
|---|---|---|
| 100.000 bar, 1 kolom sinyal | ~3-5 detik | ~50-100 ms |
| 1.000.000 bar | ~30-50 detik | ~300-500 ms |
| Optimasi parameter (10.000 run) | ~10 jam | ~30 menit |

---

## Instalasi

### pip install

```bash
# Dari direktori proyek
pip install -e ./python

# Nanti akan build Rust engine otomatis saat run() pertama
```

### Google Colab / Kaggle

```python
# Cell 1: Clone repo
!git clone https://github.com/username/rust-engine.git
%cd rust-engine

# Cell 2: Install Python package
!pip install -e ./python

# Cell 3: Import dan gunakan
from rust_backtest import run
```

Saat `run()` dipanggil pertama kali, builder akan:
1. Cek apakah Rust terinstall → jika tidak, install via rustup
2. Cek apakah C compiler tersedia → jika tidak, download zig
3. Build binary Rust
4. Simpan binary untuk pemakaian berikutnya

### Manual

```bash
# 1. Build Rust binary
cargo build --release

# 2. Install Python package
pip install -e ./python

# 3. Siap digunakan
```

---

## Data Format

### Kolom Wajib

DataFrame input harus memiliki kolom-kolom berikut (default names):

| Kolom | Tipe | Deskripsi |
|---|---|---|
| `timestamp` | datetime / int64 | Waktu bar (Unix seconds) |
| `open` | float64 | Harga open |
| `high` | float64 | Harga tertinggi |
| `low` | float64 | Harga terendah |
| `close` | float64 | Harga close |
| `volume` | float64 | Volume |
| `signal` | int/float | 1 = Long, -1 = Short, 0 = No action |
| `tp_price` | float64 | Harga Take Profit |
| `sl_price` | float64 | Harga Stop Loss |
| `units` | float64 | Jumlah unit/share per trade |

### Timestamp

- Bisa **datetime** (pandas akan konversi ke Unix seconds otomatis)
- Bisa **int64** (Unix seconds since epoch)
- Jika tanpa kolom timestamp, index DataFrame akan dipakai

### Signal

| Value | Arti |
|---|---|
| **1** | Buka posisi **Long** (hanya jika sedang Flat) |
| **-1** | Buka posisi **Short** (hanya jika sedang Flat) |
| **0** | Tidak ada aksi |

> Signal **tidak menutup** posisi. Posisi hanya tertutup via TP/SL.

### TP / SL

- `tp_price` dan `sl_price` diambil dari bar saat entry dan **disimpan untuk seluruh durasi posisi**
- Setiap bar berikutnya, engine cek apakah harga menyentuh TP/SL
  - **Long**: TP jika `high >= tp_price`, SL jika `low <= sl_price`
  - **Short**: TP jika `low <= tp_price`, SL jika `high >= sl_price`
- Exit price = harga TP/SL yang tersentuh

### Units

Jumlah unit (saham/kontrak) per trade. Engine akan cek apakah `units * entry_price <= cash` sebelum entry. Jika tidak cukup, posisi dibatalkan.

### Contoh DataFrame

```python
import pandas as pd
import numpy as np

df = pd.DataFrame({
    "timestamp": pd.date_range("2020-01-01", periods=100, freq="h"),
    "open":   [100 + i*0.1 + np.random.normal(0,0.1) for i in range(100)],
    "high":   [102 + i*0.1 + abs(np.random.normal(0,0.2)) for i in range(100)],
    "low":    [98  + i*0.1 - abs(np.random.normal(0,0.2)) for i in range(100)],
    "close":  [101 + i*0.1 + np.random.normal(0,0.1) for i in range(100)],
    "volume": np.random.randint(1000, 10000, 100),
    "signal": [1 if i < 50 else -1 for i in range(100)],
    "tp_price": [1.03*c for c in close_prices],  # +3% untuk long, -3% untuk short
    "sl_price": [0.985*c for c in close_prices], # -1.5% untuk long, +1.5% untuk short
    "units": [100] * 100,
})
```

---

## API Reference

### `run()`

```python
from rust_backtest import run

result = run(
    df,                          # DataFrame input
    signal_col="signal",         # Nama kolom signal
    open_col="open",
    high_col="high",
    low_col="low",
    close_col="close",
    volume_col="volume",
    tp_col="tp_price",           # Nama kolom take profit
    sl_col="sl_price",           # Nama kolom stop loss
    units_col="units",           # Nama kolom units
    timestamp_col=None,          # None = pakai index
    initial_capital=10_000.0,    # Modal awal
    commission_pct=0.001,        # Komisi per transaksi (0.1%)
    slippage_pct=0.0005,         # Slippage per entry/exit (0.05%)
    engine_path=None,            # Path ke binary Rust (auto-detect)
)
```

**Return**: `BacktestResult`

### `BacktestResult`

```python
result.trades         # DataFrame: histori semua trade
result.equity_curve   # DataFrame: equity per bar
result.stats          # dict: semua metrik statistik

# Metrik utama:
result.stats["total_return"]
result.stats["sharpe_ratio"]
result.stats["max_drawdown_pct"]
result.stats["win_rate"]
result.stats["profit_factor"]

# Lihat semua:
result.summary()  # Print ringkasan

# Akses trades:
result.trades[["entry_time", "exit_time", "direction", "pnl", "exit_reason"]]
```

#### Columns in `result.trades`

| Kolom | Tipe | Deskripsi |
|---|---|---|
| `entry_time` | datetime | Waktu entry |
| `exit_time` | datetime | Waktu exit |
| `direction` | str | "Long" atau "Short" |
| `entry_price` | float | Harga entry (+slippage) |
| `exit_price` | float | Harga exit (TP/SL) |
| `units` | float | Jumlah unit trade |
| `pnl` | float | Profit/Loss absolut |
| `pnl_pct` | float | PnL sebagai % equity saat entry |
| `holding_period` | int | Durasi dalam bar |
| `exit_reason` | str | "TakeProfit" atau "StopLoss" |
| `tp_price` | float | Harga TP yang dipasang |
| `sl_price` | float | Harga SL yang dipasang |

#### Columns in `result.equity_curve`

| Kolom | Tipe | Deskripsi |
|---|---|---|
| `timestamp` | datetime | Waktu bar |
| `equity` | float | Nilai portofolio (cash + MTM) |
| `drawdown` | float | Drawdown dari equity puncak |
| `drawdown_pct` | float | Drawdown sebagai % dari puncak |

---

## Logika Backtest

### Entry

Per bar (setelah TP/SL check dan equity calculation):

```
if state == Flat:
    if signal == 1:
        entry_price = close × (1 + slippage)
        if units × entry_price > cash: SKIP (not enough margin)
        state = Long(entry_price, units, tp_price, sl_price, entry_equity=cash)
    
    elif signal == -1:
        entry_price = close × (1 - slippage)
        if units × entry_price > cash: SKIP
        state = Short(entry_price, units, tp_price, sl_price, entry_equity=cash)
```

- **Entry price** = bar.close adjusted dengan slippage
- **TP/SL** diambil dari bar yang sama
- **units** ditentukan user per bar
- Jika margin tidak cukup, posisi skip (tidak error)

### Exit (TP/SL)

Pada setiap bar, engine cek apakah harga menyentuh batas TP/SL:

**Long Position:**
```
if bar.high >= tp_price → Exit di tp_price (TakeProfit)
else if bar.low <= sl_price → Exit di sl_price (StopLoss)
```

**Short Position:**
```
if bar.low <= tp_price → Exit di tp_price (TakeProfit)
else if bar.high >= sl_price → Exit di sl_price (StopLoss)
```

> Jika TP dan SL kena di bar yang sama, **TP diproses lebih dulu** (konvensi standar).

### Tidak Ada Concurrent Position

Engine hanya mengizinkan SATU posisi aktif dalam satu waktu:
- Saat posisi Long aktif, signal 1 atau -1 diabaikan
- Saat posisi Short aktif, signal -1 atau 1 diabaikan
- Posisi baru hanya dibuka setelah posisi sebelumnya ditutup (via TP/SL) dan state kembali Flat

### Equity Curve

Setiap bar:
1. **TP/SL check** — jika exit, `cash += pnl`
2. **MTM equity** — jika posisi aktif: `equity = cash + unrealized_pnl` (mark-to-market di close price)
3. **Push equity point** — simpan ke equity_curve
4. **Entry check** — jika Flat & signal cocok, buka posisi

Equity baris entry mencerminkan nilai **sebelum** entry (cash). MTM posisi baru mulai terlihat di bar berikutnya.

---

## Statistics Reference

### Return Metrics

| Field | Formula | Notes |
|---|---|---|
| `initial_capital` | — | Dari config |
| `final_equity` | equity_curve[-1] | Termasuk unrealized PnL posisi terbuka |
| `total_return` | final - initial | PnL absolut |
| `total_return_pct` | (return / initial) × 100 | Return total sebagai % |
| `annualized_return_pct` | avg_bar_return × bars_per_year × 100 | Return per tahun |

### Risk Metrics

| Field | Formula | Notes |
|---|---|---|
| `max_drawdown` | max(peak - equity) | Drawdown terbesar dalam $ |
| `max_drawdown_pct` | max(drawdown / peak × 100) | Drawdown terbesar dalam % |
| `volatility` | σ(bar_returns) | Standar deviasi return per bar |

### Trade Metrics

| Field | Formula | Notes |
|---|---|---|
| `total_trades` | Σ trades | — |
| `winning_trades` | trade.pnl > 0 | — |
| `losing_trades` | trade.pnl < 0 | — |
| `breakeven_trades` | trade.pnl == 0 | — |
| `win_rate` | winning / total | Termasuk breakeven di denominator |
| `avg_win` | Σ(win_pnl) / winning_trades | — |
| `avg_loss` | Σ(loss_pnl) / losing_trades | — |
| `largest_win` | max(win_pnl) | — |
| `largest_loss` | min(loss_pnl) | — |
| `profit_factor` | gross_profit / \|gross_loss\| | 999.0 jika semua winning |
| `expectancy` | Σ(pnl) / total_trades | Rata-rata PnL per trade |
| `avg_holding_period` | Σ(holding) / total_trades | Dalam bar |
| `max_consecutive_wins` | longest win streak | Breakeven tidak putus streak |
| `max_consecutive_losses` | longest loss streak | — |

### Ratio Metrics

| Field | Formula | Annualisasi | Notes |
|---|---|---|---|
| `sharpe_ratio` | avg_return × √N / σ_return | Ya (N = bars_per_year) | Risk-free rate dianggap 0 |
| `sortino_ratio` | avg_return × √N / σ_downside | Ya | Downside: √(∑min(0,r)² / N) |
| `calmar_ratio` | annualized_return / max_dd_pct | Ya | CAGR approximation |

#### Annualisasi

```
bars_per_year = total_bars / duration_in_years
annual_factor = sqrt(bars_per_year)
```

Durasi dihitung dari timestamp pertama hingga terakhir (dalam tahun, 1 tahun = 365.25 hari). Otomatis menyesuaikan untuk semua timeframe (1m, 5m, 1h, 4h, daily, dll).

---

## Configuration

| Parameter | Default | Deskripsi |
|---|---|---|
| `initial_capital` | 10,000 | Modal awal |
| `commission_pct` | 0.001 (0.1%) | Komisi per transaksi (×2 untuk entry+exit) |
| `slippage_pct` | 0.0005 (0.05%) | Slippage pada entry dan exit |

**Komisi**: total komisi = `2 × units × entry_price × commission_pct`
**Slippage**: entry_price = `close × (1 ± slippage_pct)`

---

## Komisi & Slippage

- Komisi dihitung 2x (entry + exit): `2 × notional × commission_pct`
- Slippage diterapkan pada entry dan exit:
  - **Long entry**: `close × (1 + slippage)` = entry lebih mahal
  - **Long exit** (TP): tetap pakai TP price (slippage tidak diterapkan ulang)
  - **Short entry**: `close × (1 - slippage)` = entry lebih murah
  - **Short exit** (SL/TP): tetap pakai SL/TP price

---

## Performance

| Jumlah Bar | Waktu Eksekusi (Rust) |
|---|---|
| 1,000 | ~2 ms |
| 10,000 | ~5 ms |
| 100,000 | ~30 ms |
| 1,000,000 | ~250 ms |

vs Python murni (pandas loop): ~100-1000× lebih lambat.

### Tips Performa

- Gunakan data dengan tipe numerik (float64/int64) — tidak perlu konversi string
- Hindari NaN dalam kolom signal/tp/sl/units
- Prefer baris lebih banyak dari kolom lebih banyak — engine optimal untuk data wide

---

## Limitations

| Limitation | Detail |
|---|---|
| **TP before SL** | Jika TP & SL kena di bar sama, TP dianggap lebih dulu. Bias optimistik untuk TP lebar + SL ketat. |
| **Entry di close** | Entry di close bar setelah signal. Jika signal real-time intra-bar, ada delay 1 bar. Standar backtesting. |
| **Unrealized PnL di akhir** | Posisi terbuka di akhir data TIDAK ditutup. Final equity include unrealized PnL. |
| **Fractional units** | Units bisa float (desimal). Tidak validasi lot size atau minimum trade. |
| **No margin call** | Cash bisa negatif jika loss beruntun besar. |
| **No limit/market order** | Entry selalu di close ± slippage. Tidak support limit order. |
| **Annualisasi 365.25** | Sharpe/Sortino pake 365.25 hari, bukan 252 trading day. Lebih akurat untuk crypto 24/7. |

---

## Changelog

### v0.2.0 (Current)
- **Fix**: Sortino downside deviation formula √(∑min(0,r)²/N) — benar
- **Fix**: Calmar ratio pakai annualized return
- **Fix**: Profit factor = 999 untuk all-winning
- **Fix**: Breakeven trades dipisah dari losses
- **Fix**: pnl_pct pakai equity saat entry (bukan initial capital)
- **Fix**: Margin check sebelum entry (units × price ≤ cash)
- **Fix**: Silent drop bar timestamp=0 → hard error
- **Change**: Annualisasi pake 365.25 hari (bukan 252 trading day)

### v0.1.0
- Engine dasar: entry bar.close, exit via TP/SL
- Signal 1/-1/0, tidak ada concurrent position
- Python wrapper dengan pandas
